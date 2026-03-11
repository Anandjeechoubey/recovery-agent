"""Tests for compliance checker (rule-based checks only)."""

import pytest

from src.agents.compliance import check_compliance_quick
from src.models.conversation import Conversation


def _make_conv(messages: list[tuple[str, str]]) -> Conversation:
    conv = Conversation(borrower_id="test", agent_type="assessment")
    for role, content in messages:
        conv.add_message(role, content)
    return conv


@pytest.mark.asyncio
async def test_ai_disclosure_pass():
    conv = _make_conv([
        ("agent", "Hello, I'm an AI agent acting on behalf of Apex Recovery. This conversation is being recorded."),
        ("borrower", "Ok"),
    ])
    violations = await check_compliance_quick(conv)
    rule_names = [v.rule for v in violations]
    assert "identity_disclosure" not in rule_names
    assert "recording_disclosure" not in rule_names


@pytest.mark.asyncio
async def test_ai_disclosure_fail():
    conv = _make_conv([
        ("agent", "Hello, I'm calling about your account."),
        ("borrower", "Ok"),
    ])
    violations = await check_compliance_quick(conv)
    rule_names = [v.rule for v in violations]
    assert "identity_disclosure" in rule_names
    assert "recording_disclosure" in rule_names


@pytest.mark.asyncio
async def test_stop_contact_respected():
    conv = _make_conv([
        ("agent", "I'm an AI agent. This is recorded."),
        ("borrower", "Stop contacting me!"),
        ("agent", "I understand and respect your request. I'll flag your account."),
    ])
    violations = await check_compliance_quick(conv)
    rule_names = [v.rule for v in violations]
    assert "no_harassment" not in rule_names


@pytest.mark.asyncio
async def test_stop_contact_violated():
    conv = _make_conv([
        ("agent", "I'm an AI agent. This is recorded."),
        ("borrower", "Stop contacting me!"),
        ("agent", "Let me tell you about your payment options anyway."),
    ])
    violations = await check_compliance_quick(conv)
    rule_names = [v.rule for v in violations]
    assert "no_harassment" in rule_names


@pytest.mark.asyncio
async def test_data_privacy_full_card():
    conv = _make_conv([
        ("agent", "I'm an AI agent. This is recorded. Your card number is 4532-1234-5678-9012."),
    ])
    violations = await check_compliance_quick(conv)
    rule_names = [v.rule for v in violations]
    assert "data_privacy" in rule_names


@pytest.mark.asyncio
async def test_data_privacy_partial_ok():
    conv = _make_conv([
        ("agent", "I'm an AI agent. This is recorded. Your account ending in 1234."),
    ])
    violations = await check_compliance_quick(conv)
    rule_names = [v.rule for v in violations]
    assert "data_privacy" not in rule_names
