"""Test VAL-04.5: Supabase Vault Token Storage & Encryption Lifecycle (Spec 04)."""
import time
import pytest
from src.auth.client import supabase_admin
from src.mcp.oauth_service import google_oauth_service


def test_supabase_vault_token_sealing_and_decryption():
    """OAuth credentials must be encrypted in Supabase Vault and retrievable via secret ID."""
    user_id = "user-vault-001"
    provider = "google_workspace"
    token_payload = {
        "access_token": "ya29.test_secure_access_token",
        "refresh_token": "1//test_secure_refresh_token",
        "expires_in": 3600,
        "token_type": "Bearer",
        "obtained_at": int(time.time()),
    }

    # 1. Store secret in Vault
    secret_id = supabase_admin.store_vault_secret(
        user_id=user_id,
        provider=provider,
        secret_data=token_payload,
    )
    assert secret_id is not None
    assert len(secret_id) > 10

    # 2. Retrieve decrypted secret
    retrieved = supabase_admin.retrieve_vault_secret(secret_id)
    assert retrieved is not None
    assert retrieved["access_token"] == token_payload["access_token"]
    assert retrieved["refresh_token"] == token_payload["refresh_token"]

    # 3. Delete secret from Vault
    deleted = supabase_admin.delete_vault_secret(secret_id)
    assert deleted is True

    # 4. Confirm secret cannot be retrieved after deletion
    after_delete = supabase_admin.retrieve_vault_secret(secret_id)
    assert after_delete is None


@pytest.mark.asyncio
async def test_vault_auto_refresh_on_expiration():
    """Expired access token stored in Vault triggers refresh flow and re-seals."""
    user_id = "user-vault-expired"
    # Create expired token (obtained 2 hours ago)
    token_payload = {
        "access_token": "ya29.old_expired_token",
        "refresh_token": "1//test_valid_refresh_token",
        "expires_in": 3600,
        "obtained_at": int(time.time()) - 7200,
    }
    secret_id = supabase_admin.store_vault_secret(
        user_id=user_id,
        provider="google_workspace",
        secret_data=token_payload,
    )

    valid_token = await google_oauth_service.get_valid_access_token(secret_id, user_id)
    assert valid_token is not None
    assert valid_token != "ya29.old_expired_token"
