"""Kernel AI (kernel.sh) Cloud Browser Infrastructure Manager (Spec 11).

Provisions isolated Chromium micro-VMs in <150ms over the Kernel REST API,
exposes Chrome DevTools Protocol (CDP) WebSocket URLs for Playwright automation,
and manages session lifecycle with automatic cleanup.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import httpx
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger("workkbot.kernel_manager")


class BrowserSession(BaseModel):
    """Represents an active cloud browser instance provisioned via Kernel AI."""
    session_id: str
    cdp_ws_url: str
    live_view_url: Optional[str] = None
    replay_view_url: Optional[str] = None


class KernelBrowserManager:
    """Manages cloud browser micro-VM lifecycle via Kernel AI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        fallback_cdp_url: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.KERNEL_API_KEY
        self.base_url = (base_url if base_url is not None else settings.KERNEL_BASE_URL).rstrip("/")
        self.fallback_cdp_url = fallback_cdp_url if fallback_cdp_url is not None else settings.BROWSER_CDP_FALLBACK_URL
        self.active_session: Optional[BrowserSession] = None
        self.active_task: Optional[str] = None
        self._active_sessions: set[str] = set()

    async def create_session(
        self,
        headless: bool = False,
        stealth: bool = True,
        region: Optional[str] = None,
        timeout_seconds: int = 120,
    ) -> BrowserSession:
        """
        Provisions a new cloud browser micro-VM on Kernel AI.
        Raises an exception if KERNEL_API_KEY is not configured or if API provisioning fails.
        """
        if not self.api_key:
            if self.fallback_cdp_url:
                logger.info("No KERNEL_API_KEY provided; using BROWSER_CDP_FALLBACK_URL: %s", self.fallback_cdp_url)
                sess = BrowserSession(
                    session_id="fallback_local_cdp_session",
                    cdp_ws_url=self.fallback_cdp_url,
                )
                self._active_sessions.add(sess.session_id)
                self.active_session = sess
                return sess
            raise ValueError(
                "KERNEL_API_KEY is not configured. Please set KERNEL_API_KEY in apps/backend/.env."
            )

        payload: Dict[str, Any] = {
            "stealth": stealth,
            "timeout_seconds": timeout_seconds,
        }
        if headless:
            payload["headless"] = True
        if region:
            payload["region"] = region

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/browsers",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code >= 400:
                    error_msg = f"Kernel browser provisioning failed ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                data = response.json()
                session_id = data.get("session_id")
                cdp_ws_url = data.get("cdp_ws_url")
                live_view_url = data.get("browser_live_view_url") or data.get("live_view_url")
                replay_view_url = data.get("replay_view_url")

                if not session_id or not cdp_ws_url:
                    raise RuntimeError(f"Kernel API returned incomplete session data: {data}")

                logger.info("Kernel browser micro-VM provisioned successfully: session_id=%s", session_id)
                session = BrowserSession(
                    session_id=session_id,
                    cdp_ws_url=cdp_ws_url,
                    live_view_url=live_view_url,
                    replay_view_url=replay_view_url,
                )
                self.active_session = session
                self._active_sessions.add(session_id)
                return session
            except httpx.HTTPError as e:
                logger.error("HTTP error connecting to Kernel API at %s: %s", self.base_url, e)
                raise RuntimeError(f"Kernel API connection error: {e}") from e

    async def close_session(self, session_id: str) -> bool:
        """Terminates the cloud browser micro-VM on Kernel AI."""
        self._active_sessions.discard(session_id)
        if self.active_session and self.active_session.session_id == session_id:
            self.active_session = None
            self.active_task = None

        if not session_id or session_id.startswith("mock_") or session_id.startswith("fallback_"):
            logger.debug("Closing simulated/fallback browser session: %s", session_id)
            return True

        if not self.api_key:
            return True

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/browsers/{session_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                logger.info("Kernel browser session %s terminated with status %s", session_id, response.status_code)
                return response.status_code in (200, 204, 404)
            except Exception as e:
                logger.warning("Error terminating Kernel browser session %s: %s", session_id, e)
                return False

    async def close_all_sessions(self) -> None:
        """Terminates all active Kernel browser micro-VMs when backend shuts down."""
        sessions_to_close = list(self._active_sessions)
        if self.active_session and self.active_session.session_id not in sessions_to_close:
            sessions_to_close.append(self.active_session.session_id)

        if not sessions_to_close:
            logger.debug("No active Kernel browser sessions to close.")
            return

        logger.info(
            "Closing %d active Kernel browser session(s) on backend shutdown: %s",
            len(sessions_to_close),
            sessions_to_close,
        )
        for sid in sessions_to_close:
            try:
                await self.close_session(sid)
            except Exception as e:
                logger.warning("Error closing Kernel session %s during shutdown: %s", sid, e)

    def get_active_session_info(self) -> Dict[str, Any]:
        """Returns the active browser session info for front-end split view."""
        if not self.active_session:
            return {
                "active": False,
                "session_id": None,
                "live_view_url": None,
                "replay_view_url": None,
                "task": None,
            }
        return {
            "active": True,
            "session_id": self.active_session.session_id,
            "live_view_url": self.active_session.live_view_url,
            "replay_view_url": self.active_session.replay_view_url,
            "task": self.active_task or "Cloud Browser Automation",
        }


kernel_browser_manager = KernelBrowserManager()

import atexit

def _sync_cleanup_on_exit():
    """Emergency synchronous cleanup if backend process terminates abruptly."""
    if kernel_browser_manager.api_key and kernel_browser_manager._active_sessions:
        for sid in list(kernel_browser_manager._active_sessions):
            if sid.startswith("mock_") or sid.startswith("fallback_"):
                continue
            try:
                with httpx.Client(timeout=3.0) as client:
                    client.delete(
                        f"{kernel_browser_manager.base_url}/browsers/{sid}",
                        headers={"Authorization": f"Bearer {kernel_browser_manager.api_key}"},
                    )
            except Exception:
                pass

atexit.register(_sync_cleanup_on_exit)
