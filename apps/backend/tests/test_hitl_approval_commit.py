"""In-Chat Human-In-The-Loop Approval & Commit Tests (Spec 04, VAL-04.6).

Verifies that mutating Composio actions trigger in-chat pauses via ToolContext.request_confirmation(),
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
async def test_mutating_composio_tool_pauses_for_confirmation():
    """Mutating Composio action pauses and requests confirmation (VAL-04.6)."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    tool = DynamicMcpTool(
        name="GOOGLECALENDAR_CREATE_EVENT",
        description="Creates a calendar event in user Google Calendar",
        parameters_schema={"properties": {"summary": {"type": "string"}}},
        provider="composio",
        is_critical=True,
    )

    ctx = MockToolContext(user_id=user_id, org_id=org_id, confirmation=None)

    result = await tool.run_async(args={"summary": "Team Standup tomorrow 10 AM"}, tool_context=ctx)

    # Must be pending approval
    assert result.get("status") == "pending_approval"
    assert result.get("requires_confirmation") is True
    assert len(ctx.requested_confirmations) == 1
    assert "Authorization required" in ctx.requested_confirmations[0]["hint"]
    assert ctx.requested_confirmations[0]["payload"]["tool_name"] == "GOOGLECALENDAR_CREATE_EVENT"


@pytest.mark.asyncio
async def test_mutating_composio_tool_executes_on_approval():
    """Mutating Composio action completes execution when user approves via ApprovalCard."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    tool = DynamicMcpTool(
        name="GOOGLECALENDAR_CREATE_EVENT",
        description="Creates calendar event",
        parameters_schema={},
        provider="composio",
        is_critical=True,
    )

    # ToolContext with user approval
    ctx = MockToolContext(
        user_id=user_id,
        org_id=org_id,
        confirmation={"confirmed": True, "approved": True},
    )

    result = await tool.run_async(args={"summary": "Approved Standup"}, tool_context=ctx)

    assert result.get("status") == "success"
    assert result.get("data") is not None
    assert result.get("composio_log_id") is not None


@pytest.mark.asyncio
async def test_mutating_composio_tool_declined_by_user():
    """Mutating Composio action safely halts when user declines via ApprovalCard."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    tool = DynamicMcpTool(
        name="GMAIL_SEND_MESSAGE",
        description="Sends email message",
        parameters_schema={},
        provider="composio",
        is_critical=True,
    )

    # ToolContext with user decline
    ctx = MockToolContext(
        user_id=user_id,
        org_id=org_id,
        confirmation={"confirmed": False, "approved": False},
    )

    result = await tool.run_async(args={"recipient": "client@example.com"}, tool_context=ctx)

    assert result.get("status") == "declined"
    assert "Action cancelled by user" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_read_action_executes_immediately_without_pause():
    """Read-only tools execute without requiring confirmation."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    tool = DynamicMcpTool(
        name="GMAIL_LIST_MESSAGES",
        description="Lists inbox messages",
        parameters_schema={},
        provider="composio",
        is_critical=False,
    )

    ctx = MockToolContext(user_id=user_id, org_id=org_id, confirmation=None)

    result = await tool.run_async(args={"query": "invoices"}, tool_context=ctx)

    assert result.get("status") == "success"
    assert len(ctx.requested_confirmations) == 0
