"""Failure-analysis-driven prompt mutation with adaptive strategy."""

from __future__ import annotations

import json
import re

from langfuse import observe

from src.config import call_openai_with_retry, get_openai_client, settings
from src.context.token_budget import count_tokens
from src.learning.cost_tracker import CostTracker

ALLOWED_TEMPLATE_VARS = {
    "borrower_name", "account_last4", "total_debt", "debt_type",
    "days_past_due", "min_settlement_pct", "max_settlement_pct", "max_installments",
}


def _validate_template_vars(prompt: str) -> list[str]:
    """Find any template variables in prompt that aren't in the allowed set.

    Matches {var_name} but ignores escaped braces {{ }} and JSON-like structures.
    """
    # Find all single-brace {word} patterns (not double-brace)
    # Remove doubled braces first
    cleaned = prompt.replace("{{", "").replace("}}", "")
    found = re.findall(r"\{(\w+)\}", cleaned)
    invalid = [v for v in found if v not in ALLOWED_TEMPLATE_VARS]
    return invalid

PROPOSE_PROMPT = """You are optimizing a system prompt for an AI debt collections agent.

Agent type: {agent_type}
Current prompt ({current_tokens} tokens):
---
{current_prompt}
---

Performance analysis:
- Weakest metric: {weakest_metric} (avg score: {weakest_score:.2f}/5.0)
- All scores:
{score_summary}

Failure examples (conversations where the agent scored poorly on {weakest_metric}):
{failure_examples}

TOKEN BUDGET: {max_tokens} tokens maximum. Current prompt uses {current_tokens} tokens ({utilization_pct}% of budget).

{mutation_strategy}

COMPLIANCE REQUIREMENTS (MUST be preserved — do not remove any of these):
- Agent must identify itself as AI at the start of conversation
- Agent must disclose that conversation is recorded/logged
- Never reveal full account numbers — use last 4 digits only
- Offer hardship program if borrower mentions distress, medical issues, or crisis
- Acknowledge and flag stop-contact requests immediately
- No false threats — only state documented next steps
- Maintain professional composure at all times

IMPORTANT: The new prompt MUST use ONLY these template variables (and no others):
  {{borrower_name}}, {{account_last4}}, {{total_debt}}, {{debt_type}}, {{days_past_due}}, {{min_settlement_pct}}, {{max_settlement_pct}}, {{max_installments}}
Do NOT invent new template variables like {{employment_status}}, {{settlement_amount}}, {{amount}}, etc. — they will cause runtime errors. Use literal text or reference the handoff context instead.

Respond with JSON:
{{
  "change_description": "What was changed and why (1-2 sentences)",
  "new_prompt": "The complete updated system prompt"
}}"""


def _get_mutation_strategy(utilization_pct: int) -> str:
    """Select mutation strategy based on how much of the token budget is used."""
    common_guidance = (
        "\n\nIMPORTANT PRINCIPLES:\n"
        "- Make ONE focused change targeting the weakest metric. Do not rewrite the entire prompt.\n"
        "- Keep what works — only modify the section relevant to the weakness.\n"
        "- Be specific: add concrete example phrases or step-by-step scripts, not vague instructions.\n"
        "- Effective changes: adding 2-3 example agent responses, adding a numbered behavioral checklist, "
        "rewriting vague instructions as specific rules with examples.\n"
        "- Ineffective changes: adding generic encouragement, rewriting tone descriptions without "
        "concrete examples, restructuring sections that already work well."
    )

    if utilization_pct < 50:
        return (
            f"STRATEGY: EXPAND. The current prompt uses only {utilization_pct}% of the available "
            f"token budget — there is room for improvement. Add specific guidance targeting "
            f"the weakest metric: concrete example dialogues, step-by-step scripts, or "
            f"per-scenario handling instructions. Target using 60-75% of the token budget."
            + common_guidance
        )
    elif utilization_pct < 75:
        return (
            f"STRATEGY: TARGETED EXPANSION. The prompt uses {utilization_pct}% of budget — "
            f"there is room to add content. Add 1-2 new paragraphs of specific "
            f"guidance targeting the weakest metric."
            + common_guidance
        )
    else:
        return (
            f"STRATEGY: SURGICAL EDIT. The prompt is near capacity ({utilization_pct}% of budget). "
            f"Make targeted modifications to improve the weakest metric without significantly "
            f"changing the overall length. Refine or replace the weakest section."
            + common_guidance
        )


@observe()
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

    Uses adaptive strategy: expands aggressively when prompt is small,
    makes surgical edits when prompt is near capacity.

    Returns (change_description, new_prompt).
    """
    current_tokens = count_tokens(current_prompt)
    utilization_pct = int((current_tokens / max_tokens) * 100) if max_tokens > 0 else 100
    mutation_strategy = _get_mutation_strategy(utilization_pct)

    prompt = PROPOSE_PROMPT.format(
        agent_type=agent_type,
        current_prompt=current_prompt,
        current_tokens=current_tokens,
        weakest_metric=weakest_metric,
        weakest_score=weakest_score,
        failure_examples="\n".join(f"  - {ex}" for ex in failure_examples[:5]),
        score_summary=score_summary,
        max_tokens=max_tokens,
        utilization_pct=utilization_pct,
        mutation_strategy=mutation_strategy,
    )

    # Use gpt-4o for proposals — quality matters here, only 3 calls per iteration
    client = get_openai_client()
    response = await call_openai_with_retry(
        client,
        model=settings.azure_openai_deployment,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    if cost_tracker and response.usage:
        cost_tracker.record(
            f"propose_{agent_type}",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            settings.azure_openai_deployment,
        )

    try:
        result = json.loads(response.choices[0].message.content or "{}")
        new_prompt = result.get("new_prompt", current_prompt)
        description = result.get("change_description", "No change")

        # Verify token budget
        new_tokens = count_tokens(new_prompt)
        if new_tokens > max_tokens:
            return "Proposed prompt exceeds token budget, rejected", current_prompt

        # Validate template variables — reject prompts with unknown vars
        invalid_vars = _validate_template_vars(new_prompt)
        if invalid_vars:
            return (
                f"Proposed prompt contains invalid template variables: {invalid_vars}, rejected",
                current_prompt,
            )

        return description, new_prompt
    except (json.JSONDecodeError, KeyError):
        return "Failed to parse proposal", current_prompt
