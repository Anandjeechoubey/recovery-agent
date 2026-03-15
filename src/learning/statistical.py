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

    # Statistical test selection based on available non-zero differences
    non_zero_diffs = diff[diff != 0]
    n_non_zero = len(non_zero_diffs)

    if n_non_zero < 3:
        # Too few observations for any valid test
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

    if n_non_zero >= 6:
        # Wilcoxon signed-rank test (preferred for larger samples)
        try:
            stat, p_value = stats.wilcoxon(non_zero_diffs, alternative="greater")
        except ValueError:
            p_value = 1.0
    else:
        # Sign test fallback for small samples (3-5 non-zero diffs)
        n_positive = int(np.sum(non_zero_diffs > 0))
        result = stats.binomtest(n_positive, n_non_zero, 0.5, alternative="greater")
        p_value = result.pvalue

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


def compare_composite(
    baseline_composite: list[float],
    candidate_composite: list[float],
    alpha: float = 0.15,
    min_effect: float = 0.05,
) -> ComparisonResult:
    """Compare weighted composite scores using a single paired test.

    More powerful than per-metric testing because it aggregates signal.
    """
    return wilcoxon_compare(
        baseline_composite, candidate_composite,
        alpha=alpha, min_effect=min_effect, metric_name="composite",
    )


def should_adopt(
    comparisons: list[ComparisonResult],
    compliance_baseline: float,
    compliance_candidate: float,
    composite_result: ComparisonResult | None = None,
) -> tuple[bool, str]:
    """Determine if a prompt change should be adopted.

    Uses a two-path adoption strategy:
    1. **Composite path**: If a composite score comparison is provided, adopt if the
       composite shows significant improvement (single test = more statistical power).
    2. **Per-metric path**: Otherwise, adopt if at least one metric improves significantly.

    Always blocks on:
    - Compliance regression (>5% drop)
    - Severe per-metric regression (>0.3 drop with p<0.1)
    """
    # Allow up to 5% compliance drop (1 conversation difference in small samples)
    compliance_tolerance = 0.05
    if compliance_candidate < compliance_baseline - compliance_tolerance:
        return False, f"Compliance regression: {compliance_baseline:.2f} → {compliance_candidate:.2f}"

    # Check for severe regression on any individual metric
    has_regression = False
    regression_reasons = []
    for comp in comparisons:
        if comp.effect_size < -0.3 and comp.p_value < 0.1:
            has_regression = True
            regression_reasons.append(f"{comp.metric_name}: {comp.effect_size:.2f} REGRESSION")

    if has_regression:
        return False, f"Regression detected: {'; '.join(regression_reasons)}"

    # Path 1: Composite score test (preferred — higher statistical power)
    if composite_result and composite_result.is_significant and composite_result.effect_size > 0:
        reasons = [f"composite: +{composite_result.effect_size:.3f} (p={composite_result.p_value:.4f})"]
        # Also note per-metric improvements
        for comp in comparisons:
            if comp.effect_size > 0.05:
                reasons.append(f"{comp.metric_name}: +{comp.effect_size:.2f}")
        return True, f"Composite improvement: {'; '.join(reasons)}"

    # Path 2: Per-metric significance (fallback)
    improvement_reasons = []
    for comp in comparisons:
        if comp.is_significant and comp.effect_size > 0:
            improvement_reasons.append(f"{comp.metric_name}: +{comp.effect_size:.2f} (p={comp.p_value:.4f})")

    if improvement_reasons:
        return True, f"Per-metric improvement: {'; '.join(improvement_reasons)}"

    # Path 3: Net positive trend — adopt if mean effect across all metrics is positive
    # even if no single metric reaches significance (reduces false negatives)
    if comparisons:
        mean_effect = float(np.mean([c.effect_size for c in comparisons]))
        positive_count = sum(1 for c in comparisons if c.effect_size > 0)
        if mean_effect > 0.03 and positive_count >= len(comparisons) * 0.6:
            reasons = [f"net_trend: +{mean_effect:.3f} ({positive_count}/{len(comparisons)} metrics positive)"]
            return True, f"Net positive trend: {'; '.join(reasons)}"

    return False, "No statistically significant improvement"
