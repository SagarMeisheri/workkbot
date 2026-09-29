"""ADK after_tool_callback: Tool Output PII Masking (Spec 03, R03.1).

Intercepts responses returned from external ERP / MCP tools:
1. Re-masks any known PII values using SessionPiiVault.
2. Runs Presidio to detect any newly returned PII from ERP databases (e.g. employee PAN, Aadhaar).
3. Replaces sensitive entities with tokens before the tool result re-enters LLM reasoning context.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.compliance.presidio_engine import presidio_engine
from src.compliance.session_pii_vault import session_pii_vault

logger = logging.getLogger("workkbot.compliance.output_mask_callback")


def mask_tool_output(session_id: str, tool_response: Any) -> Any:
    """Masks known and newly detected PII inside tool response payload."""
    if not tool_response:
        return tool_response

    # 1. Mask known sensitive values already in SessionPiiVault
    masked = session_pii_vault.mask_dict(session_id, tool_response)

    # 2. Check string fields for any newly returned PII from the ERP
    if isinstance(masked, str):
        findings = presidio_engine.analyze(masked)
        if findings:
            masked, _ = session_pii_vault.tokenize_text(session_id, masked, findings)
    elif isinstance(masked, dict):
        result = {}
        for k, v in masked.items():
            if isinstance(v, str):
                findings = presidio_engine.analyze(v)
                if findings:
                    sanitized, _ = session_pii_vault.tokenize_text(session_id, v, findings)
                    result[k] = sanitized
                else:
                    result[k] = v
            elif isinstance(v, (dict, list)):
                result[k] = mask_tool_output(session_id, v)
            else:
                result[k] = v
        masked = result
    elif isinstance(masked, list):
        masked = [mask_tool_output(session_id, item) for item in masked]

    return masked


def tool_output_mask_callback(
    tool_or_session_id: Any,
    args_dict_or_response: Optional[Any] = None,
    tool_context: Optional[Any] = None,
    tool_response: Optional[Any] = None,
) -> Any:
    """
    Canonical Google ADK after_tool_callback.
    Supports both ADK (tool, args, tool_context, tool_response)
    and direct (session_id, tool_response) signatures.
    """
    # Direct function signature: tool_output_mask_callback(session_id, tool_response)
    if isinstance(tool_or_session_id, str):
        session_id = tool_or_session_id
        response = args_dict_or_response
        return mask_tool_output(session_id, response)

    # Canonical ADK signature: (tool, args, tool_context, tool_response)
    session_id = (
        getattr(tool_context, "session_id", None)
        or getattr(getattr(tool_context, "session", None), "id", None)
        or "default_session"
    )

    masked_response = mask_tool_output(session_id, tool_response)
    return masked_response
