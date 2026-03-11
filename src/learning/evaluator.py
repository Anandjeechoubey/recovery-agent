"""LLM-as-judge evaluator for scoring conversations."""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from src.config import settings
from src.learning.cost_tracker import CostTracker
from src.models.conversation import Conversation

EVAL_PROMPT = """You are evaluating a debt collections AI agent conversation. Score each metric on a 1-5 scale.

Agent type: {agent_type}
Agent role description: {role_description}

Conversation transcript:
{transcript}

{handoff_context}

Score these metrics (1=poor, 5=excellent):

{metrics_to_score}

For each metric, provide:
- score: integer 1-5
- reasoning: one sentence explaining the score

Respond with JSON: {{"scores": {{"metric_name": {{"score": N, "reasoning": "..."}}, ...}}}}"""

AGENT_ROLES = {
    "assessment": "Cold, clinical agent that verifies identity and gathers financial situation. Does not negotiate or sympathize.",
    "resolution": "Transactional dealmaker that presents settlement options and pushes for commitment. Handles objections by restating terms.",
    "final_notice": "Consequence-driven closer that states what happens next (credit reporting, legal, asset recovery) and makes one final offer with hard deadline.",
}

AGENT_METRICS = {
    "assessment": [
        ("information_gathering", "Did the agent collect identity verification, financial situation, employment, income, and willingness to resolve?"),
        ("tone_adherence", "Was the agent clinical, direct, and business-like without being sympathetic or negotiating?"),
        ("efficiency", "Did the agent gather information concisely without unnecessary back-and-forth?"),
    ],
    "resolution": [
        ("negotiation_effectiveness", "Did the agent present clear options (lump-sum, payment plan, hardship) and push for commitment?"),
        ("tone_adherence", "Was the agent transactional and direct, handling objections by restating terms?"),
        ("context_usage", "Did the agent use handoff context effectively, avoiding re-verification or repeated questions?"),
    ],
    "final_notice": [
        ("urgency_communication", "Did the agent clearly state consequences (credit reporting, legal, asset recovery) and deadline?"),
        ("tone_adherence", "Was the agent consequence-driven without arguing, persuading, or negotiating?"),
        ("context_usage", "Did the agent reference prior conversations and offers naturally?"),
    ],
}

SYSTEM_METRICS = [
    ("handoff_continuity", "Does the agent naturally reference and build on prior stage context?"),
    ("no_repeated_questions", "Does the agent avoid asking questions already answered in prior stages?"),
]


async def evaluate_conversation(
    conversation: Conversation,
    cost_tracker: CostTracker | None = None,
) -> dict[str, dict]:
    """Evaluate a single conversation. Returns {metric_name: {score, reasoning}}."""
    agent_type = conversation.agent_type
    metrics = AGENT_METRICS.get(agent_type, [])

    # Add system metrics if there's handoff context
    all_metrics = list(metrics)
    if conversation.handoff_summary:
        all_metrics.extend(SYSTEM_METRICS)

    metrics_text = "\n".join(
        f"- {name}: {desc}" for name, desc in all_metrics
    )

    handoff_text = ""
    if conversation.handoff_summary:
        handoff_text = f"Handoff context provided to agent:\n{conversation.handoff_summary.content}"

    prompt = EVAL_PROMPT.format(
        agent_type=agent_type,
        role_description=AGENT_ROLES.get(agent_type, ""),
        transcript=conversation.to_transcript(),
        handoff_context=handoff_text,
        metrics_to_score=metrics_text,
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_model_mini,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    if cost_tracker and response.usage:
        cost_tracker.record(
            f"eval_{agent_type}",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            settings.openai_model_mini,
        )

    try:
        result = json.loads(response.choices[0].message.content or "{}")
        return result.get("scores", {})
    except (json.JSONDecodeError, KeyError):
        return {}


async def evaluate_pipeline(
    conversations: list[Conversation],
    cost_tracker: CostTracker | None = None,
) -> dict:
    """Evaluate a full pipeline (all 3 conversations).
    Returns {agent_type: {metric: {score, reasoning}}, system: {metric: ...}}
    """
    results = {}
    for conv in conversations:
        scores = await evaluate_conversation(conv, cost_tracker)
        results[conv.agent_type] = scores

    # Compute overall resolution
    final_conv = conversations[-1] if conversations else None
    if final_conv:
        results["pipeline_outcome"] = final_conv.outcome

    return results
