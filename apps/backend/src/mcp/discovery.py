"""Dynamic MCP Tool Discovery Service (Spec 04 & Spec 05).

Queries connected Remote MCP servers via standard JSON-RPC 'tools/list' protocol,
discovers all available tool declarations with JSON Schemas dynamically,
and registers them into the active Workkbot ADK runtime.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from src.auth.client import supabase_admin, _local_db
from src.mcp.client import google_mcp_client

logger = logging.getLogger("workkbot.mcp.discovery")

# Standard MCP Google Workspace catalog schemas (used when Agentgateway is offline in local dev)
STANDARD_GOOGLE_WORKSPACE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "calendar_list_events",
        "original_name": "calendar.list_events",
        "service": "calendar",
        "provider": "google_workspace",
        "description": "List upcoming meetings and events from the user's primary Google Calendar.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free text search terms to filter events that match.",
                },
                "time_min": {
                    "type": "string",
                    "description": "Lower bound for event end time in RFC3339 format.",
                },
                "time_max": {
                    "type": "string",
                    "description": "Upper bound for event start time in RFC3339 format.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default: 10).",
                },
            },
        },
    },
    {
        "name": "calendar_create_event",
        "original_name": "calendar.create_event",
        "service": "calendar",
        "provider": "google_workspace",
        "description": "Schedule a new meeting or event on the user's Google Calendar. Requires employee approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Title or summary of the meeting."},
                "start_time": {"type": "string", "description": "Start ISO datetime (e.g. 2026-10-01T10:00:00Z)."},
                "end_time": {"type": "string", "description": "End ISO datetime (e.g. 2026-10-01T11:00:00Z)."},
                "description": {"type": "string", "description": "Optional description of the meeting."},
                "location": {"type": "string", "description": "Meeting room or link location."},
            },
            "required": ["summary", "start_time", "end_time"],
        },
    },
    {
        "name": "gmail_search_threads",
        "original_name": "gmail.search_threads",
        "service": "gmail",
        "provider": "google_workspace",
        "description": "Search email threads and messages in the user's Gmail mailbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query expression."},
                "max_results": {"type": "integer", "description": "Maximum threads to retrieve."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "gmail_create_draft",
        "original_name": "gmail.create_draft",
        "service": "gmail",
        "provider": "google_workspace",
        "description": "Create a new email draft in the user's Gmail account. Requires employee approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Email address of recipient."},
                "subject": {"type": "string", "description": "Subject of the email."},
                "body": {"type": "string", "description": "Body message text."},
            },
            "required": ["recipient", "subject", "body"],
        },
    },
    {
        "name": "drive_search_files",
        "original_name": "drive.search_files",
        "service": "drive",
        "provider": "google_workspace",
        "description": "Search for files, Google Docs, and spreadsheets in Google Drive.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filename or keyword to search."},
                "page_size": {"type": "integer", "description": "Maximum files to return."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "docs_read_doc",
        "original_name": "docs.read_doc",
        "service": "docs",
        "provider": "google_workspace",
        "description": "Read the title and text content of a Google Document.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc file ID."},
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "sheets_read_sheet",
        "original_name": "sheets.read_sheet",
        "service": "sheets",
        "provider": "google_workspace",
        "description": "Read data from a Google Spreadsheet by spreadsheet ID and sheet range.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "Google Sheets ID."},
                "range_name": {"type": "string", "description": "A1 notation range (e.g. Sheet1!A1:D10)."},
            },
            "required": ["spreadsheet_id"],
        },
    },
]


class McpDiscoveryService:
    """Manages dynamic discovery of MCP tools upon client connection."""

    def __init__(self):
        # In-memory fast cache: { user_id: { provider: [tools] } }
        self._cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    async def discover_and_cache_tools(
        self,
        user_id: str,
        org_id: str,
        provider: str,
        access_token: str,
    ) -> List[Dict[str, Any]]:
        """
        Discovers tools dynamically from connected Remote MCP server via tools/list,
        and caches them for active conversational sessions.
        """
        discovered_tools: List[Dict[str, Any]] = []

        if provider == "google_workspace":
            services = ["calendar", "gmail", "drive", "docs", "sheets", "slides", "chat", "people"]
            for service in services:
                headers = {"X-Upstream-Authorization": f"Bearer {access_token}"}
                try:
                    server_tools = await google_mcp_client.list_tools(service, headers)
                    for t in server_tools:
                        raw_name = t.get("name", "")
                        clean_name = raw_name.replace(".", "_")
                        discovered_tools.append({
                            "name": clean_name,
                            "original_name": raw_name,
                            "service": service,
                            "provider": provider,
                            "description": t.get("description", f"Google {service} tool"),
                            "inputSchema": t.get("inputSchema", {"type": "object", "properties": {}}),
                        })
                except Exception as e:
                    logger.debug("Discovery on service %s failed: %s", service, e)

            # If gateway is offline or returned empty (local dev), load the standard catalog
            if not discovered_tools:
                logger.info(
                    "Agentgateway returned 0 remote tools; loading standard Google Workspace MCP catalog for user %s",
                    user_id,
                )
                discovered_tools = [dict(t) for t in STANDARD_GOOGLE_WORKSPACE_TOOLS]

        logger.info(
            "Discovered %d MCP tools for user %s provider %s",
            len(discovered_tools),
            user_id,
            provider,
        )

        # 1. Update in-memory registry
        user_dict = self._cache.setdefault(user_id, {})
        user_dict[provider] = discovered_tools

        # 2. Update local store
        for conn in _local_db.get("mcp_connections", []):
            if conn.get("user_id") == user_id and conn.get("provider") == provider:
                conn["discovered_tools"] = discovered_tools
                break

        return discovered_tools

    def get_discovered_tools(
        self,
        user_id: str,
        provider: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves currently discovered tools for the user's active connections."""
        # 1. Check in-memory cache
        user_dict = self._cache.get(user_id, {})
        if provider:
            if provider in user_dict:
                return user_dict[provider]
        elif user_dict:
            all_tools = []
            for plist in user_dict.values():
                all_tools.extend(plist)
            return all_tools

        # 2. Check local database for active connections
        for conn in _local_db.get("mcp_connections", []):
            if conn.get("user_id") == user_id and conn.get("status") == "active":
                p = conn.get("provider")
                if provider and p != provider:
                    continue
                tools = conn.get("discovered_tools")
                if tools:
                    user_dict[p] = tools
                    return tools
                # If active but not cached yet, provide default catalog
                if p == "google_workspace":
                    user_dict[p] = STANDARD_GOOGLE_WORKSPACE_TOOLS
                    return STANDARD_GOOGLE_WORKSPACE_TOOLS

        # 3. Check live Supabase table
        client = supabase_admin.get_client()
        if client:
            try:
                res = (
                    client.table("mcp_connections")
                    .select("provider, status")
                    .eq("user_id", user_id)
                    .eq("status", "active")
                    .execute()
                )
                if res.data:
                    for r in res.data:
                        p = r.get("provider")
                        if p == "google_workspace":
                            user_dict[p] = STANDARD_GOOGLE_WORKSPACE_TOOLS
                            return STANDARD_GOOGLE_WORKSPACE_TOOLS
            except Exception:
                pass

        return []

    def clear_user_tools(self, user_id: str, provider: Optional[str] = None):
        """Clears cached tools upon connector disconnection."""
        if user_id in self._cache:
            if provider:
                self._cache[user_id].pop(provider, None)
            else:
                self._cache.pop(user_id, None)


mcp_discovery_service = McpDiscoveryService()
