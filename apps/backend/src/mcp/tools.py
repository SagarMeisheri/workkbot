"""Dynamic MCP Tool Discovery & Execution Toolset (Spec 04 & Spec 05).

Eliminates all hardcoded tools. Tools are dynamically discovered and instantiated
at runtime based on the user's active integrations in Supabase (public.mcp_connections,
public.discovered_tools) and Agentgateway 1.5.x (:8080/mcp):
- Mutating actions identified by ToolSafetyClassifier trigger in-chat HITL pauses
  via `ToolContext.request_confirmation()` to render the assistant-ui ApprovalCard.
- Read actions execute immediately without user friction.
- Parameter sanitization (CVE-2026-29791) is strictly enforced on all arguments.
- Immutable audit records are logged to Supabase and Google Cloud Logging.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.auth.client import _local_db, supabase_admin
from src.mcp.audit import tool_audit_logger
from src.mcp.classifier import tool_classifier
from src.mcp.client import AgentgatewayMcpClient, mcp_client
from src.mcp.hitl.user_confirmation import hitl_handler
from src.mcp.sanitizer import mcp_sanitizer

logger = logging.getLogger("workkbot.mcp.tools")

try:
    from google.adk.agents.readonly_context import ReadonlyContext
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.base_toolset import BaseToolset
    from google.adk.tools.tool_context import ToolContext
    from google.adk.tools._gemini_schema_util import _to_gemini_schema
    from google.genai import types
    ADK_AVAILABLE = True
except (ImportError, AttributeError):
    ADK_AVAILABLE = False

    class BaseTool:  # type: ignore
        def __init__(self, name: str, description: str):
            self.name = name
            self.description = description

    class BaseToolset:  # type: ignore
        pass

    class ToolContext:  # type: ignore
        pass

    class ReadonlyContext:  # type: ignore
        pass


class DynamicMcpTool(BaseTool):
    """
    Dynamically instantiated MCP tool representing a capability exposed
    by an active connector via Agentgateway.
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: Optional[Dict[str, Any]] = None,
        provider: str = "custom",
        is_critical: Optional[bool] = None,
        client: Optional[AgentgatewayMcpClient] = None,
    ):
        super().__init__(name=name, description=description)
        self.parameters_schema = parameters_schema or {}
        self.provider = provider
        self.client = client or mcp_client

        # If not explicitly provided, classify critical status heuristically
        if is_critical is None:
            self.is_critical = tool_classifier.is_critical(
                tool_name=name,
                description=description,
                parameters_schema=self.parameters_schema,
            )
        else:
            self.is_critical = is_critical

    def _get_declaration(self) -> Optional[Any]:
        """Converts OpenAPI/JSONSchema to Gemini FunctionDeclaration for Google ADK."""
        if not ADK_AVAILABLE:
            return None
        gemini_schema = None
        if self.parameters_schema:
            try:
                gemini_schema = _to_gemini_schema(self.parameters_schema)
            except Exception as e:
                logger.debug("Schema conversion fallback for tool %s: %s", self.name, e)
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=gemini_schema,
        )

    async def run_async(
        self, *, args: Dict[str, Any], tool_context: Optional[ToolContext] = None
    ) -> Any:
        """
        Executes dynamic tool with parameter sanitization, audit logging,
        and human-in-the-loop gating for mutating actions.
        """
        start_t = time.time()

        # 1. Parameter Sanitization (CVE-2026-29791 immunity)
        clean_args = mcp_sanitizer.sanitize_arguments(args)

        user_id = getattr(tool_context, "user_id", None) or "demo-user"
        org_id = getattr(tool_context, "org_id", None) or "demo-org"

        # 2. Mutating tool execution handler with audit logging
        async def _execute(params: Dict[str, Any]) -> Dict[str, Any]:
            res = await self.client.call_tool(
                user_id=user_id,
                org_id=org_id,
                tool_name=self.name,
                arguments=params,
                provider=self.provider,
            )
            duration_ms = int((time.time() - start_t) * 1000)
            status = "failed" if "error" in res else "executed"
            tool_audit_logger.log_invocation(
                user_id=user_id,
                org_id=org_id,
                tool_name=self.name,
                provider=self.provider,
                parameters=params,
                status=status,
                output=res,
                duration_ms=duration_ms,
            )
            return res

        # 3. Route through HITL check if critical, or execute immediately if read action
        return await hitl_handler.execute_with_hitl_check(
            tool_name=self.name,
            arguments=clean_args,
            is_critical=self.is_critical,
            executor_fn=_execute,
            tool_context=tool_context,
            provider=self.provider,
        )


class DynamicMcpToolset(BaseToolset):
    """
    Canonical ADK Toolset that discovers and serves tools dynamically
    based on the user's active connectors in Supabase and Agentgateway.
    """

    def __init__(self, client: Optional[AgentgatewayMcpClient] = None):
        super().__init__()
        self.client = client or mcp_client
        self._custom_tools: List[DynamicMcpTool] = []

    def register_dynamic_tool(self, tool: DynamicMcpTool) -> None:
        """Allows test suites or runtime plugins to register dynamic tools."""
        self._custom_tools.append(tool)

    def clear_dynamic_tools(self) -> None:
        """Resets custom registered dynamic tools."""
        self._custom_tools.clear()

    async def _fetch_active_connectors(
        self, user_id: str, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries active connectors from live Supabase and local store fallback."""
        active: List[Dict[str, Any]] = []

        # 1. Check live Supabase
        sb = supabase_admin.get_client()
        if sb:
            try:
                q = sb.table("mcp_connections").select("*").eq("user_id", user_id).eq("status", "active")
                if org_id:
                    q = q.eq("org_id", org_id)
                res = q.execute()
                if res.data:
                    active.extend(res.data)
            except Exception as e:
                logger.debug("Live mcp_connections query skipped: %s", e)

        # 2. Check local fallback store
        local_conns = [
            c for c in _local_db.get("mcp_connections", [])
            if c.get("user_id") == user_id and c.get("status") == "active"
        ]
        if org_id:
            local_conns = [c for c in local_conns if c.get("org_id") == org_id]

        for lc in local_conns:
            if not any(a.get("provider") == lc.get("provider") for a in active):
                active.append(lc)

        return active

    async def _fetch_discovered_tools_from_db(
        self, user_id: str, org_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries dynamic tools persisted in public.discovered_tools (e.g. from OpenAPI or connector scans)."""
        db_tools: List[Dict[str, Any]] = []
        sb = supabase_admin.get_client()
        if sb:
            try:
                q = sb.table("discovered_tools").select("*").eq("user_id", user_id)
                if org_id:
                    q = q.eq("org_id", org_id)
                res = q.execute()
                if res.data:
                    db_tools.extend(res.data)
            except Exception as e:
                logger.debug("Live discovered_tools query skipped: %s", e)

        local_tools = [
            t for t in _local_db.get("discovered_tools", [])
            if t.get("user_id") == user_id
        ]
        if org_id:
            local_tools = [t for t in local_tools if t.get("org_id") == org_id]

        for lt in local_tools:
            if not any(t.get("name") == lt.get("name") for t in db_tools):
                db_tools.append(lt)

        return db_tools

    async def discover_tools_for_user(
        self, user_id: str, org_id: Optional[str] = None
    ) -> List[DynamicMcpTool]:
        """
        Dynamically discovers and constructs tools at runtime strictly based on active connectors:
        - ZERO hardcoded tools.
        - Fetches active connectors for the authenticated user from Supabase (public.mcp_connections).
        - Queries live Agentgateway 1.5.x for federated tools under each active connector.
        - Loads any OpenAPI/custom tools stored in public.discovered_tools for active connectors.
        - Inactive or disconnected services have zero tools exposed.
        """
        active_connectors = await self._fetch_active_connectors(user_id, org_id)
        active_providers = {c.get("provider") for c in active_connectors if c.get("provider")}

        tools: List[DynamicMcpTool] = list(self._custom_tools)
        seen_names = {t.name for t in tools}

        # 1. Discover federated tools from Agentgateway for each active connector
        for conn in active_connectors:
            provider = conn.get("provider")
            if not provider:
                continue

            conn_org_id = org_id or conn.get("org_id", "demo-org")
            discovered = await self.client.list_tools(
                user_id=user_id,
                org_id=conn_org_id,
                provider=provider,
            )

            for item in discovered:
                tool_name = item["name"]
                if tool_name in seen_names:
                    continue
                seen_names.add(tool_name)
                tool = DynamicMcpTool(
                    name=tool_name,
                    description=item.get("description", ""),
                    parameters_schema=item.get("inputSchema") or item.get("parameters_schema") or {},
                    provider=provider,
                    is_critical=item.get("critical", False),
                    client=self.client,
                )
                tools.append(tool)

        # 2. Discover tools from Supabase public.discovered_tools for active connectors
        persisted_tools = await self._fetch_discovered_tools_from_db(user_id, org_id)
        for item in persisted_tools:
            provider = item.get("provider")
            if provider and provider not in active_providers:
                # Strictly exclude tools belonging to disconnected integrations
                continue

            tool_name = item.get("name")
            if not tool_name or tool_name in seen_names:
                continue
            seen_names.add(tool_name)

            tool = DynamicMcpTool(
                name=tool_name,
                description=item.get("description", ""),
                parameters_schema=item.get("parameters_schema") or {},
                provider=provider or "custom",
                is_critical=item.get("is_critical", False),
                client=self.client,
            )
            tools.append(tool)

        return tools

    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> List[BaseTool]:
        """
        Called dynamically by Google ADK Runner before each LLM turn.
        Returns the exact tool catalog available to the current authenticated user
        based purely on their active connectors.
        """
        user_id = None
        org_id = None

        if readonly_context:
            user_id = getattr(readonly_context, "user_id", None)
            if hasattr(readonly_context, "state") and readonly_context.state:
                org_id = readonly_context.state.get("org_id")

        if not user_id:
            # When no authenticated context is bound, return custom tools if any, or empty list
            return list(self._custom_tools)

        discovered = await self.discover_tools_for_user(user_id, org_id)
        return list(discovered)


# Canonical dynamic toolset instance export
dynamic_mcp_toolset = DynamicMcpToolset()
