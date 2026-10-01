"""Unit tests for Kernel Cloud Browser Manager and CDP integration (Spec 11)."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.vm.sandbox_manager import KernelBrowserManager, KernelBrowserSession


@pytest.mark.asyncio
async def test_kernel_browser_session_cdp_actions():
    """Verifies that KernelBrowserSession dispatches actions directly over CDP Playwright primitives."""
    mock_page = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.is_connected = MagicMock(return_value=True)
    mock_playwright = AsyncMock()
    mock_kernel = MagicMock()
    mock_kb = MagicMock()
    mock_kb.session_id = "test_kernel_sess_123"

    session = KernelBrowserSession(
        session_id="test_sess_1",
        kernel_client=mock_kernel,
        kernel_browser=mock_kb,
        stream_url="https://live.onkernel.com/test",
        cdp_ws_url="wss://cdp.onkernel.com/test",
    )
    session._page = mock_page
    session._browser = mock_browser
    session._playwright = mock_playwright

    # Test screenshot
    mock_page.screenshot.return_value = b"fake_png_data"
    data = await session.async_screenshot()
    assert data == b"fake_png_data"
    mock_page.screenshot.assert_awaited_once_with(type="png")

    # Test mouse click
    await session.async_left_click(150, 220)
    mock_page.mouse.click.assert_awaited_once_with(150, 220)

    # Test typing
    await session.async_write("Premium Cotton Yarn")
    mock_page.keyboard.type.assert_awaited_once_with("Premium Cotton Yarn")

    # Test keypress
    await session.async_press("Enter")
    mock_page.keyboard.press.assert_awaited_once_with("Enter")

    # Test scroll
    await session.async_scroll("down", ticks=3)
    mock_page.mouse.wheel.assert_awaited_once_with(0, 300)

    # Test goto
    await session.async_goto("https://books.zoho.in/app#/items/new")
    mock_page.goto.assert_awaited_once_with("https://books.zoho.in/app#/items/new", wait_until="domcontentloaded")

    # Test close
    await session.close()
    mock_browser.close.assert_awaited_once()
    mock_playwright.stop.assert_awaited_once()
    mock_kernel.browsers.delete_by_id.assert_called_once_with("test_kernel_sess_123")


def test_kernel_manager_provisions_kernel_session():
    """Verifies that KernelBrowserManager uses Kernel SDK when KERNEL_API_KEY is configured."""
    manager = KernelBrowserManager()

    mock_kb = MagicMock()
    mock_kb.session_id = "kb_session_abc"
    mock_kb.browser_live_view_url = "https://live.onkernel.com/abc"
    mock_kb.cdp_ws_url = "wss://cdp.onkernel.com/abc"

    mock_kernel_cls = MagicMock()
    mock_kernel_instance = MagicMock()
    mock_kernel_instance.browsers.create.return_value = mock_kb
    mock_kernel_cls.return_value = mock_kernel_instance

    with patch("src.config.settings.KERNEL_API_KEY", "test_kernel_key"):
        with patch.dict("sys.modules", {"kernel": MagicMock(Kernel=mock_kernel_cls)}):
            session, sid, stream_url = manager.get_or_create_sandbox(
                user_id="user_test_123",
                org_id="org_test_123",
            )

    assert stream_url == "https://live.onkernel.com/abc"
    assert sid.startswith("vm_user_tes")
    assert sid in manager._active_sandboxes
    assert manager._session_states[sid]["backend"] == "kernel"
    assert manager._session_states[sid]["stream_url"] == "https://live.onkernel.com/abc"
