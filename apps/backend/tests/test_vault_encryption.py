"""Supabase Vault Token Encryption & Credential Isolation Tests (Spec 04, VAL-04.5).

Verifies that master Composio credentials and user integration tokens are stored
in Supabase Vault (pgsodium), decrypted at runtime with user_id and tenant isolation,
injected into upstream session headers, and securely purged.
"""
import pytest
import uuid
from src.mcp.vault import mcp_vault
from src.mcp.composio_service import composio_service


def test_vault_store_and_retrieve_master_key():
    """Stores master Composio key in Vault and retrieves decrypted payload (VAL-04.5)."""
    master_key = "ak_live_test_mumbai_vault_key_12345"
    secret_id = mcp_vault.store_master_composio_key(master_key)
    assert secret_id is not None

    retrieved = mcp_vault.get_master_composio_key()
    assert retrieved == master_key


def test_vault_store_and_retrieve_user_oauth_token():
    """Stores user-scoped OAuth token and retrieves decrypted payload with user isolation."""
    user_id = str(uuid.uuid4())
    provider = "google_workspace"
    token_payload = {
        "access_token": "ya29.test_access_token_12345",
        "refresh_token": "1//test_refresh_token_67890",
        "token_type": "Bearer",
    }

    secret_id = mcp_vault.store_oauth_token(
        user_id=user_id,
        provider=provider,
        token_data=token_payload,
    )
    assert secret_id is not None

    retrieved = mcp_vault.get_oauth_token(user_id=user_id, provider=provider)
    assert retrieved is not None
    assert retrieved["access_token"] == token_payload["access_token"]
    assert retrieved["refresh_token"] == token_payload["refresh_token"]


def test_inject_upstream_auth_headers():
    """Injects decrypted bearer header into upstream session requests."""
    user_id = str(uuid.uuid4())
    provider = "zoho_workplace"
    token_payload = {
        "access_token": "1000.zoho_secret_access_token",
        "token_type": "Bearer",
    }
    mcp_vault.store_oauth_token(user_id=user_id, provider=provider, token_data=token_payload)

    initial_headers = {"X-Workkbot-User-Id": user_id}
    injected_headers = mcp_vault.inject_upstream_auth_headers(
        user_id=user_id,
        provider=provider,
        headers=initial_headers,
    )

    assert "X-Upstream-Authorization" in injected_headers
    assert injected_headers["X-Upstream-Authorization"] == "Bearer 1000.zoho_secret_access_token"
    assert injected_headers["X-Workkbot-User-Id"] == user_id


def test_purge_vault_secret():
    """Purges secret on connector disconnect."""
    user_id = str(uuid.uuid4())
    provider = "notion"
    mcp_vault.store_oauth_token(user_id=user_id, provider=provider, token_data={"access_token": "secret_abc"})
    assert mcp_vault.get_oauth_token(user_id, provider) is not None

    deleted = mcp_vault.delete_oauth_token(user_id, provider)
    assert deleted is True
    assert mcp_vault.get_oauth_token(user_id, provider) is None


@pytest.mark.asyncio
async def test_composio_service_session_binding():
    """Composio service binds sessions with user_id isolation."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())

    session_record = await composio_service.get_or_create_session(user_id=user_id, org_id=org_id)
    assert session_record is not None
    assert session_record["user_id"] == user_id
    assert session_record["session_id"] is not None

    # Resuming the same session preserves session ID
    resumed = await composio_service.get_or_create_session(
        user_id=user_id,
        org_id=org_id,
        session_id=session_record["session_id"],
    )
    assert resumed["session_id"] == session_record["session_id"]
