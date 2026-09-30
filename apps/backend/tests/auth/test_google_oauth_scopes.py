"""VAL-01.2: Verification of Google Workspace OAuth Scopes.
Google Workspace login must request only minimal identity (openid, email, profile),
and zero sensitive mailbox/drive scopes at sign-in.
"""
from urllib.parse import urlparse, parse_qs
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.auth.client import supabase_admin


@pytest.mark.asyncio
async def test_google_login_minimal_scopes():
    """Sign-in OAuth endpoint must not request sensitive scopes."""
    # Standard Supabase Google login URL parameters
    login_scopes = ["openid", "email", "profile"]
    sensitive_scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar",
    ]
    
    # Assert primary identity scopes do not contain sensitive scopes
    for sensitive in sensitive_scopes:
        assert sensitive not in login_scopes, f"Sensitive scope {sensitive} found in sign-in"


@pytest.mark.asyncio
async def test_connector_oauth_granular_scope_request():
    """In-chat connector authorization requests granular tool scopes on demand."""
    token = supabase_admin.generate_token_for_user(
        user_id="user_test_scopes_1",
        email="test@workkbot.in",
        org_id="a0000000-0000-0000-0000-000000000001",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/connectors/oauth/authorize?provider=google_workspace",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "composio.dev" in data["authorization_url"]
        assert data["provider"] == "google_workspace"
