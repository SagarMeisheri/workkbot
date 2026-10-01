"""Tests for Tool Intent Router & 20-Connector Scalability (Spec 04 & Spec 05)."""
import pytest
from src.mcp.tools import ToolIntentRouter, tool_intent_router, DynamicMcpToolset, current_turn_context
from src.auth.client import _local_db


def test_intent_router_returns_all_tools_when_under_threshold():
    """When total discovered tools <= 25, router leaves all tools intact."""
    mock_tools = [
        {"name": f"tool_{i}", "provider": "google_workspace", "service": "drive"}
        for i in range(20)
    ]
    result = tool_intent_router.filter_tools(mock_tools, query="check my schedule")
    assert len(result) == 20


def test_intent_router_subselects_relevant_tools_when_over_threshold():
    """When tools > 25 (e.g. 60 tools across Google, Zoho, Slack, Jira), router picks relevant 8-12 tools."""
    tools = []
    # 20 calendar tools
    for i in range(20):
        tools.append({"name": f"calendar_event_{i}", "provider": "google_workspace", "service": "calendar"})
    # 20 zoho invoice tools
    for i in range(20):
        tools.append({"name": f"zoho_invoice_{i}", "provider": "zoho_workplace", "service": "books"})
    # 20 slack tools
    for i in range(20):
        tools.append({"name": f"slack_message_{i}", "provider": "slack", "service": "chat"})

    assert len(tools) == 60

    # User asks about invoices
    filtered_invoice = tool_intent_router.filter_tools(tools, query="Can you list recent GST invoices for ABC Corp?", max_tools=10)
    assert len(filtered_invoice) <= 10
    assert any("zoho" in t["provider"] for t in filtered_invoice)
    # Shouldn't be flooded with slack tools
    assert all("slack" not in t["provider"] for t in filtered_invoice)

    # User asks about calendar/meeting
    filtered_cal = tool_intent_router.filter_tools(tools, query="What meetings do I have scheduled this afternoon?", max_tools=10)
    assert len(filtered_cal) <= 10
    assert any("calendar" in t["service"] for t in filtered_cal)
    assert all("zoho" not in t["provider"] for t in filtered_cal)


@pytest.mark.asyncio
async def test_dynamic_mcp_toolset_with_intent_filtering():
    """Verifies DynamicMcpToolset uses turn_input to filter tools when > 25 exist."""
    user_id = "test-intent-toolset-user"
    org_id = "test-intent-org"

    # Create 40 tools: 20 calendar, 20 zoho
    mock_tools = []
    for i in range(20):
        mock_tools.append({
            "name": f"calendar_tool_{i}",
            "original_name": f"calendar.tool_{i}",
            "service": "calendar",
            "provider": "google_workspace",
            "description": "Calendar tool",
            "inputSchema": {"type": "object", "properties": {}},
        })
    for i in range(20):
        mock_tools.append({
            "name": f"zoho_books_{i}",
            "original_name": f"books.tool_{i}",
            "service": "books",
            "provider": "zoho_workplace",
            "description": "Zoho Books tool",
            "inputSchema": {"type": "object", "properties": {}},
        })

    _local_db["mcp_connections"].append({
        "id": "conn-intent-test",
        "user_id": user_id,
        "org_id": org_id,
        "provider": "google_workspace",
        "status": "active",
        "discovered_tools": mock_tools,
    })

    toolset = DynamicMcpToolset()

    token = current_turn_context.set({
        "user_id": user_id,
        "org_id": org_id,
        "turn_input": "Find GST invoices in Zoho",
    })
    try:
        active_tools = await toolset.get_tools()
        assert len(active_tools) <= 12
        tool_names = [t.name for t in active_tools]
        assert any("zoho" in n for n in tool_names)
    finally:
        current_turn_context.reset(token)
