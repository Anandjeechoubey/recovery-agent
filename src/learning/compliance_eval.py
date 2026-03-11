"""Compliance evaluation for the learning loop (cost-efficient version)."""

from __future__ import annotations

from src.agents.compliance import check_compliance_quick
from src.models.conversation import Conversation


async def evaluate_compliance(
    conversations: list[Conversation],
) -> tuple[float, list[list[dict]]]:
    """Evaluate compliance across a batch of conversations.

    Returns (compliance_rate, per_conversation_violations).
    Uses the fast rule-based checker to save costs during learning.
    """
    all_violations = []

    for conv in conversations:
        violations = await check_compliance_quick(conv)
        all_violations.append([
            {"rule": v.rule, "description": v.description, "message_index": v.message_index}
            for v in violations
        ])

    clean_count = sum(1 for v in all_violations if len(v) == 0)
    rate = clean_count / len(all_violations) if all_violations else 1.0

    return rate, all_violations
