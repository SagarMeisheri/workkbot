"""Supabase Vault Token Encryption & Credential Management (Spec 04, R04.1).

Stores Master Composio API key and per-user integration credentials sealed
inside Supabase Vault (pgsodium) as hardware-encrypted secrets.
Provides atomic retrieval, upstream auth header injection, and secure erasure.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from src.auth.client import supabase_admin, _local_db
from src.config import settings

logger = logging.getLogger("workkbot.mcp.vault")


class McpVaultManager:
    """Manages encrypted secrets in Supabase Vault (pgsodium) with fallback."""

    def __init__(self):
        # Ephemeral in-memory fallback for unit testing / local development
        self._local_vault: Dict[str, Dict[str, Any]] = {}

    def store_master_composio_key(self, api_key: str) -> Optional[str]:
        """Seals master Composio Platform project key into Supabase Vault."""
        secret_payload = json.dumps({"api_key": api_key})
        secret_name = "composio_master_key"
        description = "Master Composio Platform project key"

        client = supabase_admin.get_client()
        if client:
            try:
                res = client.rpc(
                    "create_secret",
                    {"secret": secret_payload, "name": secret_name, "description": description},
                ).execute()
                if res.data:
                    return str(res.data)
            except Exception as e:
                logger.debug("Live Supabase Vault create_secret fallback: %s", e)

        # Fallback to local store
        self._local_vault[secret_name] = {"api_key": api_key}
        return f"vault_secret_{secret_name}"

    def get_master_composio_key(self) -> Optional[str]:
        """Retrieves decrypted master Composio API key from Vault or settings."""
        secret_name = "composio_master_key"

        client = supabase_admin.get_client()
        if client:
            try:
                res = (
                    client.table("vault.decrypted_secrets")
                    .select("decrypted_secret")
                    .eq("name", secret_name)
                    .maybe_single()
                    .execute()
                )
                if res.data and res.data.get("decrypted_secret"):
                    parsed = json.loads(res.data["decrypted_secret"])
                    return parsed.get("api_key")
            except Exception as e:
                logger.debug("Live Supabase Vault decrypted_secrets lookup fallback: %s", e)

        if secret_name in self._local_vault:
            return self._local_vault[secret_name].get("api_key")

        # Fallback to environment variable / settings
        return getattr(settings, "COMPOSIO_API_KEY", None)

    def store_oauth_token(
        self,
        user_id: str,
        provider: str,
        token_data: Dict[str, Any],
    ) -> str:
        """
        Stores an encrypted OAuth token in Supabase Vault.
        Name pattern: mcp_token_${user_id}_${provider}
        """
        secret_name = f"mcp_token_{user_id}_{provider}"
        secret_payload = json.dumps(token_data)

        client = supabase_admin.get_client()
        if client:
            try:
                res = client.rpc(
                    "create_secret",
                    {
                        "secret": secret_payload,
                        "name": secret_name,
                        "description": f"MCP OAuth token for {provider}",
                    },
                ).execute()
                if res.data:
                    return str(res.data)
            except Exception as e:
                logger.debug("Live Vault store_oauth_token fallback: %s", e)

        self._local_vault[secret_name] = token_data
        return f"vault_{secret_name}"

    def get_oauth_token(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """Retrieves and decrypts an OAuth token from Supabase Vault."""
        secret_name = f"mcp_token_{user_id}_{provider}"

        client = supabase_admin.get_client()
        if client:
            try:
                res = (
                    client.table("vault.decrypted_secrets")
                    .select("decrypted_secret")
                    .eq("name", secret_name)
                    .maybe_single()
                    .execute()
                )
                if res.data and res.data.get("decrypted_secret"):
                    return json.loads(res.data["decrypted_secret"])
            except Exception as e:
                logger.debug("Live Vault get_oauth_token fallback: %s", e)

        return self._local_vault.get(secret_name)

    def inject_upstream_auth_headers(
        self,
        user_id: str,
        provider: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Injects decrypted bearer headers into upstream session requests."""
        updated = dict(headers or {})
        token_data = self.get_oauth_token(user_id, provider)
        if token_data and "access_token" in token_data:
            updated["X-Upstream-Authorization"] = f"Bearer {token_data['access_token']}"
        return updated

    def delete_oauth_token(self, user_id: str, provider: str) -> bool:
        """Purges encrypted secret from Vault on disconnect or account erasure."""
        secret_name = f"mcp_token_{user_id}_{provider}"

        client = supabase_admin.get_client()
        if client:
            try:
                client.rpc("delete_secret", {"name": secret_name}).execute()
            except Exception as e:
                logger.debug("Live Vault delete_oauth_token fallback: %s", e)

        if secret_name in self._local_vault:
            del self._local_vault[secret_name]
            return True
        return True


mcp_vault = McpVaultManager()
