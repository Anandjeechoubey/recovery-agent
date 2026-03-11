"""Tests for data models."""

from src.models.borrower import Borrower, PolicyRanges
from src.models.conversation import Conversation, HandoffSummary, Message
from src.models.evaluation import EvalResult, MetricScore, PromptVersion


def test_borrower_creation():
    b = Borrower(
        id="test-1", name="John", account_last4="1234",
        total_debt=5000, debt_type="credit_card",
        days_past_due=90, phone_number="+1234567890", email="j@test.com",
    )
    assert b.total_debt == 5000
    assert b.policy.min_settlement_pct == 0.40


def test_conversation_add_message():
    conv = Conversation(borrower_id="test", agent_type="assessment")
    msg = conv.add_message("agent", "Hello")
    assert len(conv.messages) == 1
    assert msg.role == "agent"


def test_conversation_to_transcript():
    conv = Conversation(borrower_id="test", agent_type="assessment")
    conv.add_message("agent", "Hello, I'm an AI agent.")
    conv.add_message("borrower", "Hi, what's this about?")
    transcript = conv.to_transcript()
    assert "Agent: Hello" in transcript
    assert "Borrower: Hi" in transcript


def test_eval_result_get_metric():
    result = EvalResult(
        prompt_version_id="test",
        agent_type="assessment",
        metrics=[MetricScore(name="tone", value=3.5)],
    )
    assert result.get_metric("tone").value == 3.5
    assert result.get_metric("missing") is None


def test_handoff_summary():
    hs = HandoffSummary(
        content="Summary text",
        token_count=10,
        source_agent="assessment",
    )
    assert hs.source_agent == "assessment"
