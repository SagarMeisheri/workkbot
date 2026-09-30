"""Supabase Vault (pgsodium) Token Manager for MCP Connectors (Spec 04, R04.1).

Stores, decrypts, and injects third-party OAuth and API tokens into Agentgateway upstream session headers.
Guarantees zero plaintext tokens committed to storage, tables, or log files.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.auth.client import supabase_admin, _local_vault, _local_db

logger = logging.getLogger("workkbot.mcp.vault")


class McpVaultManager:
    """Manages sealing, decrypting, and injecting MCP credentials using Supabase Vault."""

    def __init__(self):
        self.admin = supabase_admin

    def store_token(
        self,
        user_id: str,
        provider: str,
        token_payload: Optional[Dict[str, Any]] = None,
        token_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Encrypts third-party token pair into Supabase Vault as mcp_token_${user_id}_${provider}.
        Returns vault_secret_id.
        """
        payload = token_data if token_data is not None else (token_payload or {})
        vault_secret_id = self.admin.store_vault_secret(
            user_id=user_id,
            provider=provider,
            secret_data=payload,
        )
        logger.info(
            "Sealed MCP token in Supabase Vault provider=%s user=%s secret_id=%s",
            provider,
            user_id,
            vault_secret_id,
        )
        return vault_secret_id

    def get_token(
        self,
        user_id: str,
        provider: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves decrypted token for the specific user and provider.
        Searches active connection record or vault name pattern.
        """
        secret_name = f"mcp_token_{user_id}_{provider}"

        # 1. Look up connection record in public.mcp_connections
        client = self.admin.get_client()
        vault_secret_id = None
        if client:
            try:
                res = (
                    client.table("mcp_connections")
                    .select("vault_secret_id")
                    .eq("user_id", user_id)
                    .eq("provider", provider)
                    .eq("status", "active")
                    .execute()
                )
                if res.data and res.data[0].get("vault_secret_id"):
                    vault_secret_id = res.data[0]["vault_secret_id"]
            except Exception as e:
                logger.debug("Database lookup failed for connection: %s", e)

        # Fallback to local store
        if not vault_secret_id:
            for conn in _local_db.get("mcp_connections", []):
                if (
                    conn.get("user_id") == user_id
                    and conn.get("provider") == provider
                    and conn.get("status") == "active"
                ):
                    vault_secret_id = conn.get("vault_secret_id")
                    break

        if vault_secret_id:
            token = self.admin.retrieve_vault_secret(vault_secret_id)
            if token:
                return token

        # Fallback: search local vault by secret_name
        for v in _local_vault.values():
            if v.get("name") == secret_name or (
                v.get("user_id") == user_id and v.get("provider") == provider
            ):
                return v.get("data")

        return None

    def delete_token(self, vault_secret_id: str) -> bool:
        """Purges token from Supabase Vault (Apple App Store Guideline 5.1.1)."""
        success = self.admin.delete_vault_secret(vault_secret_id)
        logger.info("Purged MCP token secret_id=%s success=%s", vault_secret_id, success)
        return success

    def delete_oauth_token(self, user_id: str, provider: str) -> bool:
        """Purges token for user and provider from Supabase Vault."""
        secret_name = f"mcp_token_{user_id}_{provider}"
        # Purge from local vault if present
        to_delete = [k for k, v in _local_vault.items() if v.get("name") == secret_name or (v.get("user_id") == user_id and v.get("provider") == provider)]
        for k in to_delete:
            _local_vault.pop(k, None)

        client = self.admin.get_client()
        if client:
            try:
                res = client.table("mcp_connections").select("vault_secret_id").eq("user_id", user_id).eq("provider", provider).execute()
                if res.data:
                    for r in res.data:
                        vid = r.get("vault_secret_id")
                        if vid:
                            self.delete_token(vid)
            except Exception:
                pass
        return True

    store_oauth_token = store_token
    get_oauth_token = get_token

    def inject_upstream_auth_headers(
        self,
        user_id: str,
        provider: str,
        existing_headers: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Injects decrypted OAuth bearer token or API key into headers for Agentgateway upstream proxying.
        """
        merged_headers = dict(headers if headers is not None else (existing_headers or {}))
        token_data = self.get_token(user_id, provider)
        if not token_data:
            return merged_headers

        access_token = token_data.get("access_token") or token_data.get("api_key")
        if access_token:
            merged_headers["X-Upstream-Authorization"] = f"Bearer {access_token}"
            merged_headers["X-MCP-Provider"] = provider
            merged_headers["X-MCP-User-Id"] = user_id

        return merged_headers


mcp_vault = McpVaultManager()
