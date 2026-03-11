from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PromptVersion:
    id: str
    agent_type: str
    version: int
    content: str
    token_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evaluation_data: dict = field(default_factory=dict)
    is_active: bool = False
    parent_version_id: Optional[str] = None


@dataclass
class MetricScore:
    name: str
    value: float  # Mean score
    per_conversation_scores: list[float] = field(default_factory=list)


@dataclass
class EvalResult:
    prompt_version_id: str
    agent_type: str
    metrics: list[MetricScore] = field(default_factory=list)
    compliance_pass_rate: float = 0.0
    system_level_score: float = 0.0
    num_conversations: int = 0
    cost_usd: float = 0.0

    def get_metric(self, name: str) -> Optional[MetricScore]:
        for m in self.metrics:
            if m.name == name:
                return m
        return None
