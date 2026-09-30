"""ADK before_tool_callback: Tool Argument Rehydration (Spec 03, R03.1).

Intercepts tool calls emitted by Vertex AI:
1. Detects surrogate tokens (<PERSON_1>, <IN_PAN_1>, <EMAIL_1>) in tool argument dictionaries.
2. Replaces tokens with real sensitive values from ephemeral SessionPiiVault.
3. Dispatches the rehydrated parameters to Agentgateway / upstream ERP (Zoho, Google Workspace).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.compliance.session_pii_vault import session_pii_vault

logger = logging.getLogger("workkbot.compliance.rehydration_callback")


def rehydrate_arguments(session_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Rehydrates surrogate tokens in argument dictionary with real values."""
    if not args:
        return args
    return session_pii_vault.rehydrate_dict(session_id, args)


def tool_rehydration_callback(
    tool_or_session_id: Any,
    args_dict: Optional[Dict[str, Any]] = None,
    tool_context: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Canonical Google ADK before_tool_callback.
    Supports both ADK (tool: BaseTool, args: dict, tool_context: ToolContext)
    and direct (session_id: str, args: dict) signatures.
    """
    # Direct function signature: tool_rehydration_callback(session_id, args)
    if isinstance(tool_or_session_id, str) and isinstance(args_dict, dict):
        session_id = tool_or_session_id
        return rehydrate_arguments(session_id, args_dict)

    # Canonical ADK signature: (tool, args, tool_context)
    tool = tool_or_session_id
    args = args_dict or {}

    session_id = (
        getattr(tool_context, "session_id", None)
        or getattr(getattr(tool_context, "session", None), "id", None)
        or "default_session"
    )

    rehydrated = rehydrate_arguments(session_id, args)
    if isinstance(args, dict):
        args.clear()
        args.update(rehydrated)

    # Tool Execution Budget Guardrail (Callback-based interceptor)
    state = getattr(tool_context, "state", None)
    if isinstance(state, dict):
        tool_name = getattr(tool, "name", "tool")
        call_count = state.get(f"{tool_name}_calls", 0) + 1
        state[f"{tool_name}_calls"] = call_count
        total_calls = state.get("total_tool_calls", 0) + 1
        state["total_tool_calls"] = total_calls
        if total_calls > 2 or call_count > 2:
            logger.warning("Tool call budget exceeded in callback guardrail for %s", tool_name)
            return {"error": "Maximum execution budget for tool calls (2) exceeded for this turn."}

    # Return rehydrated arguments dictionary
    return rehydrated
