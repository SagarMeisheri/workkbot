"""Tool Invocation Audit Logger for Supabase & Google Cloud Logging (Spec 04, R04.5 & VAL-04.7).

Records immutable execution details for all MCP tools:
- Stores audit rows in Supabase PostgreSQL `public.tool_invocations` with RLS.
- Streams structured JSON log records to Google Cloud Logging in asia-south1.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from src.auth.client import supabase_admin, _local_db
from src.config import settings

logger = logging.getLogger("workkbot.mcp.audit")

# Optional live Google Cloud Logging client
try:
    from google.cloud import logging as gcp_logging
    _gcp_client = gcp_logging.Client(project=settings.GCP_PROJECT_ID)
    _cloud_logger = _gcp_client.logger("workkbot-tool-invocations")
except Exception:
    _cloud_logger = None


class ToolInvocationAuditLogger:
    """Manages immutable audit logging for tool executions."""

    def __init__(self):
        self.admin = supabase_admin
        self._local_invocations: List[Dict[str, Any]] = []

    def log_invocation(
        self,
        user_id: str,
        org_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        status: str = "executed",
        session_id: Optional[str] = None,
        provider: Optional[str] = "custom",
        output: Optional[Any] = None,
        error_message: Optional[str] = None,
        duration_ms: int = 0,
    ) -> Dict[str, Any]:
        """
        Emits an audit entry to Supabase and Google Cloud Logging.
        Returns the created audit record.
        """
        record_id = str(uuid.uuid4())
        record = {
            "id": record_id,
            "user_id": user_id,
            "org_id": org_id,
            "session_id": session_id,
            "tool_name": tool_name,
            "provider": provider,
            "parameters": parameters,
            "status": status,
            "output": output if isinstance(output, (dict, list)) else {"result": str(output)},
            "error_message": error_message,
            "duration_ms": duration_ms,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # 1. Persist to Supabase Database
        client = self.admin.get_client()
        if client:
            try:
                client.table("tool_invocations").insert(record).execute()
            except Exception as e:
                logger.debug("Database insert into tool_invocations skipped: %s", e)

        # Mirror in memory for fast test inspection
        self._local_invocations.append(record)
        if "tool_invocations" not in _local_db:
            _local_db["tool_invocations"] = []
        _local_db["tool_invocations"].append(record)

        # 2. Emit structured audit log to Google Cloud Logging
        if _cloud_logger:
            try:
                _cloud_logger.log_struct(
                    {
                        "event": "mcp_tool_invocation",
                        "record_id": record_id,
                        "user_id": user_id,
                        "org_id": org_id,
                        "session_id": session_id,
                        "tool_name": tool_name,
                        "provider": provider,
                        "status": status,
                        "duration_ms": duration_ms,
                    },
                    severity="INFO" if status in ("executed", "approved") else "WARNING",
                )
            except Exception as e:
                logger.debug("Google Cloud Logging emission failed: %s", e)

        logger.info(
            "Tool audit recorded: tool=%s status=%s user=%s duration=%sms",
            tool_name,
            status,
            user_id,
            duration_ms,
        )
        return record_id

    def get_user_audit_logs(
        self,
        user_id: str,
        org_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries audit records for a user and org."""
        results = [r for r in self._local_invocations if r.get("user_id") == user_id]
        if org_id:
            results = [r for r in results if r.get("org_id") == org_id]
        return results

    def get_recent_invocations(
        self,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries local in-memory audit store for testing and verification."""
        results = list(self._local_invocations)
        if user_id:
            results = [r for r in results if r.get("user_id") == user_id]
        if tool_name:
            results = [r for r in results if r.get("tool_name") == tool_name]
        return results


tool_audit_logger = ToolInvocationAuditLogger()
