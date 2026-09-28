"""VAL-02.7: Apple App Store Review Guideline 1.2 AI Content Moderation & Reporting.
Verifies that posting an AI content report saves an incident record in public.ai_content_reports.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings


@pytest.mark.asyncio
async def test_ai_content_reporting_success():
    """Reporting AI message records incident report."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login Reviewer
        login_res = await client.post(
            "/api/v1/auth/reviewer-login",
            json={"email": settings.REVIEWER_EMAIL, "password": settings.REVIEWER_PASSWORD},
        )
        token = login_res.json()["access_token"]

        # Submit report
        response = await client.post(
            "/api/v1/chat/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message_id": "msg_erroneous_123",
                "session_id": "sess_report_test",
                "content_snapshot": "The GST rate on all goods is 0%",
                "reason": "inaccurate",
                "details": "Factually incorrect GST rate advice.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"
        assert "report_id" in data


@pytest.mark.asyncio
async def test_ai_content_reporting_invalid_reason():
    """Invalid moderation reason code is rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/reviewer-login",
            json={"email": settings.REVIEWER_EMAIL, "password": settings.REVIEWER_PASSWORD},
        )
        token = login_res.json()["access_token"]

        response = await client.post(
            "/api/v1/chat/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message_id": "msg_123",
                "content_snapshot": "test",
                "reason": "unsupported_reason",
            },
        )
        assert response.status_code == 422
