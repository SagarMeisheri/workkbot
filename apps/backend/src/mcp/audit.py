"""Tool Execution Audit Service (Supabase & Google Cloud Logging, Spec 04, R04.5).

Emits immutable audit logs to Supabase `public.tool_invocations` table and
writes structured JSON telemetry to Google Cloud Logging.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.auth.client import supabase_admin, _local_db

logger = logging.getLogger("workkbot.mcp.audit")

# Optional Google Cloud Logging integration
try:
    from google.cloud import logging as gcp_logging
    _gcp_logging_client = gcp_logging.Client()
    _gcp_logger = _gcp_logging_client.logger("workkbot-tool-invocations")
except Exception:
    _gcp_logger = None


import re

# PII & Secret Redaction Patterns (VULN-05 Defense & India DPDP Act 2023)
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
SENSITIVE_KEY_PATTERN = re.compile(r"(token|secret|password|authorization|credential|api_key|private_key)", re.IGNORECASE)


def scrub_sensitive_audit_payload(val: Any, key_name: str = "") -> Any:
    """Scrubs secrets, tokens, and PII from parameters and results before persisting to audit tables."""
    if isinstance(val, dict):
        scrubbed = {}
        for k, v in val.items():
            if SENSITIVE_KEY_PATTERN.search(k):
                scrubbed[k] = "[REDACTED_SECRET]"
            else:
                scrubbed[k] = scrub_sensitive_audit_payload(v, key_name=k)
        return scrubbed
    elif isinstance(val, list):
        return [scrub_sensitive_audit_payload(item, key_name=key_name) for item in val]
    elif isinstance(val, str):
        if SENSITIVE_KEY_PATTERN.search(key_name):
            return "[REDACTED_SECRET]"
        if AADHAAR_PATTERN.search(val):
            val = AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", val)
        if PAN_PATTERN.search(val):
            val = PAN_PATTERN.sub("[REDACTED_PAN]", val)
        # Cap oversized document strings at 4000 characters to prevent excessive retention of customer IP
        if len(val) > 4000:
            val = val[:4000] + "... [TRUNCATED FOR DATA RETENTION]"
        return val
    return val


class ToolAuditService:
    """Manages immutable audit trail of all MCP tool executions with PII scrubbing."""

    async def log_tool_invocation(
        self,
        user_id: str,
        org_id: str,
        session_id: str,
        provider: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        duration_ms: int = 0,
        status: str = "success",
    ) -> str:
        """Records tool execution record in Supabase and Google Cloud Logging with PII redaction."""
        invocation_id = str(uuid.uuid4())
        now_str = datetime.now(timezone.utc).isoformat()

        scrubbed_params = scrub_sensitive_audit_payload(parameters)
        scrubbed_result = scrub_sensitive_audit_payload(result) if result is not None else None

        record = {
            "id": invocation_id,
            "org_id": org_id,
            "user_id": user_id,
            "session_id": session_id,
            "provider": provider,
            "tool_name": tool_name,
            "parameters": scrubbed_params,
            "result": scrubbed_result,
            "execution_duration_ms": duration_ms,
            "status": status,
            "created_at": now_str,
        }

        # 1. Write to live Supabase table if available
        client = supabase_admin.get_client()
        if client:
            try:
                client.table("tool_invocations").insert(record).execute()
            except Exception as e:
                logger.warning("Failed to insert tool_invocations into live Supabase: %s", e)

        # 2. Maintain local fallback mirror for zero-latency testing
        if "tool_invocations" not in _local_db:
            _local_db["tool_invocations"] = []
        _local_db["tool_invocations"].append(record)

        # 3. Emit structured log entry to Google Cloud Logging
        log_payload = {
            "event": "mcp_tool_invocation",
            "invocation_id": invocation_id,
            "user_id": user_id,
            "org_id": org_id,
            "session_id": session_id,
            "provider": provider,
            "tool_name": tool_name,
            "execution_duration_ms": duration_ms,
            "status": status,
            "timestamp": now_str,
        }
        if _gcp_logger:
            try:
                _gcp_logger.log_struct(log_payload, severity="INFO")
            except Exception:
                pass
        
        logger.info(
            "Tool audit recorded: tool=%s status=%s duration=%dms id=%s",
            tool_name,
            status,
            duration_ms,
            invocation_id,
        )
        return invocation_id


tool_audit = ToolAuditService()
