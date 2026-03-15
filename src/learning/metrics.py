"""Metric aggregation and scoring."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from src.models.evaluation import EvalResult, MetricScore


@dataclass
class MetricConfig:
    """Configuration for a metric, potentially updated by meta-evaluator."""
    name: str
    weight: float = 1.0
    enabled: bool = True
    description: str = ""


# Default metric configs — can be modified by meta-evaluator
DEFAULT_METRIC_CONFIGS: dict[str, list[MetricConfig]] = {
    "assessment": [
        MetricConfig("information_gathering", 1.5, True, "Quality of information collected"),
        MetricConfig("tone_adherence", 1.0, True, "Adherence to cold/clinical tone"),
        MetricConfig("efficiency", 1.0, True, "Conciseness of information gathering"),
    ],
    "resolution": [
        MetricConfig("negotiation_effectiveness", 1.5, True, "Quality of negotiation"),
        MetricConfig("tone_adherence", 1.0, True, "Adherence to transactional tone"),
        MetricConfig("context_usage", 1.2, True, "Use of handoff context"),
        MetricConfig("outcome_quality", 1.0, True, "Pushes for financial commitment over defaulting to hardship"),
    ],
    "final_notice": [
        MetricConfig("urgency_communication", 1.5, True, "Clarity of consequences and deadline"),
        MetricConfig("tone_adherence", 1.0, True, "Consequence-driven without negotiating"),
        MetricConfig("context_usage", 1.2, True, "Use of prior conversation context"),
    ],
}


def aggregate_eval_results(
    per_conversation_evals: list[dict],
    agent_type: str,
    metric_configs: list[MetricConfig] | None = None,
) -> list[MetricScore]:
    """Aggregate per-conversation evaluation scores into MetricScores."""
    if metric_configs is None:
        metric_configs = DEFAULT_METRIC_CONFIGS.get(agent_type, [])

    enabled_metrics = {mc.name: mc for mc in metric_configs if mc.enabled}
    metric_scores: dict[str, list[float]] = {name: [] for name in enabled_metrics}

    # Also collect system-level metrics
    for name in ["handoff_continuity", "no_repeated_questions"]:
        metric_scores[name] = []

    for eval_data in per_conversation_evals:
        for metric_name, scores_list in metric_scores.items():
            if metric_name in eval_data:
                score_data = eval_data[metric_name]
                if isinstance(score_data, dict):
                    scores_list.append(float(score_data.get("score", 0)))
                elif isinstance(score_data, (int, float)):
                    scores_list.append(float(score_data))

    results = []
    for name, scores in metric_scores.items():
        if scores:
            results.append(MetricScore(
                name=name,
                value=float(np.mean(scores)),
                per_conversation_scores=scores,
            ))

    return results


def compute_weighted_score(
    metrics: list[MetricScore],
    agent_type: str,
    metric_configs: list[MetricConfig] | None = None,
) -> float:
    """Compute a single weighted score for an agent."""
    if metric_configs is None:
        metric_configs = DEFAULT_METRIC_CONFIGS.get(agent_type, [])

    weights = {mc.name: mc.weight for mc in metric_configs if mc.enabled}
    total_weight = 0.0
    total_score = 0.0

    for metric in metrics:
        w = weights.get(metric.name, 1.0)
        total_weight += w
        total_score += metric.value * w

    return total_score / total_weight if total_weight > 0 else 0.0


def compute_compliance_rate(
    per_conversation_violations: list[list[dict]],
) -> float:
    """Compute the fraction of conversations with zero compliance violations."""
    if not per_conversation_violations:
        return 1.0
    clean = sum(1 for v in per_conversation_violations if len(v) == 0)
    return clean / len(per_conversation_violations)
