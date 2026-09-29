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

    # Args dict should be mutated in-place and returned
    assert args["to"] == "ceo@acme.in"
    assert result["to"] == "ceo@acme.in"
