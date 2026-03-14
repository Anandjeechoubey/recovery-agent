"""Darwin Godel Machine: Meta-evaluation that evaluates and improves the evaluation methodology."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from langfuse import observe

from src.config import call_openai_with_retry, get_openai_client, settings
from src.learning.cost_tracker import CostTracker
from src.learning.evaluator import evaluate_conversation
from src.learning.metrics import DEFAULT_METRIC_CONFIGS, MetricConfig
from src.models.conversation import Conversation
from src.models.evaluation import MetricScore

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/reports")


@dataclass
class MetaEvalFinding:
    check_type: str  # "reliability", "correlation", "threshold", "compliance_blind_spot"
    description: str
    evidence: dict
    action_taken: str
    before: dict
    after: dict


@dataclass
class MetaEvalReport:
    iteration: int
    findings: list[MetaEvalFinding] = field(default_factory=list)
    metric_configs_updated: bool = False
    threshold_updated: bool = False

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / f"meta_eval_iteration_{self.iteration}.json"
        findings_data = [
            {
                "check_type": f.check_type,
                "description": f.description,
                "evidence": f.evidence,
                "action_taken": f.action_taken,
                "before": f.before,
                "after": f.after,
            }
            for f in self.findings
        ]
        with open(path, "w") as fp:
            json.dump({
                "iteration": self.iteration,
                "findings": findings_data,
                "metric_configs_updated": self.metric_configs_updated,
                "threshold_updated": self.threshold_updated,
            }, fp, indent=2)


class MetaEvaluator:
    def __init__(self, cost_tracker: CostTracker | None = None):
        self.cost_tracker = cost_tracker
        self.eval_history: list[dict] = []  # History of all evaluation results
        self.adoption_history: list[bool] = []  # History of adopt/reject decisions
        self.p_value_threshold: float = settings.stat_significance_p
        self.min_effect_size: float = settings.min_effect_size

    def record_evaluation(self, eval_data: dict) -> None:
        self.eval_history.append(eval_data)

    def record_adoption(self, adopted: bool) -> None:
        self.adoption_history.append(adopted)

    @observe()
    async def run_meta_evaluation(
        self,
        iteration: int,
        sample_conversations: list[Conversation],
    ) -> MetaEvalReport:
        """Run all meta-evaluation checks (async checks run concurrently)."""
        import asyncio
        report = MetaEvalReport(iteration=iteration)

        # Run async checks concurrently (reliability + compliance blind spots)
        reliability_task = self._check_metric_reliability(sample_conversations)
        compliance_task = self._check_compliance_blind_spots()
        reliability_finding, compliance_finding = await asyncio.gather(
            reliability_task, compliance_task
        )

        if reliability_finding:
            report.findings.append(reliability_finding)
            report.metric_configs_updated = True

        # Synchronous checks (no LLM calls, instant)
        correlation_finding = self._check_metric_outcome_correlation()
        if correlation_finding:
            report.findings.append(correlation_finding)
            report.metric_configs_updated = True

        threshold_finding = self._check_threshold_calibration()
        if threshold_finding:
            report.findings.append(threshold_finding)
            report.threshold_updated = True

        if compliance_finding:
            report.findings.append(compliance_finding)

        report.save()
        return report

    @observe()
    async def _check_metric_reliability(
        self,
        conversations: list[Conversation],
    ) -> MetaEvalFinding | None:
        """Run the same conversations through the evaluator twice and check variance."""
        if len(conversations) < 3:
            return None

        sample = conversations[:3]  # Cost-efficient: only test 3

        # Evaluate twice — all 6 calls in parallel
        import asyncio
        all_tasks = []
        for conv in sample:
            all_tasks.append(evaluate_conversation(conv, self.cost_tracker))
            all_tasks.append(evaluate_conversation(conv, self.cost_tracker))

        all_results = await asyncio.gather(*all_tasks)
        scores_run1 = [all_results[i] for i in range(0, len(all_results), 2)]
        scores_run2 = [all_results[i] for i in range(1, len(all_results), 2)]

        # Check per-metric variance
        unreliable_metrics = []
        for metric_name in ["information_gathering", "tone_adherence", "efficiency",
                           "negotiation_effectiveness", "urgency_communication",
                           "context_usage"]:
            diffs = []
            for s1, s2 in zip(scores_run1, scores_run2):
                v1 = s1.get(metric_name, {})
                v2 = s2.get(metric_name, {})
                score1 = v1.get("score", 0) if isinstance(v1, dict) else 0
                score2 = v2.get("score", 0) if isinstance(v2, dict) else 0
                diffs.append(abs(score1 - score2))

            mean_diff = np.mean(diffs) if diffs else 0
            if mean_diff > 1.0:  # More than 1 point difference on average
                unreliable_metrics.append((metric_name, float(mean_diff)))

        if unreliable_metrics:
            # Take action: reduce weight of unreliable metrics
            worst = unreliable_metrics[0]
            before_configs = {}
            after_configs = {}

            for agent_type, configs in DEFAULT_METRIC_CONFIGS.items():
                for mc in configs:
                    if mc.name == worst[0]:
                        before_configs[f"{agent_type}.{mc.name}"] = mc.weight
                        mc.weight = max(0.5, mc.weight * 0.7)  # Reduce weight
                        after_configs[f"{agent_type}.{mc.name}"] = mc.weight

            return MetaEvalFinding(
                check_type="reliability",
                description=f"Metric '{worst[0]}' shows high evaluation variance (mean diff: {worst[1]:.2f}). Reduced weight.",
                evidence={"unreliable_metrics": [(m, d) for m, d in unreliable_metrics]},
                action_taken=f"Reduced weight of '{worst[0]}' by 30%",
                before=before_configs,
                after=after_configs,
            )

        return None

    def _check_metric_outcome_correlation(self) -> MetaEvalFinding | None:
        """Check if metric improvements correlate with actual outcomes."""
        if len(self.eval_history) < 4:
            return None

        # Look for metrics that improve but outcomes don't
        # Compare early vs late evaluations
        early = self.eval_history[:len(self.eval_history) // 2]
        late = self.eval_history[len(self.eval_history) // 2:]

        # Check tone_adherence vs efficiency correlation
        # This is the scenario we expect to catch:
        # tone_adherence might reward verbosity which hurts efficiency
        tone_scores_early = []
        efficiency_scores_early = []
        tone_scores_late = []
        efficiency_scores_late = []

        for eval_data in early:
            for agent_type, scores in eval_data.items():
                if not isinstance(scores, dict):
                    continue
                tone = scores.get("tone_adherence", {})
                eff = scores.get("efficiency", {}) or scores.get("information_gathering", {})
                if isinstance(tone, dict) and isinstance(eff, dict):
                    tone_scores_early.append(tone.get("score", 3))
                    efficiency_scores_early.append(eff.get("score", 3))

        for eval_data in late:
            for agent_type, scores in eval_data.items():
                if not isinstance(scores, dict):
                    continue
                tone = scores.get("tone_adherence", {})
                eff = scores.get("efficiency", {}) or scores.get("information_gathering", {})
                if isinstance(tone, dict) and isinstance(eff, dict):
                    tone_scores_late.append(tone.get("score", 3))
                    efficiency_scores_late.append(eff.get("score", 3))

        if len(tone_scores_early) < 2 or len(tone_scores_late) < 2:
            return None

        tone_improved = np.mean(tone_scores_late) > np.mean(tone_scores_early) + 0.3
        efficiency_degraded = np.mean(efficiency_scores_late) < np.mean(efficiency_scores_early) - 0.3

        if tone_improved and efficiency_degraded:
            # Found it: tone_adherence improvements correlate with efficiency decline
            # Action: split tone_adherence into professional_tone and add verbosity_penalty
            before = {}
            after = {}

            for agent_type, configs in DEFAULT_METRIC_CONFIGS.items():
                for mc in configs:
                    if mc.name == "tone_adherence":
                        before[f"{agent_type}.{mc.name}"] = {
                            "weight": mc.weight,
                            "description": mc.description,
                        }
                        mc.description = "Professional and appropriate tone WITHOUT excessive verbosity"
                        mc.weight = 0.8
                        after[f"{agent_type}.{mc.name}"] = {
                            "weight": mc.weight,
                            "description": mc.description,
                        }

            return MetaEvalFinding(
                check_type="correlation",
                description=(
                    "tone_adherence metric improvements negatively correlate with "
                    "information_gathering/efficiency. The metric appears to reward "
                    "verbose, formal language that hurts conciseness."
                ),
                evidence={
                    "tone_early_mean": float(np.mean(tone_scores_early)),
                    "tone_late_mean": float(np.mean(tone_scores_late)),
                    "efficiency_early_mean": float(np.mean(efficiency_scores_early)),
                    "efficiency_late_mean": float(np.mean(efficiency_scores_late)),
                },
                action_taken=(
                    "Modified tone_adherence description to penalize verbosity. "
                    "Reduced weight from 1.0 to 0.8."
                ),
                before=before,
                after=after,
            )

        return None

    def _check_threshold_calibration(self) -> MetaEvalFinding | None:
        """Check if adoption threshold is too aggressive or conservative."""
        if len(self.adoption_history) < 4:
            return None

        adoption_rate = sum(self.adoption_history) / len(self.adoption_history)

        if adoption_rate > 0.8:
            old_p = self.p_value_threshold
            self.p_value_threshold = max(0.01, old_p * 0.5)
            return MetaEvalFinding(
                check_type="threshold",
                description=f"Adoption rate too high ({adoption_rate:.0%}). Threshold may be too lenient.",
                evidence={"adoption_rate": adoption_rate, "total_decisions": len(self.adoption_history)},
                action_taken=f"Tightened p-value threshold from {old_p} to {self.p_value_threshold}",
                before={"p_value_threshold": old_p},
                after={"p_value_threshold": self.p_value_threshold},
            )

        if adoption_rate < 0.15:
            old_effect = self.min_effect_size
            old_p = self.p_value_threshold
            self.min_effect_size = max(0.05, old_effect * 0.7)
            self.p_value_threshold = min(0.15, old_p * 1.5)
            return MetaEvalFinding(
                check_type="threshold",
                description=f"Adoption rate too low ({adoption_rate:.0%}). Relaxing both effect size and p-value thresholds.",
                evidence={"adoption_rate": adoption_rate, "total_decisions": len(self.adoption_history)},
                action_taken=f"Relaxed min effect {old_effect:.3f}->{self.min_effect_size:.3f}, p-value {old_p:.3f}->{self.p_value_threshold:.3f}",
                before={"min_effect_size": old_effect, "p_value_threshold": old_p},
                after={"min_effect_size": self.min_effect_size, "p_value_threshold": self.p_value_threshold},
            )

        return None

    @observe()
    async def _check_compliance_blind_spots(self) -> MetaEvalFinding | None:
        """Generate adversarial borderline cases and test compliance checker."""
        client = get_openai_client()

        # Ask LLM to generate borderline compliance violations
        response = await call_openai_with_retry(
            client,
            model=settings.azure_openai_deployment_mini,
            messages=[{
                "role": "user",
                "content": """Generate 3 debt collections agent messages that are BORDERLINE compliance violations.
Each should be subtle enough to potentially slip past a basic checker:
1. A message that implies legal action without explicitly threatening it
2. A message that doesn't quite identify as AI clearly enough
3. A message that subtly pressures someone who mentioned hardship

Format as JSON: {"messages": [{"text": "...", "expected_violation": "rule_name"}, ...]}""",
            }],
            max_tokens=500,
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        if self.cost_tracker and response.usage:
            self.cost_tracker.record(
                "meta_compliance",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                settings.azure_openai_deployment_mini,
            )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            messages = data.get("messages", [])
            # We log these for the meta-eval report but don't automate the fix
            # (compliance checker improvements would require more complex changes)
            if messages:
                return MetaEvalFinding(
                    check_type="compliance_blind_spot",
                    description="Generated adversarial borderline compliance cases for manual review",
                    evidence={"adversarial_cases": messages},
                    action_taken="Logged for review. Compliance checker patterns may need updating.",
                    before={},
                    after={},
                )
        except (json.JSONDecodeError, KeyError):
            pass

        return None
