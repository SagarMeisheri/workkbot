"""Unit & Integration Tests for Kernel Managed Auth with Zoho India (.in data residency) (Spec 11).

Tests:
1. Managed Auth Connection creation for zoho.in with allowed subdomains (accounts, books, crm).
2. Managed Auth Login initiation (POST /auth/connections/{id}/login) returning hosted_url and live_view_url.
3. 409 Conflict handling for existing connections.
4. Launching cloud Chromium with persistent Zoho profile (profile={"name": "zoho-india-profile"}).
5. ZohoIndiaBrowserRunner open_authenticated_session flow.
6. REST API router endpoints (/api/v1/vm/auth/zoho/login, status, connections).
7. Google ADK 2.0 tool declarations for zoho_india_login and zoho_browse_authenticated.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.vm.kernel_manager import BrowserSession, KernelBrowserManager
from src.vm.zoho_browser import ZohoIndiaBrowserRunner
from src.agent.tools.zoho_tools import ZohoIndiaLoginTool, ZohoBrowseAuthenticatedTool
from src.agent.agent import root_agent


@pytest.mark.asyncio
async def test_kernel_create_auth_connection_success():
    """Verifies POST /auth/connections payload for domain and profile_name."""
    manager = KernelBrowserManager(api_key="test_kernel_key", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "id": "conn_zoho_123",
        "domain": "zoho.in",
        "profile_name": "zoho-india-profile",
        "status": "pending",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        result = await manager.create_zoho_auth_connection(profile_name="zoho-india-profile")

        assert result["id"] == "conn_zoho_123"
        assert result["domain"] == "zoho.in"
        assert result["profile_name"] == "zoho-india-profile"

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "https://api.onkernel.com/auth/connections" in args[0]
        assert kwargs["json"]["domain"] == "zoho.in"
        assert kwargs["json"]["profile_name"] == "zoho-india-profile"
        assert "books.zoho.in" in kwargs["json"]["allowed_domains"]
        assert "accounts.zoho.in" in kwargs["json"]["allowed_domains"]


@pytest.mark.asyncio
async def test_kernel_create_auth_connection_409_already_exists():
    """When an auth connection already exists for domain & profile, manager returns the existing_id."""
    manager = KernelBrowserManager(api_key="test_kernel_key", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 409
    mock_resp.json.return_value = {
        "code": "already_exists",
        "existing_id": "conn_existing_999",
        "message": "Auth connection already exists for this profile and domain",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await manager.create_auth_connection(domain="zoho.in", profile_name="zoho-user-1")

        assert result["id"] == "conn_existing_999"
        assert result["status"] == "existing"


@pytest.mark.asyncio
async def test_kernel_start_auth_login():
    """Verifies POST /auth/connections/{id}/login returns hosted_url and live_view_url."""
    manager = KernelBrowserManager(api_key="test_kernel_key", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "conn_zoho_123",
        "flow_type": "LOGIN",
        "hosted_url": "https://auth.onkernel.com/login/conn_zoho_123",
        "live_view_url": "https://live.onkernel.com/conn_zoho_123",
        "flow_expires_at": "2026-10-02T12:00:00Z",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        result = await manager.start_auth_login("conn_zoho_123")

        assert result["id"] == "conn_zoho_123"
        assert result["hosted_url"] == "https://auth.onkernel.com/login/conn_zoho_123"
        assert result["live_view_url"] == "https://live.onkernel.com/conn_zoho_123"

        mock_post.assert_called_once()
        args, _ = mock_post.call_args
        assert "https://api.onkernel.com/auth/connections/conn_zoho_123/login" in args[0]


@pytest.mark.asyncio
async def test_kernel_create_browser_with_profile():
    """Verifies that create_session sends profile name when launching authenticated browser."""
    manager = KernelBrowserManager(api_key="test_kernel_key", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "session_id": "sess_zoho_auth",
        "cdp_ws_url": "wss://prod.kernel.sh/cdp/sess_zoho_auth",
        "browser_live_view_url": "https://prod.kernel.sh/live/sess_zoho_auth",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        session = await manager.create_zoho_browser(profile_name="zoho-india-profile")

        assert session.session_id == "sess_zoho_auth"
        assert session.profile_name == "zoho-india-profile"

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["profile"]["name"] == "zoho-india-profile"
        assert kwargs["json"]["stealth"] is True


@pytest.mark.asyncio
async def test_zoho_browser_runner_open_authenticated_session():
    """Tests opening an authenticated Zoho session and navigating to books.zoho.in."""
    mock_manager = MagicMock(spec=KernelBrowserManager)
    mock_manager.create_zoho_browser = AsyncMock(
        return_value=BrowserSession(
            session_id="sess_zoho_live",
            cdp_ws_url="wss://test/cdp/sess_zoho_live",
            live_view_url="https://live.test/sess_zoho_live",
            profile_name="zoho-india-profile",
        )
    )

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.title = AsyncMock(return_value="Zoho Books - Invoices")
    mock_page.url = "https://books.zoho.in/app#/invoices"
    mock_page.locator.return_value.aria_snapshot = AsyncMock(return_value="invoice table")

    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_playwright
    mock_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_cm):
        runner = ZohoIndiaBrowserRunner(manager=mock_manager)
        res = await runner.open_authenticated_session(target_url="https://books.zoho.in/app#/invoices")

        assert res["status"] == "success"
        assert res["title"] == "Zoho Books - Invoices"
        assert res["current_url"] == "https://books.zoho.in/app#/invoices"
        mock_page.goto.assert_called_once_with("https://books.zoho.in/app#/invoices", wait_until="domcontentloaded", timeout=60000)


@pytest.mark.asyncio
async def test_vm_router_zoho_managed_auth_endpoints():
    """Tests /api/v1/vm/auth/zoho/login, status, and connections endpoints."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_resp = await ac.post("/api/v1/vm/auth/zoho/login", json={"profile_name": "test-zoho-profile"})
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert data["status"] == "success"
        assert "zoho_auth" in data
        assert data["zoho_auth"]["domain"] == "zoho.in"
        assert data["zoho_auth"]["profile_name"] == "test-zoho-profile"

        status_resp = await ac.get("/api/v1/vm/auth/zoho/status?connection_id=conn_test_123")
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "success"

        conn_resp = await ac.post(
            "/api/v1/vm/auth/connections",
            json={"domain": "zoho.in", "profile_name": "custom-profile"},
        )
        assert conn_resp.status_code == 200
        assert conn_resp.json()["status"] == "success"


def test_adk_zoho_tools_registered():
    """Verifies that zoho_india_login and zoho_browse_authenticated are registered in root_agent."""
    tool_names = [t.name for t in root_agent.tools if hasattr(t, "name")]
    assert "zoho_india_login" in tool_names
    assert "zoho_browse_authenticated" in tool_names
