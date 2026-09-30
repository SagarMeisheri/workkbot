"""Google Workspace MCP Client & ADK Dynamic Toolset Factory (Spec 04, R04.2).

Creates Google ADK 2.0 dynamic toolsets routing through Agentgateway on loopback (:8080),
enforcing parameter sanitization (CVE-2026-29791), classification, and audit trails.
"""
import logging
import time
from typing import Any, Callable, Dict, List, Optional
import httpx

from src.mcp.classifier import tool_classifier
from src.mcp.sanitizer import parameter_sanitizer
from src.mcp.audit import tool_audit
from src.mcp.hitl.user_confirmation import format_confirmation_request

logger = logging.getLogger("workkbot.mcp.client")

AGENTGATEWAY_BASE_URL = "http://127.0.0.1:8080"


class GoogleWorkspaceMCPClient:
    """Invokes Google Workspace Remote MCP tools through Agentgateway."""

    def __init__(self, gateway_url: str = AGENTGATEWAY_BASE_URL):
        self.gateway_url = gateway_url

    async def execute_tool(
        self,
        service: str,
        tool_name: str,
        arguments: Dict[str, Any],
        delegated_headers: Dict[str, str],
        user_id: str,
        org_id: str,
        session_id: str,
        confirmation_granted: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes an MCP tool through Agentgateway with full security guardrails:
        1. Classifies tool safety (read vs mutating write).
        2. Sanitizes input arguments (CVE-2026-29791).
        3. Enforces HITL pause if mutating and unconfirmed.
        4. Invokes Agentgateway on loopback with delegated headers.
        5. Logs immutable audit trail.
        """
        start_time = time.time()
        
        # 1. Classify safety
        safety_info = tool_classifier.classify(tool_name)
        if safety_info.is_critical and not confirmation_granted:
            challenge = format_confirmation_request(tool_name, arguments)
            # Record blocked turn in audit log
            await tool_audit.log_tool_invocation(
                user_id=user_id,
                org_id=org_id,
                session_id=session_id,
                provider="google_workspace",
                tool_name=tool_name,
                parameters=arguments,
                duration_ms=int((time.time() - start_time) * 1000),
                status="blocked_hitl",
            )
            return {
                "requires_confirmation": True,
                "confirmation_request": challenge.to_dict(),
            }

        # 2. Sanitize arguments
        sanitized_args = parameter_sanitizer.sanitize_arguments(arguments)

        # 3. Invoke Agentgateway route
        url = f"{self.gateway_url}/mcp/google/{service}"
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": sanitized_args,
            },
            "id": f"call_{int(time.time())}",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload, headers=delegated_headers)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if resp.status_code == 200:
                    import inspect
                    res_val = resp.json()
                    result = await res_val if inspect.iscoroutine(res_val) else res_val
                    status = "success"
                else:
                    result = {"error": resp.text, "status_code": resp.status_code}
                    status = "failed"
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = {"error": str(e)}
            status = "failed"
            logger.warning("Agentgateway MCP call failed: %s", e)

        # 4. Audit logging
        await tool_audit.log_tool_invocation(
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            provider="google_workspace",
            tool_name=tool_name,
            parameters=sanitized_args,
            result=result,
            duration_ms=duration_ms,
            status=status,
        )

        return result

    async def list_tools(

        self,
        service: str,
        delegated_headers: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Discovers available tools by querying the MCP server with JSON-RPC 'tools/list'.
        """
        url = f"{self.gateway_url}/mcp/google/{service}"
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": f"list_{service}_{int(time.time())}",
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.post(url, json=payload, headers=delegated_headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and "result" in data and "tools" in data["result"]:
                        return data["result"]["tools"]
        except Exception as e:
            logger.debug("Agentgateway MCP tools/list failed for %s: %s", service, e)
        return []


google_mcp_client = GoogleWorkspaceMCPClient()

