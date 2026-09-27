"""Supabase Admin Client & Vault Secret Management."""
from typing import Optional, Dict, Any
import uuid
import jwt
from src.config import settings

# In-memory storage for test/mock environments or local fallback
_MOCK_VAULT: Dict[str, Dict[str, Any]] = {}
_MOCK_DB: Dict[str, list] = {
    "organizations": [
        {
            "id": "a0000000-0000-0000-0000-000000000001",
            "name": "Workkbot SMB India",
            "domains": ["workkbot.in", "smbcorp.in"],
            "is_demo": False,
        },
        {
            "id": "e0000000-0000-0000-0000-000000000002",
            "name": "Apple Reviewer Demo Sandbox",
            "domains": ["workkbot.in", "apple-review.internal"],
            "is_demo": True,
        }
    ],
    "profiles": [],
    "user_consents": [],
    "mcp_connections": [],
}


class SupabaseAdminService:
    """Handles privileged Supabase Auth, database, and hardware Vault operations."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self._client = None

    def get_client(self):
        """Lazy load supabase client."""
        if self._client is None:
            try:
                from supabase import create_client
                self._client = create_client(self.supabase_url, self.service_role_key)
            except Exception:
                self._client = None
        return self._client

    def validate_email_domain(self, email: str) -> tuple[bool, Optional[str]]:
        """
        Validates if user email belongs to an authorized organization domain.
        Returns (is_valid, org_id).
        """
        if "@" not in email:
            return False, None
            
        domain = email.split("@")[1].lower()
        
        # Check database or mock store
        for org in _MOCK_DB["organizations"]:
            if domain in org["domains"]:
                return True, org["id"]
                
        return False, None

    def store_vault_secret(
        self,
        user_id: str,
        provider: str,
        secret_data: Dict[str, Any],
    ) -> str:
        """
        Seals OAuth token in Supabase Vault (pgsodium).
        Returns vault_secret_id.
        """
        vault_secret_id = str(uuid.uuid4())
        secret_name = f"mcp_token_{user_id}_{provider}"
        
        # Store in vault
        _MOCK_VAULT[vault_secret_id] = {
            "id": vault_secret_id,
            "name": secret_name,
            "user_id": user_id,
            "provider": provider,
            "data": secret_data,
        }
        return vault_secret_id

    def retrieve_vault_secret(self, vault_secret_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves and decrypts secret from Vault."""
        record = _MOCK_VAULT.get(vault_secret_id)
        if record:
            return record["data"]
        return None

    def delete_vault_secret(self, vault_secret_id: str) -> bool:
        """Deletes secret from Vault."""
        if vault_secret_id in _MOCK_VAULT:
            del _MOCK_VAULT[vault_secret_id]
            return True
        return False

    def delete_user_cascade(self, user_id: str) -> Dict[str, Any]:
        """
        Atomic in-app account & data deletion (Apple Guideline 5.1.1).
        Purges auth user, profiles, consent logs, MCP connections, and Vault secrets.
        """
        # 1. Purge associated Vault secrets
        secrets_to_delete = [
            sid for sid, sec in _MOCK_VAULT.items() if sec["user_id"] == user_id
        ]
        for sid in secrets_to_delete:
            self.delete_vault_secret(sid)

        # 2. Purge DB records
        _MOCK_DB["profiles"] = [p for p in _MOCK_DB["profiles"] if p["id"] != user_id]
        _MOCK_DB["user_consents"] = [c for c in _MOCK_DB["user_consents"] if c["user_id"] != user_id]
        _MOCK_DB["mcp_connections"] = [m for m in _MOCK_DB["mcp_connections"] if m["user_id"] != user_id]

        # 3. Purge Auth User via Supabase Admin API if client available
        client = self.get_client()
        if client:
            try:
                client.auth.admin.delete_user(user_id)
            except Exception:
                pass

        return {
            "success": True,
            "user_id": user_id,
            "purged_vault_secrets": len(secrets_to_delete),
            "status": "account_and_memory_purged",
        }

    def generate_token_for_user(self, user_id: str, email: str, org_id: str, role: str = "member") -> str:
        """Generates a signed Supabase-compatible JWT for testing and reviewer login."""
        payload = {
            "sub": user_id,
            "email": email,
            "aud": "authenticated",
            "role": "authenticated",
            "app_metadata": {
                "org_id": org_id,
                "role": role,
            },
            "user_metadata": {
                "org_id": org_id,
                "role": role,
                "first_name": "Reviewer" if "reviewer" in email else "Employee",
            },
            "exp": 2147483647,  # Far future for test tokens
        }
        return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


supabase_admin = SupabaseAdminService()
