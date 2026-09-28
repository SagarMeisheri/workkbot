"""VAL-02.1: Authenticated user streams response token-by-token over SSE via Cloud Run.
Verifies keep-alive ping comment, event deltas, and turn completion.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings


@pytest.mark.asyncio
async def test_chat_stream_authenticated():
    """Authenticated and consented user receives token-by-token SSE stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Reviewer
        login_res = await client.post(
            "/api/v1/auth/reviewer-login",
            json={"email": settings.REVIEWER_EMAIL, "password": settings.REVIEWER_PASSWORD},
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # 2. Ensure DPDP consent is signed
        from src.routers.consent import DPDP_DISCLOSURES_EN
        consent_res = await client.post(
            "/api/v1/consent",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "consent_version": "2026.1",
                "language": "en",
                "accepted_disclosures": DPDP_DISCLOSURES_EN,
            },
        )
        assert consent_res.status_code in (200, 201)

        # 3. Request SSE stream
        response = await client.post(
            "/api/v1/chat/stream",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Model-Tier": "gemini-3.8-flash",
            },
            json={
                "message": "Explain the DPDP Act 2023 requirements",
                "sessionId": "sess_test_val_02_1",
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Verify SSE stream contents
        raw_text = response.text
        assert ": ping" in raw_text  # Cloud Run HTTP/2 keep-alive comment
        assert "data: " in raw_text
        assert '"turnComplete": true' in raw_text
        assert "DPDP" in raw_text or "Digital Personal Data Protection" in raw_text


@pytest.mark.asyncio
async def test_chat_stream_unconsented_forbidden():
    """Unconsented user receives HTTP 403 Forbidden under DPDP Act 2023 (VAL-01.4)."""
    # Synthetic unconsented token
    import jwt
    import time
    unconsented_payload = {
        "sub": "00000000-0000-0000-0000-000000009999",
        "email": "unconsented@workkbot.in",
        "org_id": settings.REVIEWER_ORG_ID,
        "role": "member",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    jwt_secret = settings.SUPABASE_JWT_SECRET or "test-secret"
    unconsented_token = jwt.encode(unconsented_payload, jwt_secret, algorithm="HS256")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {unconsented_token}"},
            json={"message": "Hello"},
        )
        assert response.status_code == 403
        assert "DPDP statutory consent required" in response.json()["detail"]
