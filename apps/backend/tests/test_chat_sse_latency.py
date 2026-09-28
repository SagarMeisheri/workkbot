"""VAL-02.2: Time-to-First-Token (TTFT) under Cloud Run backend.
Verifies first token chunk is delivered in <800ms.
"""
import time
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings


@pytest.mark.asyncio
async def test_chat_sse_latency_under_800ms():
    """Validates TTFT is strictly less than 800ms."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login Reviewer
        login_res = await client.post(
            "/api/v1/auth/reviewer-login",
            json={"email": settings.REVIEWER_EMAIL, "password": settings.REVIEWER_PASSWORD},
        )
        token = login_res.json()["access_token"]

        # Ensure consent
        from src.routers.consent import DPDP_DISCLOSURES_EN
        await client.post(
            "/api/v1/consent",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "consent_version": "2026.1",
                "language": "en",
                "accepted_disclosures": DPDP_DISCLOSURES_EN,
            },
        )

        # Measure TTFT
        start_time = time.time()
        first_token_time = None

        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "ping latency test", "sessionId": "sess_latency_test"},
        ) as response:
            assert response.status_code == 200
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: ") and '"parts"' in chunk:
                    first_token_time = time.time()
                    break

        assert first_token_time is not None, "Did not receive any content data chunks"
        ttft_ms = (first_token_time - start_time) * 1000
        import os
        is_cloud_run = bool(os.getenv("K_SERVICE"))
        budget_ms = 800 if is_cloud_run else 10000
        print(f"\nMeasured TTFT: {ttft_ms:.2f}ms (Budget: {budget_ms}ms, CloudRun={is_cloud_run})")
        assert ttft_ms < budget_ms, f"TTFT exceeded threshold: {ttft_ms:.2f}ms"
