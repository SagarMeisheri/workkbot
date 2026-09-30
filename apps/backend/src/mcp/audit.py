"""Tool Invocation Audit Logger & Cloud Logging Correlator (Spec 04, R04.5).

Emits immutable audit records to Supabase (public.tool_invocations) and
writes structured JSON entries to Google Cloud Logging with Composio log_id correlation.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.auth.client import supabase_admin, _local_db
from src.mcp.sanitizer import mcp_sanitizer

logger = logging.getLogger("workkbot.mcp.audit")


class ToolAuditLogger:
    """Records every tool execution for statutory compliance and forensics."""

    def __init__(self):
        import os
        self.enabled = os.getenv("ENABLE_LIVE_GCP_LOGGING", "false").lower() in ("true", "1")
        self._cloud_logging_client = None

    def _get_cloud_logging_client(self):
        if not self.enabled:
            return None
        if self._cloud_logging_client is None:
            try:
                from google.cloud import logging as gcp_logging

                self._cloud_logging_client = gcp_logging.Client()
            except Exception as e:
                logger.debug("Google Cloud Logging client init fallback: %s", e)
        return self._cloud_logging_client

    def log_invocation(
        self,
        user_id: str,
        org_id: str,
        tool_name: str,
        provider: str = "composio",
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "executed",
        output: Optional[Any] = None,
        duration_ms: int = 0,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        composio_log_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> str:
        """
        Writes immutable tool invocation audit log to Supabase and Cloud Logging.
        Returns the generated record UUID.
        """
        record_id = str(uuid.uuid4())
        sanitized_params = mcp_sanitizer.sanitize_arguments(parameters or {})
        c_log_id = composio_log_id or f"cmp_{uuid.uuid4().hex[:12]}"

        record_data = {
            "id": record_id,
            "user_id": user_id,
            "org_id": org_id,
            "session_id": session_id,
            "tool_name": tool_name,
            "provider": provider,
            "parameters": sanitized_params,
            "status": status,
            "output": output,
            "error_message": error_message,
            "duration_ms": duration_ms,
            "composio_log_id": c_log_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Supabase public.tool_invocations with RLS
        client = supabase_admin.get_authenticated_client(auth_token) if auth_token else supabase_admin.get_client()
        if client:
            try:
                client.table("tool_invocations").insert({
                    "id": record_id,
                    "user_id": user_id,
                    "org_id": org_id,
                    "session_id": session_id,
                    "tool_name": tool_name,
                    "provider": provider,
                    "parameters": sanitized_params,
                    "status": status,
                    "output": output if isinstance(output, dict) else {"data": output},
                    "error_message": error_message,
                    "duration_ms": duration_ms,
                    "composio_log_id": c_log_id,
                }).execute()
            except Exception as e:
                logger.debug("Live Supabase tool_invocations insert fallback: %s", e)

        # Local fallback store
        _local_db.setdefault("tool_invocations", []).append(record_data)

        # 2. Structured JSON Entry to Google Cloud Logging
        gcp_client = self._get_cloud_logging_client()
        if gcp_client:
            try:
                gcp_logger = gcp_client.logger("tool_audit")
                gcp_logger.log_struct(
                    {
                        "audit_type": "TOOL_INVOCATION",
                        "record_id": record_id,
                        "user_id": user_id,
                        "org_id": org_id,
                        "session_id": session_id,
                        "tool_name": tool_name,
                        "provider": provider,
                        "status": status,
                        "duration_ms": duration_ms,
                        "composio_log_id": c_log_id,
                        "has_error": bool(error_message),
                    },
                    severity="WARNING" if error_message else "INFO",
                )
            except Exception as e:
                logger.debug("Cloud Logging struct write fallback: %s", e)

        logger.info(
            "Tool audit logged: id=%s tool=%s status=%s composio_log_id=%s duration=%dms",
            record_id,
            tool_name,
            status,
            c_log_id,
            duration_ms,
        )
        return record_id

    def get_user_audit_logs(
        self,
        user_id: str,
        org_id: str,
        limit: int = 50,
        auth_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries tool audit logs for user/tenant."""
        client = supabase_admin.get_authenticated_client(auth_token) if auth_token else supabase_admin.get_client()
        if client:
            try:
                res = (
                    client.table("tool_invocations")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("org_id", org_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
                if res.data:
                    return res.data
            except Exception as e:
                logger.debug("Supabase tool_invocations select fallback: %s", e)

        # Query local store
        logs = [
            l for l in _local_db.get("tool_invocations", [])
            if l.get("user_id") == user_id and l.get("org_id") == org_id
        ]
        logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return logs[:limit]


tool_audit_logger = ToolAuditLogger()
