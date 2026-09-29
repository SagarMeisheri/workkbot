"""Integration test for Backend In-App Account Erasure & Data Portability Router (VAL-03.7)."""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin, _local_db


@pytest.mark.asyncio
async def test_in_app_account_delete_and_export():
    """Validates /api/v1/account/delete and /api/v1/account/export endpoints."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    token = supabase_admin.generate_token_for_user(user_id=user_id, org_id=org_id, email="privacy_user@workkbot.in")

    _local_db.setdefault("profiles", []).append({
        "id": user_id,
        "org_id": org_id,
        "email": "privacy_user@workkbot.in",
        "first_name": "Privacy",
    })
    _local_db.setdefault("user_consents", []).append({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "org_id": org_id,
        "status": "active",
        "jurisdiction": "IN_DPDP_2023",
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test DSR Data Export
        export_resp = await ac.get("/api/v1/account/export", headers=headers)
        assert export_resp.status_code == 200
        export_data = export_resp.json()
        assert export_data["statutory_basis"] == "India DPDP Act 2023 Section 12"
        assert export_data["user_id"] == user_id
        assert len(export_data["consents"]) >= 1

        # 2. Test In-App Complete Deletion
        del_resp = await ac.delete("/api/v1/account/delete", headers=headers)
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["success"] is True
        assert del_data["status"] == "account_and_memory_purged"

        # 3. Verify user profile was hard-deleted
        assert not any(p["id"] == user_id for p in _local_db["profiles"])
        assert not any(c["user_id"] == user_id for c in _local_db["user_consents"])
