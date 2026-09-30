"""Human-In-The-Loop (HITL) User Confirmation Handler (Spec 04, R04.4).

Intercepts mutating actions (critical=True) and uses Google ADK 2.0
ToolContext.request_confirmation() to pause execution and challenge the active user
with an interactive ApprovalCard. Resumes execution cleanly upon user approval.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("workkbot.mcp.hitl")


class HitlConfirmationHandler:
    """Manages conversational HITL pause, approval, and decline lifecycle."""

    def evaluate_confirmation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        provider: str,
        tool_context: Any,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Evaluates confirmation state from ADK ToolContext.
        Returns:
            ("execute", confirmation_payload) -> user explicitly confirmed execution
            ("decline", confirmation_payload) -> user declined execution
            ("pause", None)                   -> first run, paused for confirmation
        """
        if not tool_context:
            # Standalone execution without context pauses by default
            return "pause", None

        # 1. Check if tool_confirmation is already present on tool_context
        confirmation = getattr(tool_context, "tool_confirmation", None)

        # Also inspect invocation context / event state if available
        if confirmation is None and hasattr(tool_context, "state"):
            state = getattr(tool_context, "state", {})
            if isinstance(state, dict):
                confirmation = state.get("tool_confirmation") or state.get("confirmed")

        if confirmation is not None:
            # Handle dictionary or ToolConfirmation model
            is_confirmed = False
            if isinstance(confirmation, dict):
                is_confirmed = bool(
                    confirmation.get("confirmed", False) or confirmation.get("approved", False)
                )
            else:
                is_confirmed = bool(getattr(confirmation, "confirmed", False))

            if is_confirmed:
                logger.info("HITL confirmed execution for tool: %s", tool_name)
                return "execute", confirmation if isinstance(confirmation, dict) else {"confirmed": True}
            else:
                logger.info("HITL declined execution for tool: %s", tool_name)
                return "decline", confirmation if isinstance(confirmation, dict) else {"confirmed": False}

        # 2. First execution: Challenge user via ADK ToolContext.request_confirmation
        hint = f"Authorization required for mutating action: {tool_name}"
        payload = {
            "tool_name": tool_name,
            "provider": provider,
            "arguments": arguments,
            "security_notice": "This action will modify external enterprise state.",
        }

        if hasattr(tool_context, "request_confirmation"):
            try:
                # ADK ToolContext accepts hint and payload
                tool_context.request_confirmation(hint=hint, payload=payload)
                logger.info("Requested HITL confirmation for tool: %s via ToolContext", tool_name)
            except Exception as e:
                logger.warning("Error calling ToolContext.request_confirmation: %s", e)

        return "pause", None


hitl_handler = HitlConfirmationHandler()
