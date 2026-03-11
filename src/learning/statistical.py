"""Statistical testing for prompt comparison."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class ComparisonResult:
    metric_name: str
    baseline_mean: float
    candidate_mean: float
    effect_size: float
    p_value: float
    ci_lower: float
    ci_upper: float
    is_significant: bool
    recommendation: str  # "adopt", "reject", "inconclusive"


def wilcoxon_compare(
    baseline_scores: list[float],
    candidate_scores: list[float],
    alpha: float = 0.05,
    min_effect: float = 0.2,
    metric_name: str = "",
) -> ComparisonResult:
    """Compare two sets of paired scores using Wilcoxon signed-rank test.

    Paired because we use the same persona/seed for both baseline and candidate.
    """
    baseline = np.array(baseline_scores)
    candidate = np.array(candidate_scores)
    diff = candidate - baseline

    baseline_mean = float(np.mean(baseline))
    candidate_mean = float(np.mean(candidate))
    effect = float(np.mean(diff))

    # Bootstrap 95% CI for effect size
    ci_lower, ci_upper = bootstrap_ci(diff)

    # Wilcoxon signed-rank test (non-parametric paired test)
    # Requires at least 6 non-zero differences
    non_zero_diffs = diff[diff != 0]
    if len(non_zero_diffs) < 6:
        return ComparisonResult(
            metric_name=metric_name,
            baseline_mean=baseline_mean,
            candidate_mean=candidate_mean,
            effect_size=effect,
            p_value=1.0,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            is_significant=False,
            recommendation="inconclusive",
        )

    try:
        stat, p_value = stats.wilcoxon(non_zero_diffs, alternative="greater")
    except ValueError:
        p_value = 1.0

    p_value = float(p_value)
    is_significant = p_value < alpha and effect >= min_effect

    if is_significant:
        recommendation = "adopt"
    elif effect < 0:
        recommendation = "reject"
    else:
        recommendation = "inconclusive"

    return ComparisonResult(
        metric_name=metric_name,
        baseline_mean=baseline_mean,
        candidate_mean=candidate_mean,
        effect_size=effect,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        is_significant=is_significant,
        recommendation=recommendation,
    )


def bootstrap_ci(
    diffs: np.ndarray,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for mean difference."""
    if len(diffs) == 0:
        return 0.0, 0.0

    rng = np.random.default_rng(42)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choice(diffs, size=len(diffs), replace=True)
        means.append(float(np.mean(sample)))

    alpha = (1 - confidence) / 2
    lower = float(np.percentile(means, alpha * 100))
    upper = float(np.percentile(means, (1 - alpha) * 100))
    return lower, upper


def should_adopt(
    comparisons: list[ComparisonResult],
    compliance_baseline: float,
    compliance_candidate: float,
) -> tuple[bool, str]:
    """Determine if a prompt change should be adopted.

    Requirements:
    1. At least one metric shows significant improvement
    2. No metric shows significant regression
    3. Compliance rate does not decrease
    """
    if compliance_candidate < compliance_baseline:
        return False, f"Compliance regression: {compliance_baseline:.2f} → {compliance_candidate:.2f}"

    has_improvement = False
    has_regression = False
    reasons = []

    for comp in comparisons:
        if comp.is_significant and comp.effect_size > 0:
            has_improvement = True
            reasons.append(f"{comp.metric_name}: +{comp.effect_size:.2f} (p={comp.p_value:.4f})")
        elif comp.effect_size < -0.2 and comp.p_value < 0.1:
            has_regression = True
            reasons.append(f"{comp.metric_name}: {comp.effect_size:.2f} REGRESSION")

    if has_regression:
        return False, f"Regression detected: {'; '.join(reasons)}"

    if has_improvement:
        return True, f"Significant improvement: {'; '.join(reasons)}"

    return False, "No statistically significant improvement"
