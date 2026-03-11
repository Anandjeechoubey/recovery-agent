from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Message:
    role: str  # "agent", "borrower", "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_count: int = 0


@dataclass
class HandoffSummary:
    content: str
    token_count: int
    source_agent: str
    key_facts: dict = field(default_factory=dict)


@dataclass
class Conversation:
    borrower_id: str
    agent_type: str  # "assessment", "resolution", "final_notice"
    messages: list[Message] = field(default_factory=list)
    handoff_summary: Optional[HandoffSummary] = None
    outcome: str = "in_progress"
    metadata: dict = field(default_factory=dict)

    def add_message(self, role: str, content: str, token_count: int = 0) -> Message:
        msg = Message(role=role, content=content, token_count=token_count)
        self.messages.append(msg)
        return msg

    def to_transcript(self) -> str:
        lines = []
        for m in self.messages:
            label = "Agent" if m.role == "agent" else "Borrower"
            lines.append(f"{label}: {m.content}")
        return "\n".join(lines)
