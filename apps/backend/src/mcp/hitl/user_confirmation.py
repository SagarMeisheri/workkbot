"""In-Chat Human-In-The-Loop (HITL) Interactive Confirmation Handler (Spec 04, R04.4).

Implements the user approval gate:
- Calls ADK's `ToolContext.request_confirmation(hint=..., payload=...)` for mutating actions.
- Formats structured challenge data for assistant-ui's interactive `ApprovalCard`.
- Evaluates user response:
  - If approved: executes tool and returns result.
  - If declined: aborts execution safely and returns model instruction to offer alternatives.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("workkbot.mcp.hitl")


class HitlConfirmationHandler:
    """Coordinates tool execution pauses and user confirmations via ADK ToolContext."""

    @classmethod
    def build_confirmation_payload(
        cls,
        tool_name: str,
        parameters: Dict[str, Any],
        provider: str = "workspace",
        tool_call_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates structured metadata rendered by assistant-ui ApprovalCard."""
        destination_map = {
            "google_workspace": "Google Workspace (Calendar/Drive/Gmail)",
            "zoho_workplace": "Zoho Workplace (Books/CRM)",
            "slack": "Slack Workspace",
            "notion": "Notion Workspace",
        }
        destination = destination_map.get(provider, f"External Integration ({provider})")

        return {
            "type": "tool_confirmation_request",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "provider": provider,
            "destination": destination,
            "parameters": parameters,
            "risk_level": "critical",
            "title": f"Authorization Required: {tool_name.replace('_', ' ').title()}",
            "warning": "This action will create, modify, or send external corporate data.",
        }

    @classmethod
    async def execute_with_hitl_check(
        cls,
        tool_name: str,
        arguments: Dict[str, Any],
        is_critical: bool,
        executor_fn: Callable[[Dict[str, Any]], Any],
        tool_context: Optional[Any] = None,
        provider: str = "workspace",
        tool_call_id: Optional[str] = None,
    ) -> Any:
        """
        Executes read actions immediately.
        For critical actions, checks if user has approved; if not, requests confirmation.
        """
        async def _invoke_executor(params: Dict[str, Any]) -> Any:
            import inspect
            if inspect.iscoroutinefunction(executor_fn):
                return await executor_fn(params)
            res = executor_fn(params)
            if inspect.isawaitable(res):
                return await res
            return res

        if not is_critical:
            # Pure read action - execute directly without pause
            return await _invoke_executor(arguments)

        # Check if running under an ADK ToolContext with prior confirmation
        if tool_context is not None:
            confirmation = getattr(tool_context, "tool_confirmation", None)
            
            # If user has already approved, execute the tool
            if confirmation is not None:
                is_approved = False
                if isinstance(confirmation, dict):
                    is_approved = confirmation.get("confirmed", False) or confirmation.get("approved", False)
                elif hasattr(confirmation, "confirmed"):
                    is_approved = getattr(confirmation, "confirmed", False)
                elif hasattr(confirmation, "approved"):
                    is_approved = getattr(confirmation, "approved", False)
                elif confirmation is True:
                    is_approved = True

                if is_approved:
                    logger.info("Tool %s approved by user, proceeding with execution", tool_name)
                    return await _invoke_executor(arguments)
                else:
                    logger.info("Tool %s rejected by user", tool_name)
                    return {
                        "status": "declined",
                        "content": [{
                            "type": "text",
                            "text": "Action cancelled by user. Please suggest an alternative approach or ask for clarification.",
                        }],
                    }

            # First execution attempt: request interactive user confirmation
            payload = cls.build_confirmation_payload(
                tool_name=tool_name,
                parameters=arguments,
                provider=provider,
                tool_call_id=tool_call_id or getattr(tool_context, "function_call_id", None),
            )

            if hasattr(tool_context, "request_confirmation"):
                tool_context.request_confirmation(
                    hint=f"Authorization required to execute {tool_name}",
                    payload=payload,
                )
                logger.info("Requested confirmation for mutating tool %s", tool_name)
                return {
                    "status": "pending_approval",
                    "payload": payload,
                }

        # Fallback when tool_context is absent (e.g. standalone test mode)
        return await _invoke_executor(arguments)


hitl_handler = HitlConfirmationHandler
