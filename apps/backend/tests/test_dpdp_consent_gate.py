"""VAL-01.4: DPDP Act 2023 Statutory Consent Gate (Apple Guideline 5.1.2i).
First-time user cannot call /chat without signing DPDP statutory consent.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin, _local_db
from src.routers.consent import DPDP_DISCLOSURES_EN


@pytest.mark.asyncio
async def test_chat_blocked_without_dpdp_consent():
    """Calling chat without consent returns 403 Forbidden."""
    user_id = "user_consent_test_1"
    token = supabase_admin.generate_token_for_user(
        user_id=user_id,
        email="consent_test@workkbot.in",
        org_id="a0000000-0000-0000-0000-000000000001",
    )
    # Ensure no consent in DB
    _local_db["user_consents"] = [c for c in _local_db["user_consents"] if c["user_id"] != user_id]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check consent status is False
        status_res = await client.get("/api/v1/consent/status", headers={"Authorization": f"Bearer {token}"})
        assert status_res.status_code == 200
        assert status_res.json()["has_consented"] is False

        # Attempt to chat -> Must be blocked
        chat_res = await client.post(
            "/api/v1/chat",
            json={"message": "Hello Workkbot"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert chat_res.status_code == 403
        assert "consent required" in chat_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_signing_consent_unlocks_chat():
    """Signing consent saves record in public.user_consents and unlocks chat."""
    user_id = "user_consent_test_2"
    token = supabase_admin.generate_token_for_user(
        user_id=user_id,
        email="consent_user2@workkbot.in",
        org_id="a0000000-0000-0000-0000-000000000001",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Sign consent
        record_res = await client.post(
            "/api/v1/consent",
            json={
                "consent_version": "2026.1",
                "language": "en",
                "accepted_disclosures": DPDP_DISCLOSURES_EN,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert record_res.status_code == 200
        assert record_res.json()["status"] == "active"

        # Check status is now True
        status_res = await client.get("/api/v1/consent/status", headers={"Authorization": f"Bearer {token}"})
        assert status_res.status_code == 200
        assert status_res.json()["has_consented"] is True

        # Chat call now succeeds
        chat_res = await client.post(
            "/api/v1/chat",
            json={"message": "Hello Workkbot"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert chat_res.status_code == 200
        assert "reply" in chat_res.json()
