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

        logger.info(
            "Discovered %d MCP tools for user %s provider %s from connected MCP server",
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
        """Retrieves currently discovered tools for all of the user's active MCP connections."""
        user_dict = self._cache.setdefault(user_id, {})

        # 1. Inspect local DB for active connections
        for conn in _local_db.get("mcp_connections", []):
            if conn.get("user_id") == user_id and conn.get("status") == "active":
                p = conn.get("provider")
                if provider and p != provider:
                    continue
                tools = conn.get("discovered_tools")
                if tools:
                    user_dict[p] = tools

        # 2. Check live Supabase table for active connections with stored tools
        client = supabase_admin.get_client()
        if client:
            try:
                res = (
                    client.table("mcp_connections")
                    .select("provider, status, discovered_tools")
                    .eq("user_id", user_id)
                    .eq("status", "active")
                    .execute()
                )
                if res.data:
                    for r in res.data:
                        p = r.get("provider")
                        if provider and p != provider:
                            continue
                        tools = r.get("discovered_tools")
                        if tools and p not in user_dict:
                            user_dict[p] = tools
            except Exception:
                pass

        if provider:
            return user_dict.get(provider, [])

        all_tools: List[Dict[str, Any]] = []
        for p_tools in user_dict.values():
            all_tools.extend(p_tools)
        return all_tools

    def clear_user_tools(self, user_id: str, provider: Optional[str] = None):
        """Clears cached tools upon connector disconnection."""
        if user_id in self._cache:
            if provider:
                self._cache[user_id].pop(provider, None)
            else:
                self._cache.pop(user_id, None)


mcp_discovery_service = McpDiscoveryService()
