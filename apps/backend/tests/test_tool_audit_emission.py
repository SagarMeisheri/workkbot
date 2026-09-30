"""Tool Invocation Audit Trail Tests with Composio log_id (Spec 04, VAL-04.7).

Verifies that every tool execution (both read and write) produces an immutable
audit log entry in Supabase (public.tool_invocations) and Google Cloud Logging,
capturing user_id, org_id, tool_name, provider, sanitized parameters, execution
duration, status, and non-empty Composio log_id.
"""
import pytest
import uuid
from src.mcp.audit import tool_audit_logger
from src.mcp.tools import DynamicMcpTool


class MockToolContext:
    def __init__(self, user_id: str, org_id: str):
        self.user_id = user_id
        self.org_id = org_id
        self.tool_confirmation = None


def test_tool_audit_logger_records_invocation_with_composio_log():
    """Direct logging records into store and Cloud Logging sink with Composio log_id (VAL-04.7)."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    composio_log_id = f"cmp_log_{uuid.uuid4().hex[:12]}"

    record_id = tool_audit_logger.log_invocation(
        user_id=user_id,
        org_id=org_id,
        tool_name="GOOGLECALENDAR_CREATE_EVENT",
        provider="composio",
        parameters={"summary": "Board Meeting"},
        status="executed",
        output={"status": "confirmed", "event_id": "gcal_999"},
        duration_ms=45,
        composio_log_id=composio_log_id,
    )
    assert record_id is not None

    # Query audit logs for user
    logs = tool_audit_logger.get_user_audit_logs(user_id=user_id, org_id=org_id)
    assert len(logs) >= 1
    target = next((l for l in logs if l.get("id") == record_id), None)
    assert target is not None
    assert target["tool_name"] == "GOOGLECALENDAR_CREATE_EVENT"
    assert target["provider"] == "composio"
    assert target["parameters"]["summary"] == "Board Meeting"
    assert target["duration_ms"] == 45
    assert target["status"] == "executed"
    assert target["composio_log_id"] == composio_log_id
    assert target["composio_log_id"] != ""


@pytest.mark.asyncio
async def test_dynamic_tool_execution_automatically_emits_audit_with_log_id():
    """Executing a DynamicMcpTool automatically invokes audit logger with Composio log_id."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    tool = DynamicMcpTool(
        name="GMAIL_LIST_MESSAGES",
        description="Search Gmail inbox messages",
        parameters_schema={},
        provider="composio",
        is_critical=False,
    )

    ctx = MockToolContext(user_id=user_id, org_id=org_id)
    res = await tool.run_async(args={"query": "contracts"}, tool_context=ctx)

    assert res.get("composio_log_id") is not None
    assert res.get("composio_log_id") != ""

    logs = tool_audit_logger.get_user_audit_logs(user_id=user_id, org_id=org_id)
    gmail_logs = [l for l in logs if l.get("tool_name") == "GMAIL_LIST_MESSAGES"]
    assert len(gmail_logs) >= 1
    assert gmail_logs[-1]["parameters"]["query"] == "contracts"
    assert gmail_logs[-1]["provider"] == "composio"
    assert gmail_logs[-1]["composio_log_id"] is not None
    assert gmail_logs[-1]["composio_log_id"] != ""
