"""Test VAL-04.6: In-Chat Human-in-the-Loop (HITL) Confirmation Flow (Spec 04)."""
import pytest
from unittest.mock import AsyncMock, patch
from src.mcp.client import google_mcp_client
from src.auth.client import _local_db


@pytest.mark.asyncio
async def test_mutating_tool_blocked_without_confirmation():
    """Mutating tools must pause and return confirmation request payload when unconfirmed."""
    headers = {"Authorization": "Bearer jwt", "X-Upstream-Authorization": "Bearer ya29"}
    args = {
        "summary": "Q4 Strategy Meeting",
        "start_time": "2026-10-05T10:00:00Z",
        "end_time": "2026-10-05T11:00:00Z",
    }

    res = await google_mcp_client.execute_tool(
        service="calendar",
        tool_name="calendar.create_event",
        arguments=args,
        delegated_headers=headers,
        user_id="user-hitl-001",
        org_id="org-hitl-001",
        session_id="session-hitl-001",
        confirmation_granted=False,
    )

    assert res.get("requires_confirmation") is True
    challenge = res.get("confirmation_request")
    assert challenge is not None
    assert challenge["tool_name"] == "calendar.create_event"
    assert challenge["service_name"] == "Google Calendar"
    assert challenge["parameters"]["summary"] == "Q4 Strategy Meeting"

    # Confirm audit log captured the blocked action
    invocations = [
        inv for inv in _local_db.get("tool_invocations", [])
        if inv["session_id"] == "session-hitl-001"
    ]
    assert len(invocations) > 0
    assert invocations[-1]["status"] == "blocked_hitl"


@pytest.mark.asyncio
async def test_mutating_tool_executes_when_confirmed():
    """Mutating tools must execute through gateway once user confirmation is granted."""
    headers = {"Authorization": "Bearer jwt", "X-Upstream-Authorization": "Bearer ya29"}
    args = {"summary": "Approved Meeting"}

    # Mock gateway HTTP response
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "event_123", "status": "confirmed"}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await google_mcp_client.execute_tool(
            service="calendar",
            tool_name="calendar.create_event",
            arguments=args,
            delegated_headers=headers,
            user_id="user-hitl-002",
            org_id="org-hitl-002",
            session_id="session-hitl-002",
            confirmation_granted=True,  # User clicked [Confirm & Execute]
        )

    assert res.get("requires_confirmation") is None
    assert res.get("id") == "event_123"

    # Audit log should show success
    invocations = [
        inv for inv in _local_db.get("tool_invocations", [])
        if inv["session_id"] == "session-hitl-002"
    ]
    assert len(invocations) > 0
    assert invocations[-1]["status"] == "success"


@pytest.mark.asyncio
async def test_read_tool_executes_without_confirmation():
    """Retrieval tools must never pause for HITL approval."""
    headers = {"Authorization": "Bearer jwt", "X-Upstream-Authorization": "Bearer ya29"}
    args = {"query": "marketing"}

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"files": [{"id": "f1", "name": "marketing.pdf"}]}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await google_mcp_client.execute_tool(
            service="drive",
            tool_name="drive.search_files",
            arguments=args,
            delegated_headers=headers,
            user_id="user-hitl-003",
            org_id="org-hitl-003",
            session_id="session-hitl-003",
            confirmation_granted=False,  # Unconfirmed, but read-only
        )

    assert res.get("requires_confirmation") is None
    assert "files" in res
