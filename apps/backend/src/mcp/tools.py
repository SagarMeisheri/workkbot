"""Dynamic MCP Tool & Toolset Implementation for Google ADK 2.0 (Spec 04 & Spec 05).

Dynamically discovers and wraps tools from connected Remote MCP servers across all providers
(Google Workspace, Zoho Workplace, Slack, Notion, GitHub, Jira, etc.), eliminating hardcoded tool definitions.
Enforces parameter sanitization (CVE-2026-29791), in-chat Human-In-The-Loop (HITL) confirmations,
Supabase Vault token retrieval, Tool Intent Routing (Tool RAG), and immutable audit logs.
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
from src.mcp.registry import connector_registry

logger = logging.getLogger("workkbot.mcp.tools")

# ContextVar storing active turn metadata: {"user_id", "org_id", "session_id", "auth_token", "state_delta", "turn_input"}
current_turn_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "current_turn_context", default=None
)


async def get_active_provider_token(provider: str, user_id: Optional[str] = None) -> Optional[str]:
    """Retrieves decrypted access token for given provider from Supabase Vault, refreshing if needed."""
    if not user_id:
        ctx = current_turn_context.get()
        if not ctx:
            return None
        user_id = ctx.get("user_id")
    if not user_id:
        return None

    # 1. Check live Supabase table mcp_connections via secure RPC or direct query
    vault_secret_id = None
    client = supabase_admin.get_client()
    if client:
        try:
            rpc_res = client.rpc("get_user_mcp_connections", {"p_user_id": user_id}).execute()
            if rpc_res.data:
                for c in rpc_res.data:
                    if c.get("provider") == provider:
                        vault_secret_id = c.get("vault_secret_id")
                        break
            if not vault_secret_id:
                tbl_res = client.table("mcp_connections").select("provider, vault_secret_id").eq("user_id", user_id).eq("status", "active").execute()
                if tbl_res.data:
                    for c in tbl_res.data:
                        if c.get("provider") == provider:
                            vault_secret_id = c.get("vault_secret_id")
                            break
        except Exception:
            pass

    # 2. Check local fallback store
    if not vault_secret_id:
        for conn in _local_db.get("mcp_connections", []):
            if conn.get("user_id") == user_id and conn.get("provider") == provider and conn.get("status") == "active":
                vault_secret_id = conn.get("vault_secret_id")
                break

    # 3. Retrieve and decrypt from Supabase Vault
    secret_data = None
    if vault_secret_id:
        secret_data = supabase_admin.retrieve_vault_secret(vault_secret_id)

    # 4. Fallback by canonical secret name if vault_secret_id was stale or missing
    if not secret_data:
        secret_name = f"mcp_token_{user_id}_{provider}"
        secret_data = supabase_admin.retrieve_vault_secret_by_name(secret_name)

    if not secret_data:
        logger.warning("No vault secret found for user %s provider %s", user_id, provider)
        return None

    # Check auto-refresh if token near expiration via provider adapter
    adapter = connector_registry.get(provider)
    if adapter and vault_secret_id:
        try:
            return await adapter.ensure_valid_token(vault_secret_id, user_id)
        except Exception as e:
            logger.debug("Token refresh returned: %s", e)

    return secret_data.get("access_token")


async def _get_active_google_token() -> Optional[str]:
    """Backward-compatible helper retrieving Google Workspace access token."""
    return await get_active_provider_token("google_workspace")


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


class ToolIntentRouter:
    """Sub-selects relevant tools based on user prompt and turn context to prevent prompt bloat (>25 tools)."""

    KEYWORD_MAPPINGS = {
        "gmail": ["email", "mail", "gmail", "inbox", "draft", "message", "send"],
        "calendar": ["calendar", "meeting", "event", "schedule", "reschedule", "invite", "time"],
        "drive": ["drive", "file", "folder", "document", "upload", "download"],
        "docs": ["doc", "document", "notes", "write", "summary"],
        "sheets": ["sheet", "spreadsheet", "csv", "row", "column", "formula", "cell", "data"],
        "slides": ["slide", "presentation", "deck", "powerpoint"],
        "chat": ["chat", "space", "message", "channel"],
        "people": ["contact", "person", "email", "directory", "colleague"],
        "zoho_workplace": ["zoho", "invoice", "gst", "bill", "tax", "lead", "crm", "customer", "vendor"],
        "zohobooks": ["zoho", "books", "item", "catalog", "inventory", "goods", "service", "price", "add", "new"],
        "zohobooks_vm": ["zoho", "books", "item", "catalog", "inventory", "goods", "service", "price", "add", "new"],
        "books": ["zoho", "books", "invoice", "bill", "gst", "accounting", "ledger", "payment", "item"],
        "crm": ["crm", "lead", "deal", "contact", "pipeline"],
        "slack": ["slack", "channel", "ping", "message", "dm", "workspace"],
        "notion": ["notion", "wiki", "page", "database", "workspace"],
        "atlassian": ["jira", "ticket", "sprint", "issue", "bug", "confluence"],
        "hubspot": ["hubspot", "deal", "contact", "marketing", "campaign"],
        "github": ["github", "pr", "pull request", "commit", "repo", "repository", "issue", "code"],
        "browser": ["browser", "web", "website", "navigate", "page", "click", "fill", "form", "portal", "dashboard", "open", "url"],
        "universal_browser": ["browser", "web", "website", "navigate", "page", "click", "fill", "form", "portal", "dashboard", "open", "url"],
    }

    def filter_tools(self, tools: List[Dict[str, Any]], query: str, max_tools: int = 12) -> List[Dict[str, Any]]:
        """Selects top matching tools if total count > 25, otherwise returns all tools."""
        if len(tools) <= 25:
            return tools

        query_lower = query.lower() if query else ""
        scored_tools = []
        for t in tools:
            score = 0
            provider = t.get("provider", "").lower()
            service = t.get("service", "").lower()
            name = t.get("name", "").lower()

            # Direct name/provider mention
            if provider and provider in query_lower:
                score += 10
            if service and service in query_lower:
                score += 8
            if name and name in query_lower:
                score += 15

            # Keyword heuristic match
            for key, kw_list in self.KEYWORD_MAPPINGS.items():
                if key in (provider, service):
                    for kw in kw_list:
                        if kw in query_lower:
                            score += 4

            scored_tools.append((score, t))

        # Sort by score descending
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        selected = [t for score, t in scored_tools if score > 0][:max_tools]
        if not selected:
            # Fallback to general/first max_tools if no specific keyword matched
            selected = [t for _, t in scored_tools[:max_tools]]

        return selected


tool_intent_router = ToolIntentRouter()


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

            # 0. Enforce maximum 10 tool calls limit per conversational turn
            tool_call_count = ctx.get("tool_call_count", 0)
            if tool_call_count >= 10:
                logger.info("Cap reached: maximum 10 tool calls per turn for session %s", session_id)
                return {
                    "status": "tool_limit_reached",
                    "message": "Maximum 10 tool calls limit reached for this turn. Synthesize your final response with the data retrieved so far.",
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

            # 2b. Special handler for Autonomous E2B Desktop Computer Use (Zoho Books Add Item)
            if self.name == "zoho_books_add_item" or self.service == "zohobooks_vm":
                from src.vm.sandbox_manager import desktop_manager
                from src.vm.zoho_books_operator import ZohoBooksItemOperator
                sandbox, sid, stream_url = desktop_manager.get_or_create_sandbox(
                    user_id=user_id,
                    org_id=org_id,
                    session_id=session_id,
                )
                state = desktop_manager.get_session_state(sid) or {}
                if not state.get("is_logged_in"):
                    desktop_manager.set_pending_item(sid, sanitized_args)
                    return {
                        "status": "awaiting_login",
                        "action": "open_split_stream",
                        "stream_url": stream_url,
                        "session_id": sid,
                        "item_name": sanitized_args.get("name"),
                        "selling_price": sanitized_args.get("selling_price"),
                        "message": (
                            f"Zoho Books login is required to add '{sanitized_args.get('name')}'. "
                            f"I have opened the interactive desktop in the Split View on your right. "
                            f"Please log in there, then click '[I Have Logged In - Proceed]' to create the item."
                        ),
                    }
                else:
                    operator = ZohoBooksItemOperator(sandbox)
                    await operator.navigate_to_new_item_page()
                    fill_res = await operator.fill_new_item_form(sanitized_args)
                    return {
                        "status": "awaiting_save_confirmation",
                        "action": "confirm_item_save",
                        "session_id": sid,
                        "item_name": sanitized_args.get("name"),
                        "selling_price": sanitized_args.get("selling_price"),
                        "cost_price": sanitized_args.get("cost_price"),
                        "details": fill_res,
                        "message": (
                            f"I have filled in the New Item form for '{sanitized_args.get('name')}' in Zoho Books. "
                            f"Please review the details in the Split View and confirm to save."
                        ),
                    }

            # 2c. Special handler for Universal Ref-Based Browser CDP tools
            if self.service == "universal_browser":
                from src.vm.sandbox_manager import desktop_manager
                from src.vm.universal_browser import UniversalBrowserSession
                sandbox, sid, stream_url = desktop_manager.get_or_create_sandbox(
                    user_id=user_id,
                    org_id=org_id,
                    session_id=session_id,
                )
                ub = UniversalBrowserSession(sandbox)
                if self.name == "browser_navigate":
                    res = await ub.navigate(sanitized_args.get("url", ""))
                    return {"status": "success", "result": res, "stream_url": stream_url, "session_id": sid}
                elif self.name == "browser_snapshot":
                    return await ub.snapshot()
                elif self.name == "browser_click":
                    return await ub.click(sanitized_args.get("target", ""))
                elif self.name == "browser_fill":
                    return await ub.fill(sanitized_args.get("target", ""), str(sanitized_args.get("value", "")))
                elif self.name == "browser_press_key":
                    return await ub.press_key(sanitized_args.get("key", "Enter"))

            # 3. Resolve user credentials from Supabase Vault for this tool's provider
            token = await get_active_provider_token(self.provider, user_id)
            if not token:
                return {
                    "status": "not_connected",
                    "message": f"{self.provider} is not connected yet. Please connect via Connectors Hub.",
                }

            # 4. Execute through McpGatewayClient with provider attribution
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
                provider=self.provider,
            )
            return result

    class DynamicMcpToolset(BaseToolset):
        """ADK BaseToolset dynamically yielding discovered tools for active connections."""

        def __init__(self):
            super().__init__(tool_filter=None)

        async def get_tools(self, readonly_context: Any = None) -> List[BaseTool]:
            """Returns dynamically constructed ADK tools discovered from active MCP connections and native VM tools."""
            ctx = current_turn_context.get() or {}
            user_id = ctx.get("user_id")
            if not user_id and readonly_context:
                user_id = getattr(readonly_context, "user_id", None) or getattr(getattr(readonly_context, "session", None), "user_id", None)

            if not user_id:
                return []

            # 1. Native Universal Browser CDP Tool specs and Zoho Books
            vm_specs = [
                {
                    "name": "browser_navigate",
                    "original_name": "browser_navigate",
                    "description": "Navigate the cloud browser to any website (e.g. Zoho Books, Vyapar, GST Portal, Shopify, Stripe, etc.).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to navigate to, e.g. https://books.zoho.in/app#/items/new"}
                        },
                        "required": ["url"]
                    },
                    "service": "universal_browser",
                    "provider": "browser",
                },
                {
                    "name": "browser_snapshot",
                    "original_name": "browser_snapshot",
                    "description": "Take a semantic accessibility snapshot of the current page. Returns interactive elements with reference IDs [ref=e1], labels, and types so you can interact with them without vision/screenshots.",
                    "inputSchema": {"type": "object", "properties": {}},
                    "service": "universal_browser",
                    "provider": "browser",
                },
                {
                    "name": "browser_click",
                    "original_name": "browser_click",
                    "description": "Click an element on the active web page by its reference ID (e.g. 'e1') or visible label.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "The element ref (e.g. 'e1') or visible label"}
                        },
                        "required": ["target"]
                    },
                    "service": "universal_browser",
                    "provider": "browser",
                },
                {
                    "name": "browser_fill",
                    "original_name": "browser_fill",
                    "description": "Fill text into an input field or textarea by its reference ID (e.g. 'e4') or label.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string", "description": "The element ref (e.g. 'e4') or label"},
                            "value": {"type": "string", "description": "The text value to enter"}
                        },
                        "required": ["target", "value"]
                    },
                    "service": "universal_browser",
                    "provider": "browser",
                },
                {
                    "name": "browser_press_key",
                    "original_name": "browser_press_key",
                    "description": "Press a keyboard key on the active web page, e.g. 'Enter', 'Tab', 'Escape'.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "Keyboard key to press, e.g. 'Enter'"}
                        },
                        "required": ["key"]
                    },
                    "service": "universal_browser",
                    "provider": "browser",
                },
                {
                    "name": "zoho_books_add_item",
                    "original_name": "zoho_books_add_item",
                    "description": "Add a new inventory or service item into Zoho Books catalog via autonomous Desktop Computer Use.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the item, e.g. Royal Basmati Rice 5kg"},
                            "type": {"type": "string", "enum": ["Goods", "Service"], "description": "Type of item"},
                            "unit": {"type": "string", "description": "Unit of measurement, e.g. bag, pcs, kg, box"},
                            "selling_price": {"type": "number", "description": "Selling Price in INR"},
                            "cost_price": {"type": "number", "description": "Cost Price in INR"},
                            "description": {"type": "string", "description": "Description of the item"}
                        },
                        "required": ["name", "selling_price"]
                    },
                    "service": "zohobooks_vm",
                    "provider": "zohobooks",
                },
            ]

            # 2. Retrieve discovered tools for user's active connections
            discovered_specs = mcp_discovery_service.get_discovered_tools(user_id=user_id) or []
            all_specs = vm_specs + discovered_specs

            turn_input = ctx.get("turn_input") or ctx.get("user_message") or ctx.get("message") or ""
            selected_specs = tool_intent_router.filter_tools(all_specs, turn_input)

            tools: List[BaseTool] = []
            for spec in selected_specs:
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

            logger.info(
                "DynamicMcpToolset yielded %d active tools for user %s",
                len(tools),
                user_id,
            )
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
