"""Failure-analysis-driven prompt mutation."""

from __future__ import annotations

import json

from src.config import get_openai_client, settings
from src.context.token_budget import count_tokens
from src.learning.cost_tracker import CostTracker

PROPOSE_PROMPT = """You are optimizing a system prompt for an AI debt collections agent.

Agent type: {agent_type}
Current prompt (token count: {current_tokens}):
---
{current_prompt}
---

Performance analysis of current prompt:
- Weakest metric: {weakest_metric} (avg score: {weakest_score:.2f}/5)
- Failure examples:
{failure_examples}

Overall scores:
{score_summary}

TOKEN BUDGET: The new prompt must be under {max_tokens} tokens. Current is {current_tokens}.

COMPLIANCE REQUIREMENTS (MUST be preserved in the new prompt):
- Agent must identify itself as AI
- Agent must disclose that conversation is recorded/logged
- Never reveal full account numbers
- Offer hardship program if borrower mentions distress
- Acknowledge and flag stop-contact requests
- No false threats
- Professional composure

Propose a TARGETED modification to the current prompt that addresses the weakest metric.
Do NOT rewrite the entire prompt. Make the minimum change needed.
Explain what you changed and why in 1-2 sentences, then provide the full updated prompt.

Respond with JSON:
{{
  "change_description": "What was changed and why",
  "new_prompt": "The full updated system prompt"
}}"""


async def propose_prompt_mutation(
    agent_type: str,
    current_prompt: str,
    weakest_metric: str,
    weakest_score: float,
    failure_examples: list[str],
    score_summary: str,
    max_tokens: int = 2000,
    cost_tracker: CostTracker | None = None,
) -> tuple[str, str]:
    """Propose a prompt mutation targeting the weakest metric.

    Returns (change_description, new_prompt).
    """
    current_tokens = count_tokens(current_prompt)

    prompt = PROPOSE_PROMPT.format(
        agent_type=agent_type,
        current_prompt=current_prompt,
        current_tokens=current_tokens,
        weakest_metric=weakest_metric,
        weakest_score=weakest_score,
        failure_examples="\n".join(f"  - {ex}" for ex in failure_examples[:3]),
        score_summary=score_summary,
        max_tokens=max_tokens,
    )

    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment_mini,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    if cost_tracker and response.usage:
        cost_tracker.record(
            f"propose_{agent_type}",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            settings.azure_openai_deployment_mini,
        )

    try:
        result = json.loads(response.choices[0].message.content or "{}")
        new_prompt = result.get("new_prompt", current_prompt)
        description = result.get("change_description", "No change")

        # Verify token budget
        new_tokens = count_tokens(new_prompt)
        if new_tokens > max_tokens:
            return "Proposed prompt exceeds token budget, rejected", current_prompt

        return description, new_prompt
    except (json.JSONDecodeError, KeyError):
        return "Failed to parse proposal", current_prompt
