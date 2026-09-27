"""
Workkbot Local PoC: Dynamic MCP Tool Registry
Discovers tools dynamically from connected providers via tools/list.
Never hardcodes tools. If a service is disconnected, its tools disappear from the agent.
"""
from typing import Any, Dict, List, Optional
from src.core.injection_shield import InjectionShield
from src.core.hitl import HitlGatekeeper
from src.mcp.client_vault import ClientVault
from src.mcp.google_workspace import GoogleWorkspaceMcpProvider
from src.mcp.zoho_suite import ZohoMcpProvider
from src.mcp.models import McpTool, McpCallResult


class DynamicToolRegistry:
    def __init__(
        self,
        vault: ClientVault,
        shield: InjectionShield,
        hitl: HitlGatekeeper,
    ):
        self.vault = vault
        self.shield = shield
        self.hitl = hitl

        # Instantiate dynamic providers
        self.google_provider = GoogleWorkspaceMcpProvider(vault)
        self.zoho_provider = ZohoMcpProvider(vault)

    def set_provider_connection(self, provider_name: str, connected: bool):
        """
        Dynamically connects or disconnects a provider.
        """
        if provider_name == "google_workspace":
            self.google_provider.is_connected = connected
        elif provider_name == "zoho_mcp":
            self.zoho_provider.is_connected = connected

    def get_available_tools(self) -> List[McpTool]:
        """
        Dynamically aggregates all tools currently offered by connected MCP servers.
        Uses the provider's list_tools() endpoint.
        """
        tools: List[McpTool] = []
        if self.google_provider.is_connected:
            tools.extend(self.google_provider.list_tools())
        if self.zoho_provider.is_connected:
            tools.extend(self.zoho_provider.list_tools())
        return tools

    def get_tool(self, tool_name: str) -> Optional[McpTool]:
        for tool in self.get_available_tools():
            if tool.name == tool_name:
                return tool
        return None

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        bypass_hitl: bool = False,
    ) -> McpCallResult:
        """
        Executes a dynamically discovered tool with:
        1. Consent gate verification
        2. HITL write gate interception
        3. Provider execution
        4. Untrusted content shield wrapping
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return McpCallResult(
                tool_name=tool_name,
                server="unknown",
                success=False,
                data=None,
                error=f"Tool '{tool_name}' is not currently available from any connected provider.",
            )

        # 1. Verify consent
        allowed, msg = self.shield.verify_consent(tool_name)
        if not allowed:
            return McpCallResult(
                tool_name=tool_name,
                server=tool.server,
                success=False,
                data=None,
                error=msg,
            )

        # 2. Check if mutating and requires HITL approval
        if tool.is_mutating and not bypass_hitl:
            approval_req = self.hitl.create_approval_request(
                action_name=tool.name,
                target_service=tool.server,
                summary=f"Requesting approval to execute {tool.name} with arguments: {arguments}",
                payload=arguments,
            )
            return McpCallResult(
                tool_name=tool_name,
                server=tool.server,
                success=True,
                data={"status": "pending_approval", "message": "Action paused pending Human-In-The-Loop approval."},
                is_hitl_pending=True,
                hitl_request_id=approval_req.id,
            )

        # 3. Call the provider dynamically
        if tool.server == "google_workspace":
            res = self.google_provider.call_tool(tool.name, arguments)
        elif tool.server == "zoho_mcp":
            res = self.zoho_provider.call_tool(tool.name, arguments)
        else:
            return McpCallResult(
                tool_name=tool_name,
                server=tool.server,
                success=False,
                data=None,
                error=f"Unrecognized server: {tool.server}",
            )

        # 4. Wrap result in indirect prompt injection shield envelope
        if res.success and res.data:
            wrapped = self.shield.wrap_untrusted_content(tool.server, tool.name, res.data)
            res.data = wrapped

        return res
