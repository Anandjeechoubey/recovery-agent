"""Simulates conversations between agents and LLM-played borrowers."""

from __future__ import annotations

from dataclasses import dataclass, field

from openai import AsyncOpenAI

from src.agents.assessment import AssessmentAgent
from src.agents.base import BaseAgent
from src.agents.final_notice import FinalNoticeAgent
from src.agents.resolution import ResolutionAgent
from src.config import settings
from src.context.summarizer import summarize_for_handoff
from src.learning.cost_tracker import CostTracker
from src.learning.personas import BorrowerPersona
from src.models.borrower import Borrower
from src.models.conversation import Conversation, HandoffSummary


@dataclass
class PipelineResult:
    conversations: list[Conversation] = field(default_factory=list)
    handoff_summaries: list[HandoffSummary] = field(default_factory=list)
    final_outcome: str = ""


def make_test_borrower(persona: BorrowerPersona) -> Borrower:
    """Create a test borrower matching the persona's situation."""
    # Map persona names to debt amounts from their prompts
    debt_map = {
        "cooperative_carl": (4500, "credit_card", "7823"),
        "combative_carmen": (6200, "personal_loan", "3341"),
        "evasive_eddie": (3100, "credit_card", "9156"),
        "confused_clara": (2800, "credit_card", "5502"),
        "distressed_dave": (5400, "auto_loan", "4478"),
    }
    debt, dtype, last4 = debt_map.get(persona.name, (4000, "credit_card", "0000"))
    name = persona.name.split("_")[1].capitalize()

    return Borrower(
        id=f"test-{persona.name}",
        name=name,
        account_last4=last4,
        total_debt=debt,
        debt_type=dtype,
        days_past_due=90,
        phone_number="+15551234567",
        email=f"{persona.name}@test.com",
    )


async def simulate_conversation(
    agent: BaseAgent,
    persona: BorrowerPersona,
    borrower: Borrower,
    handoff: HandoffSummary | None = None,
    max_turns: int = 10,
    cost_tracker: CostTracker | None = None,
    seed: int | None = None,
) -> Conversation:
    """Simulate a multi-turn conversation between an agent and a borrower persona."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    conversation = Conversation(
        borrower_id=borrower.id,
        agent_type=agent.agent_type,
        handoff_summary=handoff,
    )

    # Agent opening message
    opening = await agent.generate_opening(conversation, borrower, handoff)

    for turn in range(max_turns):
        # Borrower responds
        borrower_messages = [
            {"role": "system", "content": persona.system_prompt},
        ]
        # Add conversation history from borrower's perspective
        for msg in conversation.messages:
            if msg.role == "agent":
                borrower_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "borrower":
                borrower_messages.append({"role": "assistant", "content": msg.content})

        kwargs = {
            "model": settings.openai_model_mini,
            "messages": borrower_messages,
            "max_tokens": 200,
            "temperature": 0.8,
        }
        if seed is not None:
            kwargs["seed"] = seed + turn

        borrower_response = await client.chat.completions.create(**kwargs)
        borrower_text = borrower_response.choices[0].message.content or ""

        if cost_tracker:
            usage = borrower_response.usage
            if usage:
                cost_tracker.record(
                    f"sim_borrower_{agent.agent_type}",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    settings.openai_model_mini,
                )

        conversation.add_message("borrower", borrower_text)

        # Check if conversation should end (borrower signals end)
        if _should_end_conversation(borrower_text):
            break

        # Agent responds
        agent_msg = await agent.respond(conversation, borrower, handoff)

        if cost_tracker:
            # Approximate agent cost (we don't have exact usage from agent.respond)
            cost_tracker.record(
                f"sim_agent_{agent.agent_type}",
                500,  # Approximate input tokens
                agent_msg.token_count,
                settings.openai_model,
            )

        # Check if agent signals end
        if _agent_ending(agent_msg.content):
            break

    return conversation


async def simulate_pipeline(
    persona: BorrowerPersona,
    assessment_prompt: str | None = None,
    resolution_prompt: str | None = None,
    final_notice_prompt: str | None = None,
    cost_tracker: CostTracker | None = None,
    seed: int | None = None,
) -> PipelineResult:
    """Simulate the full 3-agent pipeline for a persona."""
    borrower = make_test_borrower(persona)
    result = PipelineResult()

    # Stage 1: Assessment
    assessment_agent = AssessmentAgent(system_prompt=assessment_prompt)
    conv1 = await simulate_conversation(
        assessment_agent, persona, borrower,
        max_turns=6, cost_tracker=cost_tracker, seed=seed,
    )
    conv1.outcome = "assessed"
    result.conversations.append(conv1)

    # Handoff 1→2
    handoff_1to2 = await summarize_for_handoff([conv1])
    if cost_tracker:
        cost_tracker.record("handoff_1to2", 300, handoff_1to2.token_count, settings.openai_model_mini)
    result.handoff_summaries.append(handoff_1to2)

    # Stage 2: Resolution (simulated as chat)
    resolution_agent = ResolutionAgent(system_prompt=resolution_prompt)
    conv2 = await simulate_conversation(
        resolution_agent, persona, borrower,
        handoff=handoff_1to2, max_turns=8,
        cost_tracker=cost_tracker, seed=(seed + 100 if seed else None),
    )
    result.conversations.append(conv2)

    # Check if deal was agreed
    borrower_msgs = [m for m in conv2.messages if m.role == "borrower"]
    deal_keywords = ["agree", "accept", "i'll pay", "deal", "go ahead", "set it up", "fine"]
    if borrower_msgs and any(kw in borrower_msgs[-1].content.lower() for kw in deal_keywords):
        conv2.outcome = "deal_agreed"
        result.final_outcome = "agreement"
        return result

    conv2.outcome = "no_deal"

    # Handoff 2→3
    handoff_2to3 = await summarize_for_handoff([conv1, conv2])
    if cost_tracker:
        cost_tracker.record("handoff_2to3", 500, handoff_2to3.token_count, settings.openai_model_mini)
    result.handoff_summaries.append(handoff_2to3)

    # Stage 3: Final Notice
    final_agent = FinalNoticeAgent(system_prompt=final_notice_prompt)
    conv3 = await simulate_conversation(
        final_agent, persona, borrower,
        handoff=handoff_2to3, max_turns=6,
        cost_tracker=cost_tracker, seed=(seed + 200 if seed else None),
    )
    result.conversations.append(conv3)

    # Check final outcome
    borrower_msgs3 = [m for m in conv3.messages if m.role == "borrower"]
    resolve_keywords = ["accept", "agree", "i'll pay", "fine", "go ahead"]
    if borrower_msgs3 and any(kw in borrower_msgs3[-1].content.lower() for kw in resolve_keywords):
        conv3.outcome = "resolved"
        result.final_outcome = "resolved"
    else:
        conv3.outcome = "no_resolution"
        result.final_outcome = "escalate"

    return result


def _should_end_conversation(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in [
        "goodbye", "hang up", "end this", "stop calling",
        "don't contact me", "leave me alone",
    ])


def _agent_ending(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in [
        "thank you for your time", "we'll be in touch",
        "this concludes", "goodbye", "end of conversation",
        "i'll note your account", "flag your account",
    ])
