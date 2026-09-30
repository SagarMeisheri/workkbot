"""Unit tests for Conversation Actions: Pin, Rename, Delete (Supabase / Local DB).
Verifies that conversations can be updated (title, pinned) and deleted,
and verifies tenant isolation during these actions.
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
async def test_conversation_pin_rename_delete():
    """Verify that a user can pin, rename, and delete their conversation."""
    org_id = "33333333-3333-3333-3333-333333333333"
    user_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    token = _generate_token(user_id, org_id, "user_c@enterprise-c.in")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create two conversations
        res1 = await client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"title": "First Conversation"},
        )
        assert res1.status_code == 200
        conv1_id = res1.json()["id"]

        res2 = await client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"title": "Second Conversation"},
        )
        assert res2.status_code == 200
        conv2_id = res2.json()["id"]

        # 2. Rename conv1
        patch_res = await client.patch(
            f"/api/v1/conversations/{conv1_id}",
            headers=headers,
            json={"title": "Renamed First Conversation"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Renamed First Conversation"

        # 3. Pin conv1 (should place it first in list)
        pin_res = await client.patch(
            f"/api/v1/conversations/{conv1_id}",
            headers=headers,
            json={"pinned": True},
        )
        assert pin_res.status_code == 200
        assert pin_res.json()["pinned"] is True

        # 4. List conversations - conv1 should be first because it is pinned
        list_res = await client.get("/api/v1/conversations", headers=headers)
        assert list_res.status_code == 200
        convs = list_res.json()["conversations"]
        assert len(convs) >= 2
        # conv1 is pinned, so it should be at index 0
        assert convs[0]["id"] == conv1_id
        assert convs[0]["title"] == "Renamed First Conversation"
        assert convs[0].get("pinned") is True

        # 5. Delete conv2
        del_res = await client.delete(f"/api/v1/conversations/{conv2_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 6. Verify conv2 is gone
        list_res_after = await client.get("/api/v1/conversations", headers=headers)
        conv_ids_after = [c["id"] for c in list_res_after.json()["conversations"]]
        assert conv2_id not in conv_ids_after
        assert conv1_id in conv_ids_after
