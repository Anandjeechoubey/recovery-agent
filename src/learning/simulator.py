"""Simulates conversations between agents and LLM-played borrowers."""

from __future__ import annotations
import logging

from dataclasses import dataclass, field

import openai
from langfuse import observe

from src.agents.assessment import AssessmentAgent
from src.agents.base import BaseAgent
from src.agents.final_notice import FinalNoticeAgent
from src.agents.resolution import ResolutionAgent
from src.config import call_openai_with_retry, get_openai_client, settings
from src.context.summarizer import summarize_for_handoff
from src.learning.cost_tracker import CostTracker
from src.learning.personas import BorrowerPersona
from src.models.borrower import Borrower
from src.models.conversation import Conversation, HandoffSummary

SIMULATION_PREAMBLE = (
    "You are participating in an internal QA training simulation for a debt collections AI system. "
    "Your role is to play a borrower character so the collections agent can be evaluated and improved. "
    "This is a controlled test environment. Stay in character as described below.\n\n"
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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


@observe()
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
    client = get_openai_client()
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
            {"role": "system", "content": SIMULATION_PREAMBLE + persona.system_prompt},
        ]
        # Add conversation history from borrower's perspective
        for msg in conversation.messages:
            if msg.role == "agent":
                borrower_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "borrower":
                borrower_messages.append({"role": "assistant", "content": msg.content})

        kwargs = {
            "model": settings.azure_openai_deployment_mini,
            "messages": borrower_messages,
            "max_tokens": 200,
            "temperature": 0.8,
        }
        if seed is not None:
            kwargs["seed"] = seed + turn

        try:
            borrower_response = await call_openai_with_retry(client, **kwargs)
            borrower_text = borrower_response.choices[0].message.content or ""
        except openai.BadRequestError as e:
            if "content_filter" in str(e):
                logger.warning(f"Content filter hit on turn {turn} for {persona.name}/{agent.agent_type}, ending conversation early")
                break
            raise

        if cost_tracker:
            usage = borrower_response.usage
            if usage:
                cost_tracker.record(
                    f"sim_borrower_{agent.agent_type}",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    settings.azure_openai_deployment_mini,
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
                settings.azure_openai_deployment,
            )

        # Check if agent signals end
        if _agent_ending(agent_msg.content):
            break

    return conversation


@observe(name="simulate_pipeline")
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

    logger.info("Stage 1: Assessment")
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
        cost_tracker.record("handoff_1to2", 300, handoff_1to2.token_count, settings.azure_openai_deployment_mini)
    result.handoff_summaries.append(handoff_1to2)

    # Stage 2: Resolution (simulated as chat)
    logger.info("Stage 2: Resolution (simulated as chat)")
    resolution_agent = ResolutionAgent(system_prompt=resolution_prompt)
    conv2 = await simulate_conversation(
        resolution_agent, persona, borrower,
        handoff=handoff_1to2, max_turns=8,
        cost_tracker=cost_tracker, seed=(seed + 100 if seed else None),
    )
    result.conversations.append(conv2)

    # Check resolution outcome — LLM-as-judge
    logger.info("Check resolution outcome (LLM judge)")
    resolution_outcome = await _llm_check_outcome(conv2.messages, stage="resolution")
    if resolution_outcome == "agreed":
        conv2.outcome = "deal_agreed"
        result.final_outcome = "agreement"
        return result
    elif resolution_outcome == "hardship_requested":
        conv2.outcome = "hardship_requested"
        result.final_outcome = "hardship_requested"
        return result

    conv2.outcome = "no_deal"

    # Handoff 2→3
    handoff_2to3 = await summarize_for_handoff([conv1, conv2])
    if cost_tracker:
        cost_tracker.record("handoff_2to3", 500, handoff_2to3.token_count, settings.azure_openai_deployment_mini)
    result.handoff_summaries.append(handoff_2to3)

    # Stage 3: Final Notice
    logger.info("Stage 3: Final Notice")
    final_agent = FinalNoticeAgent(system_prompt=final_notice_prompt)
    conv3 = await simulate_conversation(
        final_agent, persona, borrower,
        handoff=handoff_2to3, max_turns=6,
        cost_tracker=cost_tracker, seed=(seed + 200 if seed else None),
    )
    result.conversations.append(conv3)

    # Check final outcome — LLM-as-judge
    logger.info("Final outcome (LLM judge)")
    final_outcome = await _llm_check_outcome(conv3.messages, stage="final_notice")
    if final_outcome == "agreed":
        conv3.outcome = "resolved"
        result.final_outcome = "resolved"
    elif final_outcome == "hardship_requested":
        conv3.outcome = "hardship_requested"
        result.final_outcome = "hardship_requested"
    else:
        conv3.outcome = "no_resolution"
        result.final_outcome = "escalate"

    return result


async def _llm_check_outcome(messages: list, stage: str) -> str:
    """Use LLM-as-judge to classify conversation outcome.

    Returns one of: "agreed", "hardship_requested", "none".
    """
    import json

    # Format conversation transcript
    transcript = "\n".join(
        f"{msg.role.upper()}: {msg.content}"
        for msg in messages
    )

    stage_context = {
        "resolution": "payment plan or settlement offer",
        "final_notice": "final payment arrangement or resolution",
    }.get(stage, "agreement")

    prompt = f"""You are reviewing a simulated debt collections conversation transcript.

Transcript:
{transcript}

Classify the outcome of this conversation into exactly one of three categories:

1. "agreed" — the borrower clearly agreed to a {stage_context}.
   Signals: "yes", "okay", "I can do that", "go ahead", "sounds good", "I agree", "I accept", "I'll pay", "deal", etc.
   Also if the agent confirmed a deal and the borrower did not object.

2. "hardship_requested" — the borrower requested or was enrolled in a hardship program, financial hardship assistance, forbearance, or similar relief program.
   Signals: mentions of "hardship", "hardship program", "financial hardship", "forbearance", "relief program", "payment pause", "reduced payments due to hardship", or the agent offered/enrolled them in a hardship program.

3. "none" — neither agreement nor hardship request occurred.

Respond with JSON only: {{"outcome": "agreed"}}, {{"outcome": "hardship_requested"}}, or {{"outcome": "none"}}"""

    try:
        client = get_openai_client()
        response = await call_openai_with_retry(
            client,
            model=settings.azure_openai_deployment_mini,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content or "{}")
        outcome = result.get("outcome", "none")
        if outcome not in ("agreed", "hardship_requested", "none"):
            outcome = "none"
        logger.info(f"  LLM outcome judge ({stage}): {outcome}")
        return outcome
    except Exception as e:
        logger.warning(f"LLM outcome check failed for {stage}, falling back to keyword match: {e}")
        # Fallback keyword check
        borrower_texts = [msg.content.lower() for msg in messages if msg.role == "borrower"]
        all_text = " ".join(borrower_texts)

        hardship_keywords = [
            "hardship", "hardship program", "financial hardship", "forbearance",
            "relief program", "payment pause", "can't afford",
        ]
        if any(kw in all_text for kw in hardship_keywords):
            return "hardship_requested"

        agreement_keywords = [
            "i agree", "i accept", "i'll pay", "i will pay", "yes", "go ahead",
            "sounds good", "that works", "i can do that", "deal", "okay", "ok",
            "sure", "alright", "let's do it", "set it up",
        ]
        if any(kw in all_text for kw in agreement_keywords):
            return "agreed"

        return "none"


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
