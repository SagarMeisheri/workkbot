"""Kernel Cloud Browser & Autonomous Desktop Session Lifecycle Manager (Spec 11).

Directly provisions managed cloud Chromium instances via Kernel SDK, connects directly over
Chrome DevTools Protocol (CDP) using Playwright, and provides an interactive Live View URL
for live human login and Gemini 2.0 Flash vision-driven computer use in Workkbot's Split View.
Eliminates local container OOM crashes and resource limits by executing on Kernel's 8GB cloud infrastructure.
"""
import os
import uuid
import logging
import asyncio
import atexit
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

logger = logging.getLogger("workkbot.vm.sandbox_manager")


class KernelBrowserSession:
    """Wrapper around a Kernel cloud browser instance connected over CDP."""

    def __init__(
        self,
        session_id: str,
        kernel_client: Any,
        kernel_browser: Any,
        stream_url: str,
        cdp_ws_url: str,
    ):
        self.session_id = session_id
        self._kernel = kernel_client
        self._kb = kernel_browser
        self.stream_url = stream_url
        self.cdp_ws_url = cdp_ws_url

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    async def ensure_connected(self) -> Page:
        """Connects to Kernel browser over CDP via Playwright on demand."""
        async with self._lock:
            if self._page is None or self._browser is None or not self._browser.is_connected():
                logger.info("Connecting Playwright to Kernel browser over CDP: %s", self.cdp_ws_url[:60] + "...")
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_ws_url)
                self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
                self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            return self._page

    async def get_page(self) -> Page:
        """Returns the active Playwright Page connected over CDP."""
        return await self.ensure_connected()

    async def async_accessibility_snapshot(self) -> Optional[Dict[str, Any]]:
        """Returns the semantic accessibility tree snapshot over CDP."""
        page = await self.ensure_connected()
        try:
            return await page.accessibility.snapshot()
        except Exception as e:
            logger.warning("Accessibility snapshot error: %s", e)
            return None

    async def async_extract_interactive_elements(self) -> list:
        """
        Lightweight CDP DOM extraction. Returns interactive form controls with their
        labels, roles, names, placeholders, and current values without expensive screenshots.
        """
        page = await self.ensure_connected()
        js_code = """
        () => {
            const results = [];
            const selectors = 'input, select, textarea, button, [role="button"], [role="radio"], [role="combobox"], [role="checkbox"]';
            const nodes = Array.from(document.querySelectorAll(selectors));
            for (const el of nodes) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                const style = window.getComputedStyle(el);
                if (style.visibility === 'hidden' || style.display === 'none') continue;

                let labelText = '';
                if (el.labels && el.labels.length > 0) {
                    labelText = el.labels[0].innerText;
                } else if (el.id) {
                    const labelEl = document.querySelector(`label[for="${el.id}"]`);
                    if (labelEl) labelText = labelEl.innerText;
                }
                if (!labelText) {
                    const container = el.closest('.form-group, .row, tr, [class*="form-group"], [class*="field"]');
                    if (container) {
                        const lbl = container.querySelector('label, [class*="label"], [class*="title"]');
                        if (lbl && lbl !== el) labelText = lbl.innerText;
                    }
                }
                if (!labelText) {
                    const parentLabel = el.closest('label');
                    if (parentLabel) {
                        labelText = parentLabel.innerText;
                    } else if (el.parentElement) {
                        const prev = el.parentElement.querySelector('label');
                        if (prev) labelText = prev.innerText;
                    }
                }
                if (!labelText) {
                    labelText = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.innerText || el.name || '';
                }

                results.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    role: el.getAttribute('role') || el.type || el.tagName.toLowerCase(),
                    id: el.id || '',
                    name: el.name || '',
                    label: labelText.replace(/[\\r\\n\\t]+/g, ' ').trim().slice(0, 100),
                    placeholder: el.getAttribute('placeholder') || '',
                    value: el.value || '',
                    checked: el.checked || false,
                    disabled: el.disabled || false
                });
            }
            return results;
        }
        """
        try:
            return await page.evaluate(js_code)
        except Exception as e:
            logger.warning("DOM interactive element extraction error: %s", e)
            return []

    async def async_screenshot(self) -> bytes:
        """Captures page screenshot as PNG bytes directly over CDP."""
        page = await self.ensure_connected()
        return await page.screenshot(type="png")

    def screenshot(self) -> bytes:
        """Synchronous screenshot helper for backwards compatibility."""
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_screenshot(), loop)
            return future.result(timeout=15)
        except RuntimeError:
            return asyncio.run(self.async_screenshot())

    async def async_left_click(self, x: int, y: int):
        page = await self.ensure_connected()
        await page.mouse.click(x, y)

    def left_click(self, x: int, y: int):
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_left_click(x, y), loop)
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(self.async_left_click(x, y))

    async def async_write(self, text: str):
        page = await self.ensure_connected()
        await page.keyboard.type(text)

    def write(self, text: str):
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_write(text), loop)
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(self.async_write(text))

    async def async_press(self, key: str):
        page = await self.ensure_connected()
        await page.keyboard.press(key)

    def press(self, key: str):
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_press(key), loop)
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(self.async_press(key))

    async def async_scroll(self, direction: str = "down", ticks: int = 3):
        page = await self.ensure_connected()
        delta = 100 * ticks if direction == "down" else -100 * ticks
        await page.mouse.wheel(0, delta)

    def scroll(self, direction: str = "down", ticks: int = 3):
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_scroll(direction, ticks), loop)
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(self.async_scroll(direction, ticks))

    async def async_drag(self, start: list, end: list):
        page = await self.ensure_connected()
        await page.mouse.move(start[0], start[1])
        await page.mouse.down()
        await page.mouse.move(end[0], end[1])
        await page.mouse.up()

    def drag(self, start: list, end: list):
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_drag(start, end), loop)
            future.result(timeout=10)
        except RuntimeError:
            asyncio.run(self.async_drag(start, end))

    async def async_goto(self, url: str):
        page = await self.ensure_connected()
        await page.goto(url, wait_until="domcontentloaded")

    def goto(self, url: str):
        try:
            loop = asyncio.get_running_loop()
            future = asyncio.run_coroutine_threadsafe(self.async_goto(url), loop)
            future.result(timeout=30)
        except RuntimeError:
            asyncio.run(self.async_goto(url))

    def open(self, url: str):
        self.goto(url)

    async def close(self):
        """Closes CDP connection and deletes Kernel browser session."""
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
        except Exception as e:
            logger.warning("Error closing Playwright browser: %s", e)
        try:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
        except Exception as e:
            logger.warning("Error stopping Playwright: %s", e)
        try:
            if self._kernel and self._kb and hasattr(self._kb, "session_id"):
                self._kernel.browsers.delete_by_id(self._kb.session_id)
                logger.info("Deleted Kernel browser session %s", self._kb.session_id)
        except Exception as e:
            logger.warning("Error deleting Kernel browser session: %s", e)

    def kill(self):
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.close())
        except RuntimeError:
            asyncio.run(self.close())


class KernelBrowserManager:
    """Manages cloud browser sessions via Kernel SDK over CDP with E2B fallback."""

    def __init__(self, default_timeout_s: int = 1800):
        self.default_timeout_s = default_timeout_s
        self._active_sandboxes: Dict[str, Any] = {}
        # Session states: {session_id: {"user_id": ..., "org_id": ..., "status": ..., "pending_item": ...}}
        self._session_states: Dict[str, Dict[str, Any]] = {}

    def get_or_create_sandbox(
        self,
        user_id: str,
        org_id: str,
        session_id: Optional[str] = None,
        resolution: Tuple[int, int] = (1024, 720),
        dpi: int = 96,
    ) -> Tuple[Any, str, str]:
        """
        Provisions a Kernel Cloud Browser (or E2B Desktop Sandbox as fallback),
        navigating directly to https://books.zoho.in, and returns (session, session_id, stream_url).
        """
        sid = session_id or f"vm_{user_id[:8]}_{uuid.uuid4().hex[:8]}"

        if sid in self._active_sandboxes:
            sandbox = self._active_sandboxes[sid]
            state = self._session_states.get(sid, {})
            stream_url = state.get("stream_url", getattr(sandbox, "stream_url", ""))
            return sandbox, sid, stream_url

        from src.config import settings
        kernel_api_key = settings.KERNEL_API_KEY or os.environ.get("KERNEL_API_KEY", "")
        e2b_api_key = settings.E2B_API_KEY or os.environ.get("E2B_API_KEY", "")

        # 1. Prefer Kernel Cloud Browser if KERNEL_API_KEY is configured
        if kernel_api_key:
            logger.info("Creating Kernel Cloud Browser session for user=%s org=%s session=%s", user_id, org_id, sid)
            try:
                from kernel import Kernel
                kernel = Kernel(api_key=kernel_api_key)
                zoho_books_url = "https://books.zoho.in"
                kb = kernel.browsers.create(
                    start_url=zoho_books_url,
                    headless=False,
                    timeout_seconds=self.default_timeout_s,
                )
                stream_url = kb.browser_live_view_url or ""
                cdp_ws_url = kb.cdp_ws_url or ""
                logger.info("Kernel Cloud Browser active at: %s (CDP: %s)", stream_url, cdp_ws_url[:40] + "...")

                session_wrapper = KernelBrowserSession(
                    session_id=sid,
                    kernel_client=kernel,
                    kernel_browser=kb,
                    stream_url=stream_url,
                    cdp_ws_url=cdp_ws_url,
                )

                self._active_sandboxes[sid] = session_wrapper
                self._session_states[sid] = {
                    "session_id": sid,
                    "user_id": user_id,
                    "org_id": org_id,
                    "status": "awaiting_login",
                    "stream_url": stream_url,
                    "pending_item": None,
                    "is_logged_in": False,
                    "backend": "kernel",
                }

                return session_wrapper, sid, stream_url

            except Exception as e:
                logger.error("Failed to provision Kernel Cloud Browser: %s. Checking fallback...", e)

        # 2. Fallback to E2B Desktop Sandbox if Kernel not configured or failed
        logger.info("Provisioning E2B Desktop Sandbox fallback for user=%s org=%s session=%s", user_id, org_id, sid)
        if e2b_api_key:
            os.environ["E2B_API_KEY"] = e2b_api_key

        try:
            from e2b_desktop import Sandbox
            sandbox = Sandbox.create(
                resolution=resolution,
                dpi=dpi,
                timeout=self.default_timeout_s,
                api_key=e2b_api_key or None,
            )
        except ImportError:
            from e2b import Sandbox
            sandbox = Sandbox.create(
                template="desktop",
                timeout=self.default_timeout_s,
                api_key=e2b_api_key or None,
            )

        stream_url = ""
        if hasattr(sandbox, "stream"):
            try:
                sandbox.stream.start(require_auth=True)
                auth_key = getattr(sandbox.stream, "get_auth_key", lambda: None)()
                if auth_key and hasattr(sandbox.stream, "get_url"):
                    stream_url = sandbox.stream.get_url(auth_key=auth_key)
                elif hasattr(sandbox.stream, "get_url"):
                    stream_url = sandbox.stream.get_url()
            except Exception as e:
                logger.error("Failed to start E2B stream: %s", e)
                try:
                    stream_url = sandbox.stream.get_url()
                except Exception:
                    pass

        zoho_books_url = "https://books.zoho.in"
        chrome_cmd = (
            f"google-chrome --no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage "
            f"--disable-gpu --disable-software-rasterizer --renderer-process-limit=1 "
            f"--js-flags=\"--max-old-space-size=256\" --no-first-run --no-default-browser-check "
            f"--start-maximized --window-size=1024,720 --window-position=0,0 {zoho_books_url}"
        )
        try:
            if hasattr(sandbox, "commands"):
                sandbox.commands.run(chrome_cmd, background=True)
            elif hasattr(sandbox, "open"):
                sandbox.open(zoho_books_url)
        except Exception as e:
            logger.warning("Could not auto-launch Chrome command: %s", e)

        self._active_sandboxes[sid] = sandbox
        self._session_states[sid] = {
            "session_id": sid,
            "user_id": user_id,
            "org_id": org_id,
            "status": "awaiting_login",
            "stream_url": stream_url,
            "pending_item": None,
            "is_logged_in": False,
            "backend": "e2b",
        }

        return sandbox, sid, stream_url

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._session_states.get(session_id)

    def mark_logged_in(self, session_id: str) -> bool:
        if session_id in self._session_states:
            self._session_states[session_id]["is_logged_in"] = True
            self._session_states[session_id]["status"] = "ready"
            return True
        return False

    def set_pending_item(self, session_id: str, item_payload: Dict[str, Any]):
        if session_id in self._session_states:
            self._session_states[session_id]["pending_item"] = item_payload

    def get_pending_item(self, session_id: str) -> Optional[Dict[str, Any]]:
        state = self._session_states.get(session_id)
        return state.get("pending_item") if state else None

    def terminate_session(self, session_id: str):
        if session_id in self._active_sandboxes:
            sandbox = self._active_sandboxes.pop(session_id)
            try:
                if hasattr(sandbox, "close"):
                    res = sandbox.close()
                    if asyncio.iscoroutine(res):
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(res)
                        except RuntimeError:
                            asyncio.run(res)
                elif hasattr(sandbox, "kill"):
                    sandbox.kill()
                logger.info("Successfully terminated browser session %s", session_id)
            except Exception as e:
                logger.warning("Error killing session %s: %s", session_id, e)
        if session_id in self._session_states:
            self._session_states.pop(session_id)

    def cleanup_all(self):
        """Kills all active browser sessions to ensure no orphaned instances are left running."""
        count = len(self._active_sandboxes)
        if count == 0:
            return
        logger.info("Cleaning up %d active browser sessions...", count)
        for sid, sandbox in list(self._active_sandboxes.items()):
            try:
                if hasattr(sandbox, "close"):
                    res = sandbox.close()
                    if asyncio.iscoroutine(res):
                        try:
                            loop = asyncio.get_running_loop()
                            asyncio.create_task(res)
                        except RuntimeError:
                            asyncio.run(res)
                elif hasattr(sandbox, "kill"):
                    sandbox.kill()
                logger.info("Closed browser session %s on disconnect/shutdown", sid)
            except Exception as e:
                logger.warning("Error closing session %s during cleanup: %s", sid, e)
        self._active_sandboxes.clear()
        self._session_states.clear()


# Global singleton manager
desktop_manager = KernelBrowserManager()

# Automatically kill active sandboxes when the Python process exits or terminates
atexit.register(desktop_manager.cleanup_all)

