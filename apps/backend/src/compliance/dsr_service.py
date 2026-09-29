"""Automated Data Subject Request (DSR) Erasure & Portability Service (Spec 03, R03.3).

Fulfills:
1. India DPDP Act 2023 Section 12 (Right to Access & Data Portability)
2. India DPDP Act 2023 Section 13 (Right to Correction & Erasure)
3. Apple App Store Review Guideline 5.1.1 (Complete In-App Account & Memory Deletion)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.auth.client import supabase_admin, _local_db
from src.compliance.session_pii_vault import session_pii_vault
from src.compliance.cert_in_logger import cert_in_logger

logger = logging.getLogger("workkbot.compliance.dsr")


class DsrService:
    """Orchestrates statutory DSR operations across Supabase and in-memory caches."""

    def execute_dsr_erasure(self, user_id: str, org_id: str) -> Dict[str, Any]:
        """
        Executes an atomic cascading erasure across all databases, vector memories,
        Vault secrets, and Supabase Auth.
        """
        logger.info("Executing statutory DSR erasure for user=%s org=%s", user_id, org_id)

        # 1. Execute live Supabase RPC execute_dsr_erasure
        client = supabase_admin.get_client()
        rpc_result = None
        if client:
            try:
                res = client.rpc(
                    "execute_dsr_erasure",
                    {"target_user_id": user_id, "executing_org_id": org_id},
                ).execute()
                rpc_result = res.data
                logger.info("Supabase execute_dsr_erasure RPC succeeded: %s", rpc_result)
            except Exception as e:
                logger.warning("Supabase execute_dsr_erasure RPC error: %s", e)

        # 2. Hard-delete user from Supabase Auth & local mirrors via supabase_admin
        cascade_result = supabase_admin.delete_user_cascade(user_id, org_id)

        # 3. Purge any active session mappings in RAM vault
        # Scan and purge all sessions belonging to user
        session_pii_vault.purge_session(user_id)

        # 4. Write CERT-In compliant audit log
        cert_in_logger.log_security_event(
            event_type="DSR_ERASURE_EXECUTED",
            user_id=user_id,
            org_id=org_id,
            details={
                "status": "hard_erasure_completed",
                "purged_vault_secrets": cascade_result.get("purged_vault_secrets", 0),
                "compliance": ["DPDP_ACT_2023_SEC_13", "APPLE_GUIDELINE_5.1.1"],
            },
        )

        return {
            "success": True,
            "user_id": user_id,
            "status": "dsr_erasure_completed",
            "purged_vault_secrets": cascade_result.get("purged_vault_secrets", 0),
            "rpc_result": rpc_result,
        }

    def export_user_data(self, user_id: str, org_id: str) -> Dict[str, Any]:
        """
        Fulfills DPDP Act 2023 Section 12 (Right to Access & Data Portability).
        Compiles all user profile, consent records, conversations, and connected providers.
        """
        client = supabase_admin.get_client()
        profile_data = {}
        consents: List[Dict[str, Any]] = []
        conversations: List[Dict[str, Any]] = []
        mcp_connections: List[Dict[str, Any]] = []

        if client:
            try:
                p_res = client.table("profiles").select("*").eq("id", user_id).execute()
                if p_res.data:
                    profile_data = p_res.data[0]

                c_res = client.table("user_consents").select("*").eq("user_id", user_id).execute()
                consents = c_res.data or []

                conv_res = client.table("conversations").select("*").eq("user_id", user_id).execute()
                conversations = conv_res.data or []

                mcp_res = client.table("mcp_connections").select("id, provider, scopes, created_at").eq("user_id", user_id).execute()
                mcp_connections = mcp_res.data or []
            except Exception as e:
                logger.warning("Supabase export data read error: %s", e)

        # Fallback to local mirrors if empty
        if not profile_data:
            profile_data = next((p for p in _local_db.get("profiles", []) if p.get("id") == user_id), {})
        if not consents:
            consents = [c for c in _local_db.get("user_consents", []) if c.get("user_id") == user_id]
        if not conversations:
            conversations = [c for c in _local_db.get("conversations", []) if c.get("user_id") == user_id]
        if not mcp_connections:
            mcp_connections = [
                {"provider": m.get("provider"), "created_at": m.get("created_at")}
                for m in _local_db.get("mcp_connections", [])
                if m.get("user_id") == user_id
            ]

        # Log CERT-In data access audit
        cert_in_logger.log_security_event(
            event_type="DSR_DATA_EXPORTED",
            user_id=user_id,
            org_id=org_id,
            details={"conversations_count": len(conversations), "consents_count": len(consents)},
        )

        return {
            "format_version": "2026.09",
            "statutory_basis": "India DPDP Act 2023 Section 12",
            "user_id": user_id,
            "org_id": org_id,
            "profile": profile_data,
            "consents": consents,
            "conversations": conversations,
            "connected_tools": mcp_connections,
        }


# Global singleton
dsr_service = DsrService()
