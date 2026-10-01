"""OAuth 2.0 Token Lifecycle & Multi-Connector Vault Integration (Spec 04 & Spec 05).

Provides backwards-compatible GoogleOAuthService interface while delegating to
the unified ConnectorRegistry for all providers (Google Workspace, Zoho, Slack, etc.).
"""
import logging
from typing import Any, Dict, Optional
from src.mcp.registry import connector_registry

logger = logging.getLogger("workkbot.mcp.oauth_service")


class GoogleOAuthService:
    """Manages Google Workspace OAuth credentials lifecycle via connector_registry."""

    def __init__(self):
        self._adapter = connector_registry.get("google_workspace")

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges authorization code with Google OAuth endpoint."""
        return await self._adapter.exchange_code(code, redirect_uri)

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Alias for exchange_code_for_tokens matching BaseConnectorAdapter interface."""
        return await self._adapter.exchange_code(code, redirect_uri)

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes expired access token using Google refresh_token."""
        return await self._adapter.refresh_token(refresh_token)

    async def revoke_token(self, token: str) -> bool:
        """Revokes token upstream at Google (Apple Guideline 5.1.1 & DPDP Act 2023)."""
        return await self._adapter.revoke_token(token)

    async def get_valid_access_token(self, vault_secret_id: str, user_id: str) -> str:
        """Retrieves and automatically refreshes token from Supabase Vault if close to expiry."""
        return await self._adapter.ensure_valid_token(vault_secret_id, user_id)


# Backward-compatible singleton instance
google_oauth_service = GoogleOAuthService()
