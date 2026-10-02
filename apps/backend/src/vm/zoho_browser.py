"""Zoho India Cloud Browser Automation Runner via Kernel Managed Auth (Spec 11).

Enables autonomous agents to access Zoho India (.in data residency) applications
(Zoho Books, Zoho Invoices, Zoho CRM, Zoho Accounts) using persistent authenticated profiles.
Uses Kernel Managed Auth to securely manage login credentials, multi-factor sessions, and session reuse.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.vm.kernel_manager import KernelBrowserManager, kernel_browser_manager

logger = logging.getLogger("workkbot.zoho_browser")


class ZohoIndiaBrowserRunner:
    """Manages authenticated Zoho India browser sessions via Kernel Managed Auth."""

    DEFAULT_PROFILE_NAME = "zoho-india-profile"
    ZOHO_INDIA_DOMAINS = [
        "zoho.in",
        "accounts.zoho.in",
        "books.zoho.in",
        "crm.zoho.in",
        "mail.zoho.in",
        "invoice.zoho.in",
    ]

    def __init__(self, manager: Optional[KernelBrowserManager] = None):
        self.manager = manager or kernel_browser_manager

    async def initiate_login(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Starts the Kernel Managed Auth login flow for Zoho India.
        Returns the hosted URL for user authentication and the live stream view URL.
        """
        prof = profile_name or self.DEFAULT_PROFILE_NAME
        logger.info("Initiating Zoho India Managed Auth login flow for profile: %s", prof)
        return await self.manager.start_zoho_login(profile_name=prof)

    async def check_login_status(self, connection_id: str) -> Dict[str, Any]:
        """Checks the status of an in-progress or completed Zoho auth connection."""
        return await self.manager.get_auth_connection(connection_id)

    async def open_authenticated_session(
        self,
        target_url: str = "https://books.zoho.in",
        profile_name: Optional[str] = None,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Spawns a stealth cloud browser instance loading the authenticated Zoho India profile.
        Navigates to the target URL where the agent is already logged in.
        """
        prof = profile_name or self.DEFAULT_PROFILE_NAME
        logger.info("Launching authenticated Zoho browser for %s (profile=%s)", target_url, prof)

        session = await self.manager.create_zoho_browser(
            profile_name=prof,
            headless=False,
            timeout_seconds=timeout_seconds,
        )
        self.manager.active_task = f"Zoho India Automation: {target_url}"

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {
                "status": "error",
                "session_id": session.session_id,
                "live_view_url": session.live_view_url,
                "error": "Playwright is required for browser automation.",
            }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(session.cdp_ws_url)
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                # Navigate to the target Zoho URL with authenticated profile state
                logger.info("Navigating to authenticated Zoho URL: %s", target_url)
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Capture accessibility DOM tree
                try:
                    dom_snapshot = await page.locator("body").aria_snapshot()
                except Exception:
                    dom_snapshot = await page.locator("body").inner_text()

                title = await page.title()
                current_url = page.url
                await browser.close()

                return {
                    "status": "success",
                    "session_id": session.session_id,
                    "live_view_url": session.live_view_url,
                    "profile_name": prof,
                    "title": title,
                    "current_url": current_url,
                    "dom_snapshot": dom_snapshot[:8000] if dom_snapshot else None,
                }
        except Exception as e:
            logger.error("Error in authenticated Zoho session: %s", e)
            return {
                "status": "error",
                "session_id": session.session_id,
                "live_view_url": session.live_view_url,
                "profile_name": prof,
                "error": str(e),
            }


zoho_browser_runner = ZohoIndiaBrowserRunner()
