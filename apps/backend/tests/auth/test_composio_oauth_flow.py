"""Composio OAuth Routing & Connected Account Vault Sealing.

Verifies that connectors route through Composio Connect Links and that
the resulting connected_account_id is sealed into Supabase Vault.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin, _local_vault, _local_db


@pytest.mark.asyncio
async def test_composio_oauth_routing_and_vault():
    user_id = "user_composio_oauth_1"
    org_id = "a0000000-0000-0000-0000-000000000001"
    token = supabase_admin.generate_token_for_user(
        user_id=user_id,
        email="test_composio@workkbot.in",
        org_id=org_id,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Authorize endpoint routes via Composio Connect Link when use_composio=true
        res = await client.get(
            "/api/v1/auth/connectors/oauth/authorize?provider=google_workspace&use_composio=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "authorization_url" in data
        assert "composio.dev" in data["authorization_url"]

        # 2. Callback endpoint seals connected_account_id into Vault
        callback_res = await client.post(
            "/api/v1/auth/connectors/oauth/callback",
            json={
                "provider": "google_workspace",
                "connected_account_id": "ca_live_composio_acc_999",
                "status": "active",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert callback_res.status_code == 200
        cb_data = callback_res.json()
        assert cb_data["status"] == "active"
        assert cb_data["provider"] == "google_workspace"

        # 3. Verify sealed in Vault
        vault_record = next(
            (v for v in _local_vault.values() if v["user_id"] == user_id and v["provider"] == "google_workspace"),
            None,
        )
        assert vault_record is not None
        assert vault_record["data"]["connected_account_id"] == "ca_live_composio_acc_999"
        assert "composio_ca_live_composio_acc_999" in vault_record["data"]["access_token"]
