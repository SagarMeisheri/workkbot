"""Dynamic MCP Tool Wrapper for Google ADK 2.0 (Spec 04, R04.3 & R04.4).

Wraps dynamically discovered tools from Composio and Agentgateway:
- Classifies mutating vs. read-only actions (ToolSafetyClassifier)
- Intercepts mutating actions to trigger HITL gating (ToolContext.request_confirmation)
- Sanitizes dynamic arguments (McpParameterSanitizer / CVE-2026-29791)
- Emits immutable audit trails to Supabase and Cloud Logging with Composio log_id
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from src.mcp.audit import tool_audit_logger
from src.mcp.classifier import tool_classifier
from src.mcp.client import AgentgatewayMcpClient, agentgateway_client
from src.mcp.composio_service import composio_service
from src.mcp.hitl.user_confirmation import hitl_handler
from src.mcp.sanitizer import mcp_sanitizer

logger = logging.getLogger("workkbot.mcp.tools")

try:
    from google.adk.tools import BaseTool
except ImportError:
    class BaseTool:
        """Fallback tool base class when google-adk is mocked."""
        def __init__(self, name: str, description: str):
            self.name = name
            self.description = description


class DynamicMcpTool(BaseTool):
    """Dynamic tool bridging external MCP / Composio actions into Google ADK 2.0."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: Optional[Dict[str, Any]] = None,
        provider: str = "composio",
        is_critical: Optional[bool] = None,
        client: Optional[AgentgatewayMcpClient] = None,
    ):
        super().__init__(name=name, description=description)
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema or {}
        self.provider = provider
        self.client = client or agentgateway_client

        # If not explicitly specified, classify using heuristic safety classifier
        if is_critical is None:
            self.is_critical = tool_classifier.is_critical(
                tool_name=name,
                description=description,
                parameters_schema=self.parameters_schema,
            )
        else:
            self.is_critical = is_critical

    async def run_async(
        self,
        args: Dict[str, Any],
        tool_context: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes tool asynchronously with HITL gating, argument sanitization,
        and statutory audit logging.
        """
        start_time = time.time()
        user_id = getattr(tool_context, "user_id", "system_user")
        org_id = getattr(tool_context, "org_id", "system_org")
        session_id = getattr(tool_context, "session_id", None)

        # 1. Human-In-The-Loop gating for mutating actions (Spec 04, R04.4)
        if self.is_critical:
            decision, payload = hitl_handler.evaluate_confirmation(
                tool_name=self.name,
                arguments=args,
                provider=self.provider,
                tool_context=tool_context,
            )

            if decision == "pause":
                # First run: paused waiting for user confirmation card
                return {
                    "status": "pending_approval",
                    "tool_name": self.name,
                    "provider": self.provider,
                    "requires_confirmation": True,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Authorization required for mutating action: {self.name}",
                        }
                    ],
                }
            elif decision == "decline":
                # User declined execution via ApprovalCard
                duration_ms = int((time.time() - start_time) * 1000)
                tool_audit_logger.log_invocation(
                    user_id=user_id,
                    org_id=org_id,
                    session_id=session_id,
                    tool_name=self.name,
                    provider=self.provider,
                    parameters=args,
                    status="declined",
                    output={"message": "Action cancelled by user"},
                    duration_ms=duration_ms,
                )
                return {
                    "status": "declined",
                    "tool_name": self.name,
                    "provider": self.provider,
                    "content": [
                        {
                            "type": "text",
                            "text": f"Action cancelled by user: {self.name}",
                        }
                    ],
                }

        # 2. Sanitize parameters against CVE-2026-29791 (Spec 04, R04.2)
        sanitized_args = mcp_sanitizer.sanitize_arguments(args)

        # 3. Execute tool via Agentgateway or Composio session
        execution_error = None
        result = None
        composio_log_id = None

        try:
            if self.provider == "composio":
                comp_res = await composio_service.execute_tool(
                    session_id=session_id or f"sess_{user_id}",
                    tool_slug=self.name,
                    arguments=sanitized_args,
                )
                composio_log_id = comp_res.get("log_id")
                if comp_res.get("status") == "failed":
                    execution_error = comp_res.get("error", "Execution failed")
                else:
                    result = comp_res.get("data")
            else:
                gw_res = await self.client.execute_tool(
                    provider=self.provider,
                    tool_name=self.name,
                    arguments=sanitized_args,
                )
                if gw_res.get("status") == "failed":
                    execution_error = gw_res.get("error", "Agentgateway execution failed")
                else:
                    result = gw_res

        except Exception as exc:
            logger.error("Error executing dynamic tool %s: %s", self.name, exc)
            execution_error = str(exc)

        duration_ms = int((time.time() - start_time) * 1000)
        status = "failed" if execution_error else "success"

        # 4. Record statutory audit trail (Spec 04, R04.5)
        tool_audit_logger.log_invocation(
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            tool_name=self.name,
            provider=self.provider,
            parameters=sanitized_args,
            status="executed" if status == "success" else "failed",
            output=result,
            error_message=execution_error,
            duration_ms=duration_ms,
            composio_log_id=composio_log_id,
        )

        if execution_error:
            return {
                "status": "failed",
                "error": execution_error,
                "tool_name": self.name,
                "duration_ms": duration_ms,
                "composio_log_id": composio_log_id,
            }

        return {
            "status": "success",
            "data": result,
            "tool_name": self.name,
            "duration_ms": duration_ms,
            "composio_log_id": composio_log_id,
        }
