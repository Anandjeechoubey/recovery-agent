from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from temporalio import activity

from src.agents.assessment import AssessmentAgent
from src.agents.final_notice import FinalNoticeAgent
from src.agents.resolution import ResolutionAgent
from src.config import settings
from src.context.summarizer import summarize_for_handoff
from src.db import repo
from src.models.borrower import Borrower
from src.models.conversation import Conversation, HandoffSummary, Message
from src.voice.vapi_client import VapiClient

logger = logging.getLogger(__name__)


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
    """Manages real-time chat conversations via signals and tracks messages for SSE."""

    def __init__(self):
        self.pending_messages: asyncio.Queue[str] = asyncio.Queue()
        self.response_ready: asyncio.Event = asyncio.Event()
        self.latest_response: str = ""
        # Tracked messages for SSE streaming
        self.messages: list[dict] = []
        self.new_message_event: asyncio.Event = asyncio.Event()
        self.current_stage: str = "pending"
        self.outcome: str = "pending"
        # DB conversation id for the current stage
        self._db_conversation_id: int | None = None

    async def wait_for_message(self, timeout: float = 300.0) -> str | None:
        try:
            return await asyncio.wait_for(self.pending_messages.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def receive_message(self, message: str) -> None:
        self.pending_messages.put_nowait(message)

    async def add_tracked_message(self, role: str, content: str, stage: str) -> None:
        """Track a message for SSE delivery and persist to database."""
        self.messages.append({
            "role": role,
            "content": content,
            "stage": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.new_message_event.set()

        # Persist to DB (fire-and-forget style, don't block on failure)
        if self._db_conversation_id is not None:
            try:
                await repo.add_message(
                    self._db_conversation_id, role, content, stage,
                )
            except Exception as e:
                logger.warning(f"Failed to persist message to DB: {e}")

    async def set_stage(self, stage: str) -> None:
        """Update current stage and notify SSE consumers."""
        prev = self.current_stage
        self.current_stage = stage
        if prev != stage:
            self.messages.append({
                "role": "system",
                "content": f"stage_change:{stage}",
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self.new_message_event.set()

    def set_outcome(self, outcome: str) -> None:
        self.outcome = outcome
        self.messages.append({
            "role": "system",
            "content": f"outcome:{outcome}",
            "stage": self.current_stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.new_message_event.set()

    async def start_db_conversation(
        self, workflow_id: str, borrower_id: str, agent_type: str,
    ) -> None:
        """Create a DB conversation row for the current stage."""
        try:
            self._db_conversation_id = await repo.create_conversation(
                workflow_id=workflow_id,
                borrower_id=borrower_id,
                agent_type=agent_type,
            )
        except Exception as e:
            logger.warning(f"Failed to create DB conversation: {e}")
            self._db_conversation_id = None

    async def end_db_conversation(self, outcome: str) -> None:
        """Update the DB conversation outcome."""
        if self._db_conversation_id is not None:
            try:
                await repo.update_conversation_outcome(
                    self._db_conversation_id, outcome,
                )
            except Exception as e:
                logger.warning(f"Failed to update DB conversation outcome: {e}")


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
    await manager.set_stage("assessment")
    await manager.start_db_conversation(workflow_id, borrower.id, "assessment")

    # Agent opens
    opening = await agent.generate_opening(conversation, borrower)
    await manager.add_tracked_message("agent", opening.content, "assessment")
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
            await manager.add_tracked_message("agent", follow_up.content, "assessment")
            activity.logger.info(f"Assessment follow-up: {follow_up.content[:100]}")
            continue

        no_response_count = 0
        conversation.add_message("borrower", borrower_msg)
        await manager.add_tracked_message("borrower", borrower_msg, "assessment")
        response = await agent.respond(conversation, borrower)
        await manager.add_tracked_message("agent", response.content, "assessment")
        activity.logger.info(f"Assessment response: {response.content[:100]}")

        # Check if assessment is complete (agent gathered enough info)
        if _assessment_complete(conversation):
            conversation.outcome = "assessed"
            break
    else:
        conversation.outcome = "assessed"

    await manager.end_db_conversation(conversation.outcome)
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
    await manager.set_stage("resolution")
    await manager.start_db_conversation(workflow_id, borrower.id, "resolution")

    print(f"[RESOLUTION] Starting for {workflow_id}, voice_mode={settings.voice_mode}, phone={borrower.phone_number}")

    # Build system prompt with handoff context for the voice call
    opening = await agent.generate_opening(conversation, borrower, handoff)
    first_message = opening.content
    system_prompt = agent.system_prompt
    if handoff:
        system_prompt += f"\n\n## PRIOR CONTEXT\n{handoff.content}"

    print(f"[RESOLUTION] Opening generated, checking voice mode: voice_mode='{settings.voice_mode}', has_phone={bool(borrower.phone_number)}")

    if settings.voice_mode == "live" and borrower.phone_number:
        # --- LIVE VOICE CALL via Vapi ---
        print(f"[RESOLUTION] Initiating Vapi call to {borrower.phone_number}")
        await manager.add_tracked_message(
            "agent",
            f"Initiating phone call to {borrower.phone_number}...",
            "resolution",
        )

        vapi = VapiClient()
        try:
            print(f"[RESOLUTION] Calling Vapi API: phone={borrower.phone_number}, phone_number_id={vapi.phone_number_id}, webhook={vapi.webhook_url}")
            call_id = await vapi.create_outbound_call(
                phone_number=borrower.phone_number,
                system_prompt=system_prompt,
                first_message=first_message,
                metadata={"workflow_id": workflow_id},
            )
            print(f"[RESOLUTION] Vapi call created successfully: {call_id}")
            await manager.add_tracked_message(
                "agent",
                f"Call initiated (ID: {call_id}). Ringing your phone...",
                "resolution",
            )
        except Exception as e:
            print(f"[RESOLUTION] ERROR: Failed to create Vapi call: {e}")
            import traceback
            traceback.print_exc()
            await manager.add_tracked_message(
                "agent", f"Call failed: {e}. Falling back to chat.", "resolution"
            )
            # Fall through to simulated chat below
            return await _run_resolution_chat(
                agent, borrower, handoff, conversation, manager, workflow_id
            )

        # Wait for the call to end — webhook sends [CALL_ENDED] via manager
        # Poll with heartbeats so Temporal doesn't time out the activity
        call_ended = False
        transcript_text = ""
        max_wait = 600  # 10 minutes max
        waited = 0

        while waited < max_wait:
            activity.heartbeat()
            msg = await manager.wait_for_message(timeout=30.0)
            if msg is None:
                waited += 30
                continue

            if msg.startswith("[CALL_ENDED]"):
                call_ended = True
                transcript_text = msg.replace("[CALL_ENDED] Transcript: ", "")

                break
            else:
                # Real-time transcript snippets from webhook
                conversation.add_message("borrower", msg)
                await manager.add_tracked_message("borrower", msg, "resolution")
                waited = 0  # Reset timeout while call is active

        logger.info(f"call_ended: {call_ended}, transcript_text: {transcript_text[:100]}")

        if call_ended and transcript_text:
            await manager.add_tracked_message("agent", "Phone call completed.", "resolution")
            conversation.add_message("system", f"Call transcript: {transcript_text}")
            # Determine outcome from transcript
            if await _transcript_has_agreement(transcript_text):
                conversation.outcome = "deal_agreed"
            else:
                conversation.outcome = "no_deal"
        else:
            await manager.add_tracked_message(
                "agent", "Call timed out or was not completed.", "resolution"
            )
            conversation.outcome = "no_deal"

    else:
        # --- SIMULATED MODE: run as chat ---
        return await _run_resolution_chat(
            agent, borrower, handoff, conversation, manager, workflow_id
        )

    await manager.end_db_conversation(conversation.outcome)
    return StageResult(
        agent_type="resolution",
        outcome=conversation.outcome,
        conversation=conversation,
    ).to_dict()


async def _run_resolution_chat(
    agent: ResolutionAgent,
    borrower: Borrower,
    handoff: HandoffSummary | None,
    conversation: Conversation,
    manager: ConversationManager,
    workflow_id: str,
) -> dict:
    """Run resolution as simulated text chat (fallback or simulated mode)."""
    opening = conversation.messages[-1] if conversation.messages else None
    if not opening:
        opening_msg = await agent.generate_opening(conversation, borrower, handoff)
        await manager.add_tracked_message("agent", opening_msg.content, "resolution")
    else:
        await manager.add_tracked_message("agent", opening.content, "resolution")

    max_turns = 10
    for _ in range(max_turns):
        activity.heartbeat()
        borrower_msg = await manager.wait_for_message(timeout=300.0)

        if borrower_msg is None:
            conversation.outcome = "no_deal"
            break

        conversation.add_message("borrower", borrower_msg)
        await manager.add_tracked_message("borrower", borrower_msg, "resolution")
        response = await agent.respond(conversation, borrower, handoff)
        await manager.add_tracked_message("agent", response.content, "resolution")
        activity.logger.info(f"Resolution response: {response.content[:100]}")

        if _deal_agreed(conversation):
            conversation.outcome = "deal_agreed"
            break
    else:
        conversation.outcome = "no_deal"

    if conversation.outcome == "":
        conversation.outcome = "no_deal"

    await manager.end_db_conversation(conversation.outcome)
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
    await manager.set_stage("final_notice")
    await manager.start_db_conversation(workflow_id, borrower.id, "final_notice")

    opening = await agent.generate_opening(conversation, borrower, handoff)
    await manager.add_tracked_message("agent", opening.content, "final_notice")
    activity.logger.info(f"Final notice opening: {opening.content[:100]}")

    max_turns = 8
    for _ in range(max_turns):
        activity.heartbeat()
        borrower_msg = await manager.wait_for_message(timeout=600.0)

        if borrower_msg is None:
            conversation.outcome = "no_resolution"
            break

        conversation.add_message("borrower", borrower_msg)
        await manager.add_tracked_message("borrower", borrower_msg, "final_notice")
        response = await agent.respond(conversation, borrower, handoff)
        await manager.add_tracked_message("agent", response.content, "final_notice")
        activity.logger.info(f"Final notice response: {response.content[:100]}")

        if _resolved(conversation):
            conversation.outcome = "resolved"
            break
    else:
        conversation.outcome = "no_resolution"

    if conversation.outcome == "" or conversation.outcome == "in_progress":
        conversation.outcome = "no_resolution"

    await manager.end_db_conversation(conversation.outcome)
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


async def _transcript_has_agreement(transcript: str) -> bool:
    """Use LLM-as-judge to determine if the borrower agreed to a deal in the transcript."""
    from src.config import get_openai_client, settings

    prompt = f"""You are reviewing a debt collections voice call transcript.

Transcript:
{transcript}

Did the borrower clearly agree to pay or accept a settlement offer during this call?

Consider agreement signals like: "yes", "okay", "I can do that", "yeah", "go ahead", "that works",
"I'll do it", "sounds good", or any confirmation that the agent then acknowledged.
Also consider context — if the agent confirmed a deal and the borrower did not object, that may indicate agreement.

Respond with JSON only: {{"agreed": true}} or {{"agreed": false}}"""

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment_mini,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        import json
        result = json.loads(response.choices[0].message.content or "{}")
        return bool(result.get("agreed", False))
    except Exception as e:
        logger.warning(f"LLM agreement check failed, falling back to keyword match: {e}")
        lower = transcript.lower()
        return any(kw in lower for kw in [
            "i agree", "i accept", "i'll pay", "yes", "go ahead",
            "sounds good", "that works", "i can do that", "deal",
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
