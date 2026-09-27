"""
Workkbot Local PoC: Model Context Protocol (MCP) Standard Models
Conforms to official MCP specifications for Tool discovery and execution.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class McpTool:
    """
    Standard MCP Tool definition exposed by an MCP Server via tools/list.
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    server: str  # e.g., "google_workspace" or "zoho_mcp"
    category: str  # e.g., "Email", "Drive", "Calendar", "CRM", "Books", "Desk"
    is_mutating: bool = False  # If True, triggers Human-In-The-Loop (HITL) gate


@dataclass
class McpCallResult:
    """
    Standard MCP tool invocation response.
    """
    tool_name: str
    server: str
    success: bool
    data: Any
    is_hitl_pending: bool = False
    hitl_request_id: Optional[str] = None
    error: Optional[str] = None
