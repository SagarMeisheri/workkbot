"""In-Chat Human-In-The-Loop Approval & Commit Tests (Spec 04, VAL-04.6).

Verifies that mutating actions trigger in-chat pauses via ToolContext.request_confirmation(),
and that receiving approval executes the tool while declining safely aborts execution.
Read-only tools execute immediately without pause.
"""
import pytest
import uuid
from typing import Any, Dict
from src.mcp.hitl.user_confirmation import hitl_handler
from src.mcp.tools import DynamicMcpTool
from src.mcp.client import AgentgatewayMcpClient


class MockToolContext:
    """Simulates Google ADK ToolContext for HITL confirmation testing."""
    def __init__(self, user_id: str, org_id: str, confirmation: Any = None):
        self.user_id = user_id
        self.org_id = org_id
        self.tool_confirmation = confirmation
        self.requested_confirmations: list = []

    def request_confirmation(self, hint: str, payload: Dict[str, Any]):
        self.requested_confirmations.append({"hint": hint, "payload": payload})


@pytest.mark.asyncio
async def test_mutating_tool_pauses_for_confirmation():
    """Mutating action pauses and requests confirmation (VAL-04.6)."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    client = AgentgatewayMcpClient()
    client.register_mock_server("google_workspace", [
        {
            "name": "google_calendar_create_event",
            "description": "Create calendar event",
            "inputSchema": {"properties": {"summary": {"type": "string"}}},
        }
    ])

    tool = DynamicMcpTool(
        name="google_calendar_create_event",
        description="Create calendar event",
        parameters_schema={"properties": {"summary": {"type": "string"}}},
        provider="google_workspace",
        is_critical=True,
        client=client,
    )

    ctx = MockToolContext(user_id=user_id, org_id=org_id, confirmation=None)

    result = await tool.run_async(args={"summary": "Q3 Planning Meeting"}, tool_context=ctx)

    # Must be pending approval
    assert result.get("status") == "pending_approval"
    assert len(ctx.requested_confirmations) == 1
    assert "Authorization required" in ctx.requested_confirmations[0]["hint"]
    assert ctx.requested_confirmations[0]["payload"]["tool_name"] == "google_calendar_create_event"


@pytest.mark.asyncio
async def test_mutating_tool_executes_on_approval():
    """Mutating action completes execution when user approves via ApprovalCard."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    client = AgentgatewayMcpClient()
    executed_calls = []

    async def _mock_handler(params):
        executed_calls.append(params)
        return {"status": "success", "event_id": "gcal_12345"}

    client.register_mock_server("google_workspace", [
        {
            "name": "google_calendar_create_event",
            "description": "Create calendar event",
            "handler": _mock_handler,
        }
    ])

    tool = DynamicMcpTool(
        name="google_calendar_create_event",
        description="Create calendar event",
        parameters_schema={},
        provider="google_workspace",
        is_critical=True,
        client=client,
    )

    # ToolContext with user approval
    ctx = MockToolContext(
        user_id=user_id,
        org_id=org_id,
        confirmation={"confirmed": True, "approved": True},
    )

    result = await tool.run_async(args={"summary": "Approved Standup"}, tool_context=ctx)

    assert result.get("status") == "success"
    assert len(executed_calls) == 1
    assert executed_calls[0]["summary"] == "Approved Standup"


@pytest.mark.asyncio
async def test_mutating_tool_declined_by_user():
    """Mutating action safely halts when user declines via ApprovalCard."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    client = AgentgatewayMcpClient()
    tool = DynamicMcpTool(
        name="zoho_books_create_invoice",
        description="Create invoice",
        parameters_schema={},
        provider="zoho_workplace",
        is_critical=True,
        client=client,
    )

    # ToolContext with user decline
    ctx = MockToolContext(
        user_id=user_id,
        org_id=org_id,
        confirmation={"confirmed": False, "approved": False},
    )

    result = await tool.run_async(args={"amount": 50000}, tool_context=ctx)

    assert result.get("status") == "declined"
    assert "Action cancelled by user" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_read_action_executes_immediately_without_pause():
    """Read-only tools execute without requiring confirmation."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    client = AgentgatewayMcpClient()
    tool = DynamicMcpTool(
        name="google_drive_search",
        description="Search Google Drive",
        parameters_schema={},
        provider="google_workspace",
        is_critical=False,
        client=client,
    )

    ctx = MockToolContext(user_id=user_id, org_id=org_id, confirmation=None)

    result = await tool.run_async(args={"query": "financials"}, tool_context=ctx)

    assert result.get("status") in ("executed", "success")
    assert len(ctx.requested_confirmations) == 0
