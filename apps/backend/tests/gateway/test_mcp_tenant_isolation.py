"""VAL-01.7: Multi-Tenant MCP Connection Isolation.
Verifies that a user from Org A cannot access or view Org B MCP connections or secrets.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin, _local_db, _local_vault


@pytest.mark.asyncio
async def test_cross_tenant_isolation_connectors():
    """User in Org B cannot see connections created by User in Org A."""
    user_a = "user_org_a_999"
    org_a = "a0000000-0000-0000-0000-000000000001"
    token_a = supabase_admin.generate_token_for_user(user_id=user_a, email="user_a@workkbot.in", org_id=org_a)

    user_b = "user_org_b_888"
    org_b = "b0000000-0000-0000-0000-000000000002"
    token_b = supabase_admin.generate_token_for_user(user_id=user_b, email="user_b@othercorp.in", org_id=org_b)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A connects Google Workspace
        res_a = await client.post(
            "/api/v1/auth/connectors/oauth/callback",
            json={"provider": "google_workspace", "code": "code_a"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res_a.status_code == 200
        conn_a_id = res_a.json()["id"]

        # User B queries their connectors -> must be empty (cannot see User A's connector)
        res_b_list = await client.get(
            "/api/v1/auth/connectors",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b_list.status_code == 200
        b_connections = res_b_list.json()
        assert not any(c["id"] == conn_a_id for c in b_connections)

        # User B attempts to delete User A's connector -> 404 / Forbidden
        res_b_delete = await client.delete(
            f"/api/v1/auth/connectors/{conn_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert res_b_delete.status_code == 404
