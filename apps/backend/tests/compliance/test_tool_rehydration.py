"""Unit tests for ADK before_tool Argument Rehydration (VAL-03.3)."""
import pytest
from unittest.mock import MagicMock
from src.compliance.session_pii_vault import session_pii_vault
from src.compliance.callbacks.tool_rehydration_callback import (
    tool_rehydration_callback,
    rehydrate_arguments,
)


def test_tool_rehydration_direct():
    """Tests argument rehydration replacing tokens with real PII."""
    session_id = "test_rehydration_sess"
    session_pii_vault.purge_session(session_id)

    # Setup vault with known sensitive mappings
    session_pii_vault.get_or_create_token(session_id, "finance@startup.in", "EMAIL_ADDRESS")
    session_pii_vault.get_or_create_token(session_id, "ABCDE1234F", "INDIA_PAN")

    # LLM emitted tool call arguments with tokens
    raw_tool_args = {
        "vendor_email": "<EMAIL_1>",
        "pan_number": "<IN_PAN_1>",
        "amount": 25000,
        "metadata": {
            "notification_email": "<EMAIL_1>",
            "invoice_id": "INV-2026-99",
        },
    }

    rehydrated = rehydrate_arguments(session_id, raw_tool_args)

    assert rehydrated["vendor_email"] == "finance@startup.in"
    assert rehydrated["pan_number"] == "ABCDE1234F"
    assert rehydrated["amount"] == 25000
    assert rehydrated["metadata"]["notification_email"] == "finance@startup.in"
    assert rehydrated["metadata"]["invoice_id"] == "INV-2026-99"


def test_tool_rehydration_adk_callback_signature():
    """Tests the canonical ADK before_tool_callback(tool, args, tool_context) hook."""
    session_id = "adk_hook_sess"
    session_pii_vault.purge_session(session_id)

    session_pii_vault.get_or_create_token(session_id, "ceo@acme.in", "EMAIL_ADDRESS")

    mock_tool = MagicMock()
    mock_tool.name = "zoho_send_invoice"

    mock_context = MagicMock()
    mock_context.session.id = session_id
    mock_context.session_id = session_id

    args = {"to": "<EMAIL_1>", "subject": "Quarterly P&L"}

    result = tool_rehydration_callback(mock_tool, args, mock_context)

    # Canonical ADK 2.0 contract: args dict is mutated in-place and None is returned
    # so that ADK executes the underlying tool runner.
    assert args["to"] == "ceo@acme.in"
    assert result is None


def test_tool_call_limit_max_3():
    """Tests that exceeding 3 tool calls in a turn returns an interception error."""
    from src.compliance.callbacks.tool_rehydration_callback import reset_turn_tool_call_count

    session_id = "limit_test_sess"
    reset_turn_tool_call_count(session_id)

    mock_tool = MagicMock()
    mock_tool.name = "GMAIL_FETCH_EMAILS"
    mock_context = MagicMock()
    mock_context.session.id = session_id
    mock_context.session_id = session_id

    # 1st call
    res1 = tool_rehydration_callback(mock_tool, {"max_results": 5}, mock_context)
    assert res1 is None

    # 2nd call
    res2 = tool_rehydration_callback(mock_tool, {"ids_only": True}, mock_context)
    assert res2 is None

    # 3rd call
    res3 = tool_rehydration_callback(mock_tool, {"include_spam_trash": True}, mock_context)
    assert res3 is None

    # 4th call - exceeds limit of 3! Must return error dictionary instructing agent to summarize
    res4 = tool_rehydration_callback(mock_tool, {"max_results": 10}, mock_context)
    assert res4 is not None
    assert res4.get("status") == "limit_reached"
    assert res4.get("tool_calls_executed") == 3
    assert "Per-turn tool call limit reached" in res4.get("error", "")

    # Resetting count for new turn allows 3 more calls
    reset_turn_tool_call_count(session_id)
    res_fresh = tool_rehydration_callback(mock_tool, {"max_results": 5}, mock_context)
    assert res_fresh is None

