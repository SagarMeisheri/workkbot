"""VAL-01.3: Reviewer Sandbox Authentication (Apple Guideline 2.1).
apple-reviewer@workkbot.in logs in cleanly and accesses isolated demo organization.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings


@pytest.mark.asyncio
async def test_reviewer_login_success():
    """Valid reviewer credentials yield valid token and isolated demo org."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/reviewer-login",
            json={
                "email": settings.REVIEWER_EMAIL,
                "password": settings.REVIEWER_PASSWORD,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["email"] == settings.REVIEWER_EMAIL
        assert data["org_id"] == settings.REVIEWER_ORG_ID
        assert data["is_demo"] is True
        assert data["role"] == "tool-admin"


@pytest.mark.asyncio
async def test_reviewer_login_invalid_password():
    """Invalid password fails with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/reviewer-login",
            json={
                "email": settings.REVIEWER_EMAIL,
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401
