from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from temporalio import activity

from src.agents.assessment import AssessmentAgent
from src.agents.final_notice import FinalNoticeAgent
from src.agents.resolution import ResolutionAgent
from src.context.summarizer import summarize_for_handoff
from src.models.borrower import Borrower
from src.models.conversation import Conversation, HandoffSummary, Message


@dataclass
class StageResult:
    agent_type: str
    outcome: str  # "assessed", "no_response", "deal_agreed", "no_deal", "resolved", "no_resolution"
    conversation: Conversation
    messages_json: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "outcome": self.outcome,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in self.conversation.messages
            ],
        }


class ConversationManager:
    """Manages real-time chat conversations via signals."""

    def __init__(self):
        self.pending_messages: asyncio.Queue[str] = asyncio.Queue()
        self.response_ready: asyncio.Event = asyncio.Event()
        self.latest_response: str = ""

    async def wait_for_message(self, timeout: float = 300.0) -> str | None:
        try:
            return await asyncio.wait_for(self.pending_messages.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def receive_message(self, message: str) -> None:
        self.pending_messages.put_nowait(message)


# Global conversation managers keyed by workflow_id
_managers: dict[str, ConversationManager] = {}


def get_manager(workflow_id: str) -> ConversationManager:
    if workflow_id not in _managers:
        _managers[workflow_id] = ConversationManager()
    return _managers[workflow_id]


def cleanup_manager(workflow_id: str) -> None:
    _managers.pop(workflow_id, None)


@activity.defn
async def run_assessment(
    borrower_dict: dict,
    workflow_id: str,
) -> dict:
    borrower = _dict_to_borrower(borrower_dict)
    agent = AssessmentAgent()
    conversation = Conversation(borrower_id=borrower.id, agent_type="assessment")
    manager = get_manager(workflow_id)

    # Agent opens
    opening = await agent.generate_opening(conversation, borrower)
    activity.logger.info(f"Assessment opening: {opening.content[:100]}")

    # Conversation loop
    no_response_count = 0
    max_turns = 10

    for _ in range(max_turns):
        activity.heartbeat()
        borrower_msg = await manager.wait_for_message(timeout=300.0)

        if borrower_msg is None:
            no_response_count += 1
            if no_response_count >= 2:
                conversation.outcome = "no_response"
                break
            follow_up = await agent.respond(conversation, borrower)
            activity.logger.info(f"Assessment follow-up: {follow_up.content[:100]}")
            continue

        no_response_count = 0
        conversation.add_message("borrower", borrower_msg)
        response = await agent.respond(conversation, borrower)
        activity.logger.info(f"Assessment response: {response.content[:100]}")

        # Check if assessment is complete (agent gathered enough info)
        if _assessment_complete(conversation):
            conversation.outcome = "assessed"
            break
    else:
        conversation.outcome = "assessed"

    return StageResult(
        agent_type="assessment",
        outcome=conversation.outcome,
        conversation=conversation,
    ).to_dict()


@activity.defn
async def run_resolution(
    borrower_dict: dict,
    handoff_dict: dict | None,
    workflow_id: str,
) -> dict:
    borrower = _dict_to_borrower(borrower_dict)
    handoff = _dict_to_handoff(handoff_dict) if handoff_dict else None
    agent = ResolutionAgent()
    conversation = Conversation(
        borrower_id=borrower.id,
        agent_type="resolution",
        handoff_summary=handoff,
    )
    manager = get_manager(workflow_id)

    # Agent opens (voice call simulation or live)
    opening = await agent.generate_opening(conversation, borrower, handoff)
    activity.logger.info(f"Resolution opening: {opening.content[:100]}")

    max_turns = 10
    for _ in range(max_turns):
        activity.heartbeat()
        borrower_msg = await manager.wait_for_message(timeout=300.0)

        if borrower_msg is None:
            conversation.outcome = "no_deal"
            break

        conversation.add_message("borrower", borrower_msg)
        response = await agent.respond(conversation, borrower, handoff)
        activity.logger.info(f"Resolution response: {response.content[:100]}")

        # Check for deal
        if _deal_agreed(conversation):
            conversation.outcome = "deal_agreed"
            break
    else:
        conversation.outcome = "no_deal"

    if conversation.outcome == "":
        conversation.outcome = "no_deal"

    return StageResult(
        agent_type="resolution",
        outcome=conversation.outcome,
        conversation=conversation,
    ).to_dict()


@activity.defn
async def run_final_notice(
    borrower_dict: dict,
    handoff_dict: dict | None,
    workflow_id: str,
) -> dict:
    borrower = _dict_to_borrower(borrower_dict)
    handoff = _dict_to_handoff(handoff_dict) if handoff_dict else None
    agent = FinalNoticeAgent()
    conversation = Conversation(
        borrower_id=borrower.id,
        agent_type="final_notice",
        handoff_summary=handoff,
    )
    manager = get_manager(workflow_id)

    opening = await agent.generate_opening(conversation, borrower, handoff)
    activity.logger.info(f"Final notice opening: {opening.content[:100]}")

    max_turns = 8
    for _ in range(max_turns):
        activity.heartbeat()
        borrower_msg = await manager.wait_for_message(timeout=600.0)

        if borrower_msg is None:
            conversation.outcome = "no_resolution"
            break

        conversation.add_message("borrower", borrower_msg)
        response = await agent.respond(conversation, borrower, handoff)
        activity.logger.info(f"Final notice response: {response.content[:100]}")

        if _resolved(conversation):
            conversation.outcome = "resolved"
            break
    else:
        conversation.outcome = "no_resolution"

    if conversation.outcome == "" or conversation.outcome == "in_progress":
        conversation.outcome = "no_resolution"

    return StageResult(
        agent_type="final_notice",
        outcome=conversation.outcome,
        conversation=conversation,
    ).to_dict()


@activity.defn
async def create_handoff(
    stage_results: list[dict],
    max_tokens: int = 500,
) -> dict | None:
    conversations = []
    for result in stage_results:
        conv = Conversation(
            borrower_id="",
            agent_type=result["agent_type"],
        )
        for msg_dict in result.get("messages", []):
            conv.add_message(msg_dict["role"], msg_dict["content"])
        conversations.append(conv)

    if not conversations:
        return None

    summary = await summarize_for_handoff(conversations, max_tokens)
    return {
        "content": summary.content,
        "token_count": summary.token_count,
        "source_agent": summary.source_agent,
    }


def _assessment_complete(conversation: Conversation) -> bool:
    """Heuristic: assessment is complete if we have 3+ agent messages
    (opening + 2 exchanges) and agent's last message indicates wrap-up."""
    agent_msgs = [m for m in conversation.messages if m.role == "agent"]
    if len(agent_msgs) < 3:
        return False
    last = agent_msgs[-1].content.lower()
    return any(kw in last for kw in [
        "thank you for", "i have the information", "next step",
        "someone will", "we'll be in touch", "that's all",
        "i'll pass this", "resolution team",
    ])


def _deal_agreed(conversation: Conversation) -> bool:
    borrower_msgs = [m for m in conversation.messages if m.role == "borrower"]
    if not borrower_msgs:
        return False
    last = borrower_msgs[-1].content.lower()
    return any(kw in last for kw in [
        "i agree", "i accept", "i'll pay", "i will pay", "let's do it",
        "deal", "ok i'll do", "fine i'll", "yes", "go ahead",
        "i can do that", "set it up", "sign me up",
    ])


def _resolved(conversation: Conversation) -> bool:
    borrower_msgs = [m for m in conversation.messages if m.role == "borrower"]
    if not borrower_msgs:
        return False
    last = borrower_msgs[-1].content.lower()
    return any(kw in last for kw in [
        "i accept", "i agree", "i'll take", "fine", "ok deal",
        "i'll pay", "i will pay", "let's do", "go ahead",
    ])


def _dict_to_borrower(d: dict) -> Borrower:
    from src.models.borrower import PolicyRanges
    policy_data = d.get("policy", {})
    policy = PolicyRanges(
        min_settlement_pct=policy_data.get("min_settlement_pct", 0.4),
        max_settlement_pct=policy_data.get("max_settlement_pct", 0.8),
        max_installments=policy_data.get("max_installments", 12),
        hardship_program=policy_data.get("hardship_program", True),
    )
    return Borrower(
        id=d["id"],
        name=d["name"],
        account_last4=d["account_last4"],
        total_debt=d["total_debt"],
        debt_type=d["debt_type"],
        days_past_due=d["days_past_due"],
        phone_number=d.get("phone_number", ""),
        email=d.get("email", ""),
        policy=policy,
    )


def _dict_to_handoff(d: dict) -> HandoffSummary:
    return HandoffSummary(
        content=d["content"],
        token_count=d["token_count"],
        source_agent=d["source_agent"],
    )
