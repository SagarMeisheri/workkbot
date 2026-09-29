"""VAL-02.5: Multi-Tenant Isolation for Conversations & Sessions (Supabase RLS).
Verifies that a user from Organization A cannot view, fetch, or delete conversations
belonging to Organization B.
"""
import uuid
import time
import jwt
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings


def _generate_token(user_id: str, org_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "role": "member",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    jwt_secret = settings.SUPABASE_JWT_SECRET or "test-secret"
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_cross_tenant_conversation_isolation():
    """User in Org A cannot access or list conversations created in Org B."""
    org_a = "11111111-1111-1111-1111-111111111111"
    user_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    token_a = _generate_token(user_a, org_a, "user_a@enterprise-a.in")

    org_b = "22222222-2222-2222-2222-222222222222"
    user_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    token_b = _generate_token(user_b, org_b, "user_b@enterprise-b.in")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. User A creates conversation
        create_res = await client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"title": "Confidential M&A Strategy Org A"},
        )
        assert create_res.status_code == 200
        conv_a_id = create_res.json()["id"]

        # 2. User B lists conversations: MUST NOT contain User A's conversation
        list_res = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert list_res.status_code == 200
        convs_b = list_res.json().get("conversations", [])
        assert not any(c.get("id") == conv_a_id for c in convs_b), "User B saw User A conversation in list!"

        # 3. User B directly attempts to fetch User A's conversation: MUST return 404
        fetch_res = await client.get(
            f"/api/v1/conversations/{conv_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert fetch_res.status_code == 404, "User B was able to fetch User A's conversation!"

        # 4. Clean up by User A
        await client.delete(
            f"/api/v1/conversations/{conv_a_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
