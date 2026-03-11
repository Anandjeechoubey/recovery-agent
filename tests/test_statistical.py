"""Tests for statistical testing module."""

from src.learning.statistical import bootstrap_ci, should_adopt, wilcoxon_compare


def test_wilcoxon_significant_improvement():
    baseline = [2.0, 2.5, 2.0, 2.5, 3.0, 2.0, 2.5, 2.0, 2.5, 3.0]
    candidate = [3.5, 4.0, 3.5, 4.0, 4.5, 3.5, 4.0, 3.5, 4.0, 4.5]
    result = wilcoxon_compare(baseline, candidate, metric_name="test")
    assert result.effect_size > 0
    assert result.recommendation == "adopt"


def test_wilcoxon_no_improvement():
    baseline = [3.0, 3.5, 3.0, 3.5, 3.0, 3.5, 3.0, 3.5, 3.0, 3.5]
    candidate = [3.0, 3.5, 3.0, 3.5, 3.0, 3.5, 3.0, 3.5, 3.0, 3.5]
    result = wilcoxon_compare(baseline, candidate, metric_name="test")
    assert result.recommendation != "adopt"


def test_wilcoxon_regression():
    baseline = [4.0, 4.5, 4.0, 4.5, 4.0, 4.5, 4.0, 4.5, 4.0, 4.5]
    candidate = [2.0, 2.5, 2.0, 2.5, 2.0, 2.5, 2.0, 2.5, 2.0, 2.5]
    result = wilcoxon_compare(baseline, candidate, metric_name="test")
    assert result.effect_size < 0
    assert result.recommendation == "reject"


def test_bootstrap_ci():
    import numpy as np
    diffs = np.array([0.5, 0.3, 0.7, 0.4, 0.6, 0.5, 0.3, 0.8])
    lower, upper = bootstrap_ci(diffs)
    assert lower > 0  # All positive diffs, CI should be positive
    assert upper > lower


def test_should_adopt_compliance_regression():
    from src.learning.statistical import ComparisonResult
    comp = ComparisonResult(
        metric_name="test", baseline_mean=3.0, candidate_mean=4.0,
        effect_size=1.0, p_value=0.01, ci_lower=0.5, ci_upper=1.5,
        is_significant=True, recommendation="adopt",
    )
    adopt, reason = should_adopt([comp], compliance_baseline=0.9, compliance_candidate=0.8)
    assert not adopt
    assert "Compliance regression" in reason


def test_should_adopt_success():
    from src.learning.statistical import ComparisonResult
    comp = ComparisonResult(
        metric_name="test", baseline_mean=3.0, candidate_mean=4.0,
        effect_size=1.0, p_value=0.01, ci_lower=0.5, ci_upper=1.5,
        is_significant=True, recommendation="adopt",
    )
    adopt, reason = should_adopt([comp], compliance_baseline=0.9, compliance_candidate=0.9)
    assert adopt
    assert "improvement" in reason.lower()
