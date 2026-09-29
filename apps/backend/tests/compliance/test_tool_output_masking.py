"""Unit tests for ADK after_tool Tool Output Masking (VAL-03.4)."""
import pytest
from unittest.mock import MagicMock
from src.compliance.session_pii_vault import session_pii_vault
from src.compliance.callbacks.tool_output_mask_callback import (
    tool_output_mask_callback,
    mask_tool_output,
)


def test_tool_output_masking_known_pii():
    """Tests that previously known PII in tool response is masked back to tokens."""
    session_id = "mask_sess_01"
    session_pii_vault.purge_session(session_id)

    # Register known email in vault
    token = session_pii_vault.get_or_create_token(session_id, "vendor@corp.in", "EMAIL_ADDRESS")

    # Upstream ERP returned response with raw email
    erp_response = {
        "status": "delivered",
        "invoice_id": "INV-500",
        "recipient": "vendor@corp.in",
        "details": {"contact": "vendor@corp.in", "charges": 1200},
    }

    masked = mask_tool_output(session_id, erp_response)

    # Raw email must be replaced with token
    assert masked["recipient"] == token
    assert masked["details"]["contact"] == token
    assert masked["invoice_id"] == "INV-500"
    assert masked["details"]["charges"] == 1200


def test_tool_output_masking_newly_discovered_pii():
    """Tests that newly returned PII from ERP databases (like PAN) is detected and tokenized."""
    session_id = "mask_sess_02"
    session_pii_vault.purge_session(session_id)

    # ERP response returns an Indian PAN that wasn't in the user prompt
    erp_response = {
        "status": "vendor_retrieved",
        "tax_record": "Vendor PAN is ABCDE1234F verified by Income Tax Dept",
    }

    masked = mask_tool_output(session_id, erp_response)

    assert "ABCDE1234F" not in masked["tax_record"]
    assert "<IN_PAN_1>" in masked["tax_record"]


def test_tool_output_masking_adk_callback_signature():
    """Tests the canonical ADK after_tool_callback(tool, args, tool_context, tool_response) hook."""
    session_id = "adk_after_tool_sess"
    session_pii_vault.purge_session(session_id)

    session_pii_vault.get_or_create_token(session_id, "hr@enterprise.in", "EMAIL_ADDRESS")

    mock_tool = MagicMock()
    mock_context = MagicMock()
    mock_context.session.id = session_id

    tool_response = {"success": True, "created_by": "hr@enterprise.in"}
    result = tool_output_mask_callback(mock_tool, {}, mock_context, tool_response)

    assert result["created_by"] == "<EMAIL_1>"
    assert result["success"] is True
