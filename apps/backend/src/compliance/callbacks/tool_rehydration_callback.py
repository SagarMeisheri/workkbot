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


# Track per-session turn tool call count to enforce limit of 3 at max
_TURN_TOOL_CALL_COUNTS: Dict[str, int] = {}


def reset_turn_tool_call_count(session_id: str) -> None:
    """Resets the tool call counter at the beginning of a conversational turn."""
    _TURN_TOOL_CALL_COUNTS[session_id] = 0


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
        getattr(getattr(tool_context, "session", None), "id", None)
        or getattr(tool_context, "session_id", None)
        or "default_session"
    )
    if not isinstance(session_id, str):
        session_id = str(session_id)

    rehydrated = rehydrate_arguments(session_id, args)
    if isinstance(args, dict):
        args.clear()
        args.update(rehydrated)

    # Enforce maximum tool call limit of 3 per turn
    current_count = _TURN_TOOL_CALL_COUNTS.get(session_id, 0) + 1
    _TURN_TOOL_CALL_COUNTS[session_id] = current_count
    if current_count > 3:
        tool_name = getattr(tool, "name", "tool")
        logger.warning(
            "Tool call limit exceeded in turn for session=%s (call %d > 3 for tool=%s). Forcing summarization.",
            session_id, current_count, tool_name
        )
        return {
            "status": "limit_reached",
            "tool_calls_executed": current_count - 1,
            "error": "Per-turn tool call limit reached (maximum 3 calls). Do not call any more tools. Please synthesize and summarize the information retrieved so far for the user."
        }

    # CRITICAL: Return None in ADK so ADK executes the actual tool runner instead of short-circuiting!
    return None
