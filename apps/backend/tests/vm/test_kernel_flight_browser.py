"""Unit & Integration Tests for Kernel AI Autonomous Cloud Browser & Playwright Flight Scraper (Spec 11).

Tests:
1. KernelBrowserManager micro-VM session lifecycle (provisioning, strict error raising, teardown).
2. FlightPriceScraper dynamic DOM extraction over Playwright CDP (zero hardcoding, generic routes).
3. Google ADK 2.0 FlightSearchTool declaration and execution flow.
4. Registration of flight_tool in root_agent.
"""
from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.vm.kernel_manager import BrowserSession, KernelBrowserManager
from src.vm.flight_scraper import FlightPriceScraper
from src.agent.tools.flight_tools import FlightSearchTool, flight_tool
from src.agent.agent import root_agent


@pytest.mark.asyncio
async def test_kernel_browser_manager_no_key_raises_error():
    """Without KERNEL_API_KEY, manager strictly raises ValueError instead of simulating."""
    manager = KernelBrowserManager(api_key="", fallback_cdp_url="")
    with pytest.raises(ValueError, match="KERNEL_API_KEY is not configured"):
        await manager.create_session()


@pytest.mark.asyncio
async def test_kernel_browser_manager_provisioning_success():
    """With KERNEL_API_KEY, manager calls Kernel REST API to provision Chromium micro-VM."""
    manager = KernelBrowserManager(api_key="kernel_test_live_key_123", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "session_id": "sess_kernel_live_999",
        "cdp_ws_url": "wss://prod-jfk.kernel.sh/cdp/sess_kernel_live_999",
        "browser_live_view_url": "https://prod-jfk.kernel.sh/live/sess_kernel_live_999",
        "replay_view_url": "https://prod-jfk.kernel.sh/replay/sess_kernel_live_999",
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        session = await manager.create_session(headless=False, stealth=True, region="us-east")

        assert session.session_id == "sess_kernel_live_999"
        assert session.cdp_ws_url == "wss://prod-jfk.kernel.sh/cdp/sess_kernel_live_999"
        assert session.live_view_url == "https://prod-jfk.kernel.sh/live/sess_kernel_live_999"

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "https://api.onkernel.com/browsers" in args[0]
        assert kwargs["headers"]["Authorization"] == "Bearer kernel_test_live_key_123"
        assert kwargs["json"]["stealth"] is True
        assert kwargs["json"]["region"] == "us-east"


@pytest.mark.asyncio
async def test_kernel_browser_manager_provisioning_failure_raises_runtime_error():
    """When Kernel REST API returns an error, manager raises RuntimeError with exact details."""
    manager = KernelBrowserManager(api_key="invalid_key", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": "Unauthorized"}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Kernel browser provisioning failed \\(401\\)"):
            await manager.create_session()


@pytest.mark.asyncio
async def test_kernel_browser_manager_close_session():
    """Teardown sends DELETE /browsers/{id} to release cloud resources."""
    manager = KernelBrowserManager(api_key="kernel_test_key", base_url="https://api.onkernel.com")

    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=mock_resp) as mock_delete:
        success = await manager.close_session("sess_kernel_live_999")
        assert success is True
        mock_delete.assert_called_once_with(
            "https://api.onkernel.com/browsers/sess_kernel_live_999",
            headers={"Authorization": "Bearer kernel_test_key"},
        )


@pytest.mark.asyncio
async def test_flight_price_scraper_playwright_extraction():
    """Tests generic Playwright semantic extraction on any route (e.g. BLR to DXB)."""
    mock_manager = MagicMock(spec=KernelBrowserManager)
    mock_manager.create_session = AsyncMock(
        return_value=BrowserSession(
            session_id="real_cdp_session",
            cdp_ws_url="wss://prod-jfk.kernel.sh/cdp/real_cdp_session",
        )
    )
    mock_manager.close_session = AsyncMock()

    # Mock Playwright element items
    card_1 = MagicMock()
    card_1.inner_text = AsyncMock(return_value="IndiGo\n07:15 - 09:30\n2h 15m\nNon-stop\n₹5,200")
    img_1 = MagicMock()
    img_1.count = AsyncMock(return_value=1)
    img_1.get_attribute = AsyncMock(return_value="IndiGo Airlines")
    card_1.locator.return_value.first = img_1

    card_2 = MagicMock()
    card_2.inner_text = AsyncMock(return_value="Air India\n11:00 - 13:45\n2h 45m\nNon-stop\nINR 6,100")
    img_2 = MagicMock()
    img_2.count = AsyncMock(return_value=0)
    card_2.locator.return_value.first = img_2

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.screenshot = AsyncMock(return_value=b"fake_jpeg_bytes")
    mock_page.get_by_role.return_value.all = AsyncMock(return_value=[card_1, card_2])
    mock_page.locator.return_value.aria_snapshot = AsyncMock(return_value="flight list")

    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_playwright_instance
    mock_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_cm):
        scraper = FlightPriceScraper(manager=mock_manager)
        result = await scraper.search_flights(origin="BLR", destination="DXB", date="2026-11-01")

        assert result["status"] == "success"
        assert result["origin"] == "BLR"
        assert result["destination"] == "DXB"
        assert result["flight_count"] == 2
        assert len(result["flights"]) == 2
        assert result["max_tool_calls"] == 10

        flight1 = result["flights"][0]
        assert flight1["airline"] == "IndiGo Airlines"
        assert flight1["departure"] == "07:15"
        assert flight1["arrival"] == "09:30"
        assert flight1["price_inr"] == 5200

        flight2 = result["flights"][1]
        assert flight2["airline"] == "Air India"
        assert flight2["departure"] == "11:00"
        assert flight2["arrival"] == "13:45"
        assert flight2["price_inr"] == 6100

        assert result["screenshot_b64"] == base64.b64encode(b"fake_jpeg_bytes").decode("utf-8")
        mock_page.goto.assert_called_once()
        mock_manager.close_session.assert_called_once_with("real_cdp_session")


@pytest.mark.asyncio
async def test_agentic_loop_max_10_tool_calls_limit():
    """Verifies that the agentic browser loop enforces a strict limit of max 10 tool calls."""
    mock_manager = MagicMock(spec=KernelBrowserManager)
    mock_manager.create_session = AsyncMock(
        return_value=BrowserSession(
            session_id="sess_limit_test",
            cdp_ws_url="wss://prod-jfk.kernel.sh/cdp/sess_limit_test",
        )
    )
    mock_manager.close_session = AsyncMock()

    mock_elem = MagicMock()
    mock_elem.is_visible = AsyncMock(return_value=True)
    mock_elem.click = AsyncMock()
    mock_elem.fill = AsyncMock()

    mock_page = MagicMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.screenshot = AsyncMock(return_value=b"fake_jpeg")
    mock_page.locator.return_value.first = mock_elem
    mock_page.locator.return_value.aria_snapshot = AsyncMock(return_value="mock aria tree")
    mock_page.get_by_role.return_value.all = AsyncMock(return_value=[])
    mock_page.locator.return_value.all = AsyncMock(return_value=[])

    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)

    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_instance = MagicMock()
    mock_playwright_instance.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_playwright_instance
    mock_cm.__aexit__.return_value = None

    with patch("playwright.async_api.async_playwright", return_value=mock_cm):
        scraper = FlightPriceScraper(manager=mock_manager)
        # Always return a click action to simulate an agent that wants to keep clicking
        scraper._decide_next_action = AsyncMock(
            return_value={"action": "click", "target": "button", "reason": "keep searching"}
        )

        # Attempt to request 25 steps; scraper must strictly enforce MAX_TOOL_CALLS = 10
        result = await scraper.search_flights(origin="BOM", destination="DEL", max_tool_calls=25)

        assert result["max_tool_calls"] == 10
        assert result["tool_calls_count"] == 10
        assert scraper._decide_next_action.call_count == 10


@pytest.mark.asyncio
async def test_decide_next_action_exceeds_max_steps():
    """_decide_next_action returns 'done' when step_number > max_steps."""
    scraper = FlightPriceScraper()
    decision = await scraper._decide_next_action(
        origin="BOM",
        destination="DEL",
        date="2026-10-10",
        dom_snapshot="",
        step_number=11,
        max_steps=10,
    )
    assert decision["action"] == "done"
    assert "Reached maximum tool call limit" in decision["reason"]


@pytest.mark.asyncio
async def test_vm_router_session_endpoints():
    """Tests GET /api/v1/vm/session and POST /api/v1/vm/close."""
    from httpx import AsyncClient, ASGITransport
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/vm/session")
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data

        close_resp = await ac.post("/api/v1/vm/close")
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] in ["closed", "none", "noop"]


@pytest.mark.asyncio
async def test_adk_flight_search_tool_declaration_and_run():
    """Tests Google ADK 2.0 FlightSearchTool schema declaration and execution wrapper."""
    mock_scraper = MagicMock(spec=FlightPriceScraper)
    mock_scraper.search_flights = AsyncMock(
        return_value={
            "status": "success",
            "origin": "BOM",
            "destination": "DEL",
            "date": "2026-10-10",
            "flight_count": 1,
            "flights": [
                {
                    "airline": "IndiGo",
                    "departure": "06:00",
                    "arrival": "08:15",
                    "duration": "2h 15m",
                    "stops": "Non-stop",
                    "price_inr": 4850,
                }
            ],
            "screenshot_b64": "dummy_b64",
        }
    )

    tool = FlightSearchTool(scraper=mock_scraper)
    assert tool.name == "search_flight_prices"

    # Verify run_async parses arguments and returns formatted summary
    output = await tool.run_async(args={"origin": "BOM", "destination": "DEL", "date": "2026-10-10"})
    assert output["status"] == "success"
    assert output["flight_count"] == 1
    assert "IndiGo" in output["summary"]
    assert "₹4,850" in output["summary"]
    assert output["has_screenshot"] is True


def test_root_agent_registration():
    """Verifies that flight_tool is registered in the canonical Google ADK root_agent."""
    tool_names = [t.name for t in root_agent.tools if hasattr(t, "name")]
    assert "search_flight_prices" in tool_names


def test_clean_target_text_parsing():
    """Verifies parsing of aria snapshot targets, quotes, and CSS notation."""
    scraper = FlightPriceScraper()
    role, text = scraper._clean_target_text('combobox "Where from?"')
    assert role == "combobox"
    assert text == "Where from?"

    role, text = scraper._clean_target_text('button "Search"')
    assert role == "button"
    assert text == "Search"

    role, text = scraper._clean_target_text('"[aria-label*=\'Where from?\']"')
    assert text == "Where from?"

    role, text = scraper._clean_target_text('"Where to?"')
    assert role is None
    assert text == "Where to?"

    role, text = scraper._clean_target_text("Where from?")
    assert role is None
    assert text == "Where from?"


@pytest.mark.asyncio
async def test_resolve_locator_special_characters():
    """Verifies _resolve_locator uses get_by_role / get_by_label without CSS syntax errors on quotes & question marks."""
    scraper = FlightPriceScraper()
    mock_page = MagicMock()

    mock_loc = MagicMock()
    mock_loc.count = AsyncMock(return_value=1)
    mock_loc.first = mock_loc
    mock_page.get_by_role.return_value = mock_loc

    # Target with quotes and question mark that previously failed Playwright CSS parsing
    result = await scraper._resolve_locator(mock_page, 'combobox "Where from?"')
    assert result == mock_loc
    mock_page.get_by_role.assert_called_with("combobox", name="Where from?")


@pytest.mark.asyncio
async def test_kernel_browser_manager_close_all_on_shutdown():
    """Verifies that close_all_sessions closes all tracked micro-VMs on backend shutdown."""
    manager = KernelBrowserManager(api_key="test_key", base_url="https://api.onkernel.com")
    manager._active_sessions = {"sess_1", "sess_2"}
    manager.active_session = BrowserSession(
        session_id="sess_1",
        cdp_ws_url="wss://test/cdp/sess_1",
    )

    closed_sessions = []
    async def mock_close(sid: str):
        closed_sessions.append(sid)
        return True

    manager.close_session = mock_close
    await manager.close_all_sessions()

    assert set(closed_sessions) == {"sess_1", "sess_2"}
