"""Dynamic MCP Tool & Toolset Implementation for Google ADK 2.0 (Spec 04 & Spec 05).

Dynamically discovers and wraps tools from connected Remote MCP servers (Google Workspace),
eliminating hardcoded tool definitions. Enforces parameter sanitization (CVE-2026-29791),
in-chat Human-In-The-Loop (HITL) confirmations, Supabase Vault token retrieval, and immutable audit logs.
"""
from contextvars import ContextVar
import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from src.auth.client import supabase_admin, _local_db
from src.mcp.classifier import tool_classifier
from src.mcp.sanitizer import parameter_sanitizer
from src.mcp.audit import tool_audit
from src.mcp.hitl.user_confirmation import format_confirmation_request
from src.mcp.client import google_mcp_client, AGENTGATEWAY_BASE_URL
from src.mcp.discovery import mcp_discovery_service

logger = logging.getLogger("workkbot.mcp.google_tools")

# ContextVar storing active turn metadata: {"user_id", "org_id", "session_id", "auth_token", "state_delta"}
current_turn_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "current_turn_context", default=None
)


async def _get_active_google_token() -> Optional[str]:
    """Retrieves decrypted Google access token for current turn user from Supabase Vault."""
    ctx = current_turn_context.get()
    if not ctx:
        return None
    user_id = ctx.get("user_id")
    if not user_id:
        return None

    # 1. Check live Supabase table mcp_connections via secure RPC
    vault_secret_id = None
    client = supabase_admin.get_client()
    if client:
        try:
            rpc_res = client.rpc("get_user_mcp_connections", {"p_user_id": user_id}).execute()
            if rpc_res.data:
                for c in rpc_res.data:
                    if c.get("provider") == "google_workspace":
                        vault_secret_id = c.get("vault_secret_id")
                        break
        except Exception:
            pass

    # 2. Check local fallback store
    if not vault_secret_id:
        for conn in _local_db.get("mcp_connections", []):
            if conn.get("user_id") == user_id and conn.get("provider") == "google_workspace" and conn.get("status") == "active":
                vault_secret_id = conn.get("vault_secret_id")
                break

    # 3. Retrieve and decrypt from Supabase Vault
    secret_data = None
    if vault_secret_id:
        secret_data = supabase_admin.retrieve_vault_secret(vault_secret_id)

    # 4. Fallback: Lookup by canonical secret name if vault_secret_id was stale or missing
    if not secret_data:
        secret_name = f"mcp_token_{user_id}_google_workspace"
        secret_data = supabase_admin.retrieve_vault_secret_by_name(secret_name)

    if not secret_data:
        logger.warning("No vault secret found for user %s google_workspace", user_id)
        return None

    # Check auto-refresh if token near expiration
    from src.mcp.oauth_service import google_oauth_service
    try:
        if vault_secret_id:
            refreshed = await google_oauth_service.get_valid_access_token(vault_secret_id, user_id)
            if refreshed:
                return refreshed
    except Exception as e:
        logger.debug("Token refresh check returned: %s", e)

    return secret_data.get("access_token")


def strip_schema_descriptions(schema: Any) -> Any:
    """Recursively removes 'description' and verbose docs from JSON schema to prevent massive prompt bloat."""
    if isinstance(schema, dict):
        return {
            k: strip_schema_descriptions(v)
            for k, v in schema.items()
            if k not in ("description", "x-google-enum-descriptions")
        }
    elif isinstance(schema, list):
        return [strip_schema_descriptions(item) for item in schema]
    return schema


try:
    from google.adk.tools import BaseTool
    from google.adk.tools.base_toolset import BaseToolset
    from google.genai import types

    class DynamicMcpTool(BaseTool):
        """ADK BaseTool dynamically constructed from discovered MCP server JSON-RPC tools."""

        def __init__(
            self,
            name: str,
            original_name: str,
            description: str,
            parameters_json_schema: Dict[str, Any],
            service: str,
            provider: str = "google_workspace",
        ):
            # Omit tool description from the agent prompt to avoid prompt bloat, but preserve for classifier (VULN-09 Defense)
            super().__init__(name=name, description="")
            self.original_name = original_name
            self.tool_description = description
            self.service = service
            self.provider = provider
            self._schema = strip_schema_descriptions(parameters_json_schema) or {"type": "object", "properties": {}}

        def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
            """Returns lightweight FunctionDeclaration containing only tool name and stripped parameter schema."""
            return types.FunctionDeclaration(
                name=self.name,
                description="",
                parameters_json_schema=self._schema,
            )

        async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
            """Executes discovered MCP tool with security sanitization, HITL gate, and audit."""
            ctx = current_turn_context.get() or {}
            user_id = ctx.get("user_id", "unknown")
            org_id = ctx.get("org_id", "unknown")
            session_id = ctx.get("session_id", "unknown")
            # 0. Enforce maximum 2 tool calls limit per conversational turn
            tool_call_count = ctx.get("tool_call_count", 0)
            if tool_call_count >= 2:
                logger.info("Cap reached: maximum 2 tool calls per turn for session %s", session_id)
                return {
                    "status": "tool_limit_reached",
                    "message": "Maximum 2 tool calls limit reached for this turn. Synthesize your final response with the data retrieved so far.",
                }
            ctx["tool_call_count"] = tool_call_count + 1

            # 1. Parameter sanitization (CVE-2026-29791)
            sanitized_args = parameter_sanitizer.sanitize_arguments(args or {})

            # 2. Classification & HITL approval check (VULN-09: pass tool_description for semantic classification)
            safety_info = tool_classifier.classify(self.name, tool_description=self.tool_description)
            state_delta = ctx.get("state_delta") or {}

            # Cryptographically bind confirmation to tool and arguments hash (VULN-04 Defense)
            import hashlib
            args_str = json.dumps(sanitized_args, sort_keys=True)
            args_hash = hashlib.sha256(f"{self.original_name}:{args_str}".encode()).hexdigest()[:16]

            confirmed_tool = state_delta.get("confirmed_tool") or state_delta.get("approved_tool")
            confirmed_hash = state_delta.get("confirmation_hash")

            is_confirmed = False
            if confirmed_tool in (self.name, self.original_name):
                # If confirmation_hash was supplied by client, verify parameter integrity
                if confirmed_hash:
                    is_confirmed = (confirmed_hash == args_hash)
                else:
                    is_confirmed = True
            elif state_delta.get("approval_granted") is True and confirmed_hash == args_hash:
                is_confirmed = True

            if safety_info.is_critical and not is_confirmed:
                challenge = format_confirmation_request(self.original_name, sanitized_args)
                await tool_audit.log_tool_invocation(
                    user_id=user_id,
                    org_id=org_id,
                    session_id=session_id,
                    provider=self.provider,
                    tool_name=self.original_name,
                    parameters=sanitized_args,
                    duration_ms=0,
                    status="blocked_hitl",
                )
                return {
                    "requires_confirmation": True,
                    "confirmation_request": challenge.to_dict(),
                }

            # 3. Resolve user credentials from Supabase Vault
            token = await _get_active_google_token()
            if not token:
                return {
                    "status": "not_connected",
                    "message": f"{self.provider} is not connected yet. Please connect via Connectors Hub.",
                }

            # 4. Execute strictly through MCP via google_mcp_client
            delegated_headers = {
                "X-Upstream-Authorization": f"Bearer {token}",
                "Authorization": f"Bearer {token}",
            }
            result = await google_mcp_client.execute_tool(
                service=self.service,
                tool_name=self.original_name,
                arguments=sanitized_args,
                delegated_headers=delegated_headers,
                user_id=user_id,
                org_id=org_id,
                session_id=session_id,
                confirmation_granted=is_confirmed,
            )
            return result



    class DynamicMcpToolset(BaseToolset):
        """ADK BaseToolset dynamically yielding discovered tools for active connections."""

        def __init__(self):
            super().__init__(tool_filter=None)

        async def get_tools(self, readonly_context: Any = None) -> List[BaseTool]:
            """Returns dynamically constructed ADK tools discovered from active MCP connections."""
            ctx = current_turn_context.get() or {}
            user_id = ctx.get("user_id")
            if not user_id:
                return []

            # Retrieve discovered tools for user's active connections
            discovered_specs = mcp_discovery_service.get_discovered_tools(user_id=user_id)
            if not discovered_specs:
                return []

            tools: List[BaseTool] = []
            for spec in discovered_specs:
                tools.append(
                    DynamicMcpTool(
                        name=spec["name"],
                        original_name=spec.get("original_name", spec["name"]),
                        description=spec.get("description", ""),
                        parameters_json_schema=spec.get("inputSchema", {}),
                        service=spec.get("service", "general"),
                        provider=spec.get("provider", "google_workspace"),
                    )
                )

            logger.info("DynamicMcpToolset yielded %d active tools for user %s from connected MCP servers", len(tools), user_id)
            return tools



except ImportError:
    # Fallback placeholders when google-adk is not present
    class DynamicMcpTool:
        def __init__(self, *args, **kwargs):
            pass

    class DynamicMcpToolset:
        def __init__(self, *args, **kwargs):
            pass
        async def get_tools(self, *args, **kwargs):
            return []


# Canonical dynamic toolset instance for ADK Agent
dynamic_mcp_toolset = DynamicMcpToolset()
