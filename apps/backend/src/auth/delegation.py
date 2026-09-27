"""Agentgateway Token Delegation Service.
Retrieves encrypted tokens from Supabase Vault and injects authenticated session headers.
"""
from typing import Dict, Any, Optional
import httpx
from src.auth.client import supabase_admin, _MOCK_DB
from src.config import settings


class TokenDelegationService:
    """Manages secure token retrieval and delegation to Agentgateway sidecar."""

    async def get_delegated_headers(
        self,
        user_id: str,
        org_id: str,
        provider: str,
        user_jwt: str,
    ) -> Dict[str, str]:
        """
        Retrieves user's OAuth token from Supabase Vault and constructs
        Agentgateway authenticated session headers.
        """
        # Find active connection
        connection = None
        for conn in _MOCK_DB["mcp_connections"]:
            if conn["user_id"] == user_id and conn["provider"] == provider and conn["status"] == "active":
                connection = conn
                break
                
        if not connection:
            raise ValueError(f"No active connection found for provider '{provider}' and user '{user_id}'")
            
        # Verify tenant isolation (org_id match)
        if connection["org_id"] != org_id:
            raise PermissionError("Cross-tenant connection access prohibited by RLS policy")
            
        vault_secret_id = connection.get("vault_secret_id")
        if not vault_secret_id:
            raise ValueError("Connection lacks associated Supabase Vault secret")
            
        # Decrypt secret from Vault
        secret_data = supabase_admin.retrieve_vault_secret(vault_secret_id)
        if not secret_data or "access_token" not in secret_data:
            raise ValueError("Failed to retrieve decrypted access token from Supabase Vault")
            
        access_token = secret_data["access_token"]
        
        # Build headers for Agentgateway
        return {
            "Authorization": f"Bearer {user_jwt}",
            "X-Upstream-Authorization": f"Bearer {access_token}",
            "X-Workkbot-User-Id": user_id,
            "X-Workkbot-Org-Id": org_id,
            "X-Workkbot-Provider": provider,
        }

    def verify_cel_policy(
        self,
        claims: Dict[str, Any],
        resource: Dict[str, Any],
    ) -> bool:
        """
        Simulates Agentgateway 1.5.x CEL policy engine:
        request.auth.claims.sub == resource.owner && request.auth.claims.org_id == resource.org_id
        """
        sub = claims.get("sub")
        org_id = claims.get("org_id")
        
        owner = resource.get("owner")
        resource_org_id = resource.get("org_id")
        
        # Strict equality check
        if sub != owner:
            return False
        if org_id != resource_org_id:
            return False
        return True


token_delegator = TokenDelegationService()
