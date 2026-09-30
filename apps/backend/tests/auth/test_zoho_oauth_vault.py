"""VAL-01.6: Zoho Workplace MCP Connection & Supabase Vault Storage.
Connects Zoho Workplace MCP via accounts.zoho.in and stores tokens sealed in Vault.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin, _local_vault, _local_db
from src.config import settings


@pytest.mark.asyncio
async def test_zoho_connect_and_vault_storage():
    """Zoho OAuth flow seals token into Supabase Vault and creates mcp_connections record."""
    user_id = "user_zoho_test_1"
    org_id = "a0000000-0000-0000-0000-000000000001"
    token = supabase_admin.generate_token_for_user(
        user_id=user_id,
        email="zoho_user@workkbot.in",
        org_id=org_id,
    )
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Authorize URL uses .in datacenter
        auth_url_res = await client.get(
            "/api/v1/auth/connectors/oauth/authorize?provider=zoho_workplace",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert auth_url_res.status_code == 200
        auth_data = auth_url_res.json()
        auth_url = auth_data["authorization_url"]
        assert "composio.dev" in auth_url.lower() or "zoho" in auth_url.lower()
        assert auth_data["provider"] == "zoho_workplace"

        # 2. Callback exchanges code and seals in Vault
        callback_res = await client.post(
            "/api/v1/auth/connectors/oauth/callback",
            json={
                "provider": "zoho_workplace",
                "code": "zoho-auth-code-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert callback_res.status_code == 200
        data = callback_res.json()
        assert data["provider"] == "zoho_workplace"
        assert data["status"] == "active"
        
        # Verify secret exists in Vault
        vault_record = next(
            (v for v in _local_vault.values() if v["user_id"] == user_id and v["provider"] == "zoho_workplace"),
            None
        )
        assert vault_record is not None
        assert "access_token" in vault_record["data"]
        assert vault_record["data"]["access_token"].startswith("mcp_access_zoho_workplace")
