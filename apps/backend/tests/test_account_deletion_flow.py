"""VAL-01.9: In-App Account & Data Deletion Flow (Apple Guideline 5.1.1 Compliance).
Verifies /api/v1/account/delete cascades deletion across user, vault secrets, and database records.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin, _local_db, _local_vault


@pytest.mark.asyncio
async def test_in_app_account_deletion_cascades_completely():
    """Triggering in-app account deletion purges all data with zero residual traces."""
    user_id = "user_delete_target_1"
    org_id = "a0000000-0000-0000-0000-000000000001"
    token = supabase_admin.generate_token_for_user(user_id=user_id, email="delete_me@workkbot.in", org_id=org_id)

    # 1. Setup user records: profile, consent, mcp connection, vault secret
    _local_db["profiles"].append({
        "id": user_id,
        "org_id": org_id,
        "email": "delete_me@workkbot.in",
        "role": "member",
    })
    _local_db["user_consents"].append({
        "id": "consent_del_1",
        "user_id": user_id,
        "org_id": org_id,
        "consent_version": "2026.1",
        "status": "active",
    })
    secret_id = supabase_admin.store_vault_secret(
        user_id=user_id,
        provider="google_workspace",
        secret_data={"access_token": "token_to_purge"},
    )
    _local_db["mcp_connections"].append({
        "id": "conn_del_1",
        "user_id": user_id,
        "org_id": org_id,
        "provider": "google_workspace",
        "vault_secret_id": secret_id,
        "status": "active",
    })

    # Assert preconditions exist
    assert any(p["id"] == user_id for p in _local_db["profiles"])
    assert any(c["user_id"] == user_id for c in _local_db["user_consents"])
    assert any(m["user_id"] == user_id for m in _local_db["mcp_connections"])
    assert secret_id in _local_vault

    # 2. Call DELETE /api/v1/account/delete
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/api/v1/account/delete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "account_and_memory_purged"
        assert data["purged_vault_secrets"] >= 1

    # 3. Assert complete purge in DB and Vault (Zero Residual Records)
    assert not any(p["id"] == user_id for p in _local_db["profiles"])
    assert not any(c["user_id"] == user_id for c in _local_db["user_consents"])
    assert not any(m["user_id"] == user_id for m in _local_db["mcp_connections"])
    assert secret_id not in _local_vault
