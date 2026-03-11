"""Tests for token budget enforcement."""

import pytest

from src.agents.assessment import ASSESSMENT_PROMPT, AssessmentAgent
from src.agents.final_notice import FINAL_NOTICE_PROMPT
from src.agents.resolution import RESOLUTION_PROMPT
from src.context.token_budget import count_tokens, enforce_budget, truncate_to_tokens


def test_count_tokens_basic():
    text = "Hello, world!"
    tokens = count_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_truncate_to_tokens():
    text = "word " * 1000  # ~1000 tokens
    truncated = truncate_to_tokens(text, 100)
    assert count_tokens(truncated) <= 100


def test_enforce_budget_no_handoff():
    prompt = "Short prompt"
    result_prompt, result_handoff = enforce_budget(prompt, None, max_total=2000)
    assert result_prompt == prompt
    assert result_handoff is None


def test_enforce_budget_with_handoff():
    prompt = "Short prompt"
    handoff = "Some context"
    result_prompt, result_handoff = enforce_budget(
        prompt, handoff, max_total=2000, max_handoff=500
    )
    assert result_prompt == prompt
    assert result_handoff == handoff
    assert count_tokens(result_handoff) <= 500


def test_enforce_budget_truncates_handoff():
    prompt = "Short prompt"
    handoff = "word " * 600  # More than 500 tokens
    result_prompt, result_handoff = enforce_budget(
        prompt, handoff, max_total=2000, max_handoff=500
    )
    assert count_tokens(result_handoff) <= 500


def test_enforce_budget_raises_on_overflow():
    prompt = "word " * 2500  # Way over 2000 tokens
    with pytest.raises(ValueError, match="exceeds budget"):
        enforce_budget(prompt, None, max_total=2000)


def test_assessment_prompt_fits_budget():
    """Assessment agent gets full 2000 token budget (no handoff)."""
    # Render with sample data
    rendered = ASSESSMENT_PROMPT.format(
        borrower_name="John Doe",
        account_last4="1234",
        total_debt="$5,000.00",
        debt_type="credit card",
        days_past_due=90,
        min_settlement_pct=40,
        max_settlement_pct=80,
        max_installments=12,
    )
    tokens = count_tokens(rendered)
    assert tokens <= 2000, f"Assessment prompt is {tokens} tokens, exceeds 2000"


def test_resolution_prompt_fits_budget():
    """Resolution agent gets 1500 tokens (2000 - 500 handoff)."""
    rendered = RESOLUTION_PROMPT.format(
        borrower_name="John Doe",
        account_last4="1234",
        total_debt="$5,000.00",
        debt_type="credit card",
        days_past_due=90,
        min_settlement_pct=40,
        max_settlement_pct=80,
        max_installments=12,
    )
    tokens = count_tokens(rendered)
    assert tokens <= 1500, f"Resolution prompt is {tokens} tokens, exceeds 1500"


def test_final_notice_prompt_fits_budget():
    """Final notice agent gets 1500 tokens (2000 - 500 handoff)."""
    rendered = FINAL_NOTICE_PROMPT.format(
        borrower_name="John Doe",
        account_last4="1234",
        total_debt="$5,000.00",
        debt_type="credit card",
        days_past_due=90,
        min_settlement_pct=40,
        max_settlement_pct=80,
        max_installments=12,
    )
    tokens = count_tokens(rendered)
    assert tokens <= 1500, f"Final notice prompt is {tokens} tokens, exceeds 1500"


def test_full_budget_enforcement_assessment():
    """Test that assessment agent can build messages within budget."""
    rendered = ASSESSMENT_PROMPT.format(
        borrower_name="John Doe",
        account_last4="1234",
        total_debt="$5,000.00",
        debt_type="credit card",
        days_past_due=90,
        min_settlement_pct=40,
        max_settlement_pct=80,
        max_installments=12,
    )
    prompt, handoff = enforce_budget(rendered, None, max_total=2000, max_handoff=500)
    assert count_tokens(prompt) <= 2000


def test_full_budget_enforcement_with_handoff():
    """Test that agents with handoff stay within 2000 total."""
    rendered = RESOLUTION_PROMPT.format(
        borrower_name="John Doe",
        account_last4="1234",
        total_debt="$5,000.00",
        debt_type="credit card",
        days_past_due=90,
        min_settlement_pct=40,
        max_settlement_pct=80,
        max_installments=12,
    )
    handoff = "word " * 400  # Some handoff context
    prompt, handoff = enforce_budget(rendered, handoff, max_total=2000, max_handoff=500)
    total = count_tokens(prompt) + count_tokens(handoff)
    assert total <= 2000, f"Total {total} tokens exceeds 2000"
