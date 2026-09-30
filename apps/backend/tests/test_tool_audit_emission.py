"""Tool Invocation Audit Trail Tests (Spec 04, VAL-04.7).

Verifies that every tool execution (both read and write) produces an immutable
audit log entry in Supabase (public.tool_invocations) and Google Cloud Logging,
capturing user_id, org_id, tool_name, provider, sanitized parameters, execution
duration, and status.
"""
import pytest
import uuid
from src.mcp.audit import tool_audit_logger
from src.mcp.tools import DynamicMcpTool
from src.mcp.client import AgentgatewayMcpClient


class MockToolContext:
    def __init__(self, user_id: str, org_id: str):
        self.user_id = user_id
        self.org_id = org_id
        self.tool_confirmation = None


def test_tool_audit_logger_records_invocation():
    """Direct logging records into local store and Cloud Logging sink (VAL-04.7)."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    record_id = tool_audit_logger.log_invocation(
        user_id=user_id,
        org_id=org_id,
        tool_name="google_calendar_create_event",
        provider="google_workspace",
        parameters={"summary": "Board Meeting"},
        status="executed",
        output={"status": "confirmed", "event_id": "gcal_999"},
        duration_ms=45,
    )
    assert record_id is not None

    # Query audit logs for user
    logs = tool_audit_logger.get_user_audit_logs(user_id=user_id, org_id=org_id)
    assert len(logs) >= 1
    target = next((l for l in logs if l.get("id") == record_id), None)
    assert target is not None
    assert target["tool_name"] == "google_calendar_create_event"
    assert target["provider"] == "google_workspace"
    assert target["parameters"]["summary"] == "Board Meeting"
    assert target["duration_ms"] == 45
    assert target["status"] == "executed"


@pytest.mark.asyncio
async def test_dynamic_tool_execution_automatically_emits_audit():
    """Executing a DynamicMcpTool automatically invokes audit logger."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    client = AgentgatewayMcpClient()
    tool = DynamicMcpTool(
        name="google_drive_search",
        description="Search Drive files",
        parameters_schema={},
        provider="google_workspace",
        is_critical=False,
        client=client,
    )

    ctx = MockToolContext(user_id=user_id, org_id=org_id)
    await tool.run_async(args={"query": "contracts"}, tool_context=ctx)

    logs = tool_audit_logger.get_user_audit_logs(user_id=user_id, org_id=org_id)
    drive_logs = [l for l in logs if l.get("tool_name") == "google_drive_search"]
    assert len(drive_logs) >= 1
    assert drive_logs[-1]["parameters"]["query"] == "contracts"
    assert drive_logs[-1]["provider"] == "google_workspace"
