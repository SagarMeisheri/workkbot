"""Security Hardening Verification Tests (VULN-01 through VULN-10)."""
import time
import pytest
from unittest.mock import AsyncMock, patch
from httpx import Response, Request

from src.mcp.client import google_mcp_client
from src.mcp.sanitizer import parameter_sanitizer
from src.mcp.audit import tool_audit, scrub_sensitive_audit_payload
from src.mcp.hitl.user_confirmation import format_confirmation_request
from src.routers.auth import _generate_oauth_state, _verify_oauth_state


def test_hmac_oauth_state_tamper_proofing():
    """VULN-03: OAuth state must be signed and reject tampering or expiry."""
    user_id = "user-sec-001"
    org_id = "org-sec-001"
    provider = "google_workspace"

    # 1. Valid state generates and verifies
    valid_state = _generate_oauth_state(user_id, org_id, provider)
    verified = _verify_oauth_state(valid_state, expected_provider=provider)
    assert verified == (user_id, org_id)

    # 2. Tampered user_id or org_id must fail signature check
    parts = valid_state.split(":")
    tampered_parts = ["attacker-user", parts[1], parts[2], parts[3], parts[4], parts[5]]
    tampered_state = ":".join(tampered_parts)
    assert _verify_oauth_state(tampered_state, expected_provider=provider) is None

    # 3. Provider confusion attack (state generated for zoho used for google)
    assert _verify_oauth_state(valid_state, expected_provider="zoho_workplace") is None

    # 4. Expired state (timestamp in the past > 15m)
    expired_parts = [parts[0], parts[1], parts[2], str(int(time.time()) - 1000), parts[4], parts[5]]
    expired_state = ":".join(expired_parts)
    assert _verify_oauth_state(expired_state, expected_provider=provider) is None


@pytest.mark.asyncio
async def test_agentgateway_fail_closed_on_rejection():
    """VULN-02: Client must fail-closed and NEVER bypass gateway on HTTP errors or CEL rejections."""
    headers = {"Authorization": "Bearer jwt", "X-Upstream-Authorization": "Bearer ya29"}
    args = {"query": "confidential documents"}

    # Mock gateway returning 403 Forbidden (e.g. cross-tenant CEL violation)
    req = Request("POST", "http://127.0.0.1:8080/mcp/google/drive")
    mock_resp = Response(403, text="CEL Policy Violation: tenant mismatch", request=req)

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await google_mcp_client.execute_tool(
            service="drive",
            tool_name="drive.search_files",
            arguments=args,
            delegated_headers=headers,
            user_id="user-sec-002",
            org_id="org-sec-002",
            session_id="session-sec-002",
            confirmation_granted=True,
        )

        # Call should have gone strictly to gateway and halted
        assert mock_post.call_count == 1
        assert res.get("status_code") == 403
        assert "CEL Policy Violation" in res.get("error", "")


def test_hitl_parameter_binding_hash():
    """VULN-04: Confirmation requests must include cryptographic parameter hash."""
    params = {"to": "ceo@workkbot.in", "subject": "Quarterly Report"}
    req = format_confirmation_request("gmail.create_draft", params)
    data = req.to_dict()
    assert "confirmation_hash" in data
    assert len(data["confirmation_hash"]) == 16


def test_multiline_sanitizer_preserves_content():
    """VULN-08: Multiline fields must preserve carriage returns and line feeds without corruption."""
    doc_args = {
        "document_body": "Title: Executive Summary\r\nLine 1: Revenue up.\r\nLine 2: Churn down.",
        "description": "Meeting Notes\nAttendees: Priya, Rahul",
        "single_line_field": "Heading\r\nInjectionAttempt",
    }
    sanitized = parameter_sanitizer.sanitize_arguments(doc_args)
    assert "\r\n" in sanitized["document_body"]
    assert "\n" in sanitized["description"]
    # Single-line field should have CRLF stripped into space
    assert "\r" not in sanitized["single_line_field"]
    assert "\n" not in sanitized["single_line_field"]


def test_audit_scrubbing_redacts_tokens_and_pii():
    """VULN-05: Sensitive tokens and Indian PII must be scrubbed before audit persistence."""
    raw_params = {
        "user_email": "employee@workkbot.in",
        "aadhaar": "1234 5678 9012",
        "pan": "ABCDE1234F",
        "auth_token": "ya29.live_secret_access_token_super_confidential",
    }
    scrubbed = scrub_sensitive_audit_payload(raw_params)
    assert scrubbed["auth_token"] == "[REDACTED_SECRET]"
    assert "[REDACTED_AADHAAR]" in scrubbed["aadhaar"]
    assert "[REDACTED_PAN]" in scrubbed["pan"]
    assert scrubbed["user_email"] == "employee@workkbot.in"
