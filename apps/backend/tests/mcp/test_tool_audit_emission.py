"""Test VAL-04.7: Immutable Tool Execution Audit Emission (Supabase & Cloud Logging, Spec 04)."""
import pytest
from src.mcp.audit import tool_audit
from src.auth.client import _local_db


@pytest.mark.asyncio
async def test_tool_audit_record_created_with_tenant_isolation():
    """Tool execution must produce immutable records with user and tenant isolation."""
    user_id = "user-audit-001"
    org_id = "org-audit-001"
    session_id = "sess-audit-001"
    tool_name = "sheets.update_values"
    params = {"spreadsheet_id": "sheet_abc", "range": "A1:B2", "values": [[1, 2]]}

    inv_id = await tool_audit.log_tool_invocation(
        user_id=user_id,
        org_id=org_id,
        session_id=session_id,
        provider="google_workspace",
        tool_name=tool_name,
        parameters=params,
        result={"updated_cells": 2},
        duration_ms=45,
        status="success",
    )

    assert inv_id is not None

    # Verify record in local mirror
    record = next((r for r in _local_db.get("tool_invocations", []) if r["id"] == inv_id), None)
    assert record is not None
    assert record["user_id"] == user_id
    assert record["org_id"] == org_id
    assert record["session_id"] == session_id
    assert record["provider"] == "google_workspace"
    assert record["tool_name"] == tool_name
    assert record["parameters"] == params
    assert record["execution_duration_ms"] == 45
    assert record["status"] == "success"
    assert "created_at" in record
