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


class ToolAuditService:
    """Manages immutable audit trail of all MCP tool executions."""

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
        """Records tool execution record in Supabase and Google Cloud Logging."""
        invocation_id = str(uuid.uuid4())
        now_str = datetime.now(timezone.utc).isoformat()

        record = {
            "id": invocation_id,
            "org_id": org_id,
            "user_id": user_id,
            "session_id": session_id,
            "provider": provider,
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
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
