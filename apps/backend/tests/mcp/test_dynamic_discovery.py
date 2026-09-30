"""Tests for Dynamic MCP Tool Discovery & Dynamic ADK Toolset (Spec 04/05)."""
import pytest
from unittest.mock import AsyncMock, patch

from src.mcp.discovery import mcp_discovery_service, STANDARD_GOOGLE_WORKSPACE_TOOLS
from src.mcp.google_tools import DynamicMcpTool, DynamicMcpToolset, current_turn_context
from src.auth.client import _local_db


@pytest.mark.asyncio
async def test_mcp_discovery_service_fallback_catalog():
    """Verifies discovery yields standard Google Workspace MCP catalog when gateway is offline."""
    user_id = "test-discovery-user-1"
    org_id = "test-discovery-org-1"

    tools = await mcp_discovery_service.discover_and_cache_tools(
        user_id=user_id,
        org_id=org_id,
        provider="google_workspace",
        access_token="fake_token_123",
    )

    assert len(tools) > 0
    tool_names = [t["name"] for t in tools]
    assert "calendar_list_events" in tool_names
    assert "gmail_search_threads" in tool_names
    assert "drive_search_files" in tool_names

    # Test retrieval from cache
    cached = mcp_discovery_service.get_discovered_tools(user_id=user_id)
    assert len(cached) == len(tools)


@pytest.mark.asyncio
async def test_mcp_discovery_service_remote_tools_list():
    """Verifies discovery correctly parses tools from remote MCP server JSON-RPC tools/list."""
    user_id = "test-discovery-user-2"
    org_id = "test-discovery-org-2"

    mock_remote_tools = [
        {
            "name": "calendar.custom_action",
            "description": "Custom action on calendar",
            "inputSchema": {
                "type": "object",
                "properties": {"action_type": {"type": "string"}},
            },
        }
    ]

    with patch("src.mcp.client.google_mcp_client.list_tools", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_remote_tools

        tools = await mcp_discovery_service.discover_and_cache_tools(
            user_id=user_id,
            org_id=org_id,
            provider="google_workspace",
            access_token="real_or_mock_token",
        )

        assert any(t["name"] == "calendar_custom_action" for t in tools)
        custom_tool = next(t for t in tools if t["name"] == "calendar_custom_action")
        assert custom_tool["original_name"] == "calendar.custom_action"
        assert "action_type" in custom_tool["inputSchema"]["properties"]


@pytest.mark.asyncio
async def test_dynamic_mcp_toolset_yields_tools_for_connected_user():
    """Verifies DynamicMcpToolset returns BaseTool instances dynamically for connected users."""
    user_id = "test-toolset-user"
    org_id = "test-toolset-org"

    # Seed an active connection in _local_db
    _local_db["mcp_connections"] = [
        {
            "id": "conn-test-1",
            "user_id": user_id,
            "org_id": org_id,
            "provider": "google_workspace",
            "status": "active",
            "discovered_tools": STANDARD_GOOGLE_WORKSPACE_TOOLS,
        }
    ]

    toolset = DynamicMcpToolset()

    # When no turn context is set, toolset returns empty list
    tools_empty = await toolset.get_tools()
    assert len(tools_empty) == 0

    # When turn context is active for connected user
    token = current_turn_context.set({"user_id": user_id, "org_id": org_id})
    try:
        active_tools = await toolset.get_tools()
        assert len(active_tools) > 0
        names = [t.name for t in active_tools]
        assert "calendar_list_events" in names

        # Verify dynamic function declaration
        cal_tool = next(t for t in active_tools if t.name == "calendar_list_events")
        decl = cal_tool._get_declaration()
        assert decl.name == "calendar_list_events"
        assert decl.parameters_json_schema is not None
    finally:
        current_turn_context.reset(token)


@pytest.mark.asyncio
async def test_dynamic_tool_hitl_enforcement():
    """Verifies dynamic tools enforce HITL confirmation for mutating tools."""
    user_id = "test-hitl-user"
    token = current_turn_context.set({
        "user_id": user_id,
        "org_id": "test-org",
        "session_id": "sess-123",
        "state_delta": {},  # Not yet confirmed
    })

    try:
        tool = DynamicMcpTool(
            name="calendar_create_event",
            original_name="calendar.create_event",
            description="Create event",
            parameters_json_schema={"type": "object"},
            service="calendar",
            provider="google_workspace",
        )

        res = await tool.run_async(args={"summary": "Meeting with Client", "start_time": "2026-10-01T10:00:00Z"})
        assert res.get("requires_confirmation") is True
        assert "confirmation_request" in res
    finally:
        current_turn_context.reset(token)
