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
    replay_id: Optional[str] = None
    telemetry_enabled: bool = False
    profile_name: Optional[str] = None


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
        telemetry: Optional[Dict[str, Any]] = None,
        profile_name: Optional[str] = None,
    ) -> BrowserSession:
        """
        Provisions a new cloud browser micro-VM on Kernel AI.
        Configures browser telemetry (btel) by default for console & network observability.
        Supports mounting a persistent browser profile (e.g. for Zoho India Managed Auth).
        Raises an exception if KERNEL_API_KEY is not configured or if API provisioning fails.
        """
        if not self.api_key:
            if self.fallback_cdp_url:
                logger.info("No KERNEL_API_KEY provided; using BROWSER_CDP_FALLBACK_URL: %s", self.fallback_cdp_url)
                sess = BrowserSession(
                    session_id="fallback_local_cdp_session",
                    cdp_ws_url=self.fallback_cdp_url,
                    telemetry_enabled=False,
                    profile_name=profile_name,
                )
                self._active_sessions.add(sess.session_id)
                self.active_session = sess
                return sess
            raise ValueError(
                "KERNEL_API_KEY is not configured. Please set KERNEL_API_KEY in apps/backend/.env."
            )

        # Default telemetry (btel): stream console.log and network events
        telemetry_config = telemetry if telemetry is not None else {
            "browser": {
                "console": {"enabled": True},
                "network": {"enabled": True},
            },
        }

        payload: Dict[str, Any] = {
            "stealth": stealth,
            "timeout_seconds": timeout_seconds,
        }
        if telemetry_config:
            payload["telemetry"] = telemetry_config
        if profile_name:
            payload["profile"] = {"name": profile_name}
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

                logger.info(
                    "Kernel browser micro-VM provisioned successfully: session_id=%s (profile=%s, telemetry=%s)",
                    session_id,
                    profile_name,
                    bool(telemetry_config),
                )
                session = BrowserSession(
                    session_id=session_id,
                    cdp_ws_url=cdp_ws_url,
                    live_view_url=live_view_url,
                    replay_view_url=replay_view_url,
                    telemetry_enabled=bool(telemetry_config),
                    profile_name=profile_name,
                )
                self.active_session = session
                self._active_sessions.add(session_id)
                return session
            except httpx.HTTPError as e:
                logger.error("HTTP error connecting to Kernel API at %s: %s", self.base_url, e)
                raise RuntimeError(f"Kernel API connection error: {e}") from e

    async def start_replay(
        self,
        session_id: str,
        framerate: Optional[int] = None,
        max_duration_in_seconds: Optional[int] = None,
        record_audio: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Starts a video replay recording on the active browser session (POST /browsers/{id}/replays).
        Returns a dict with replay_id, replay_view_url, and start timestamp.
        """
        if not self.api_key or session_id.startswith("mock_") or session_id.startswith("fallback_"):
            logger.debug("Simulating replay start for session: %s", session_id)
            mock_id = f"replay_{session_id}"
            mock_url = f"https://api.onkernel.com/browser/replays?replay_id={mock_id}"
            if self.active_session and self.active_session.session_id == session_id:
                self.active_session.replay_id = mock_id
                self.active_session.replay_view_url = mock_url
            return {
                "replay_id": mock_id,
                "replay_view_url": mock_url,
                "started_at": "2026-10-02T00:00:00Z",
            }

        payload: Dict[str, Any] = {"record_audio": record_audio}
        if framerate is not None:
            payload["framerate"] = framerate
        if max_duration_in_seconds is not None:
            payload["max_duration_in_seconds"] = max_duration_in_seconds

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/browsers/{session_id}/replays",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    replay_id = data.get("replay_id")
                    replay_view_url = data.get("replay_view_url") or f"https://api.onkernel.com/browser/replays?replay_id={replay_id}"
                    data["replay_view_url"] = replay_view_url
                    logger.info("Kernel browser replay started: replay_id=%s (session=%s)", replay_id, session_id)
                    if self.active_session and self.active_session.session_id == session_id:
                        self.active_session.replay_id = replay_id
                        self.active_session.replay_view_url = replay_view_url
                    return data
                else:
                    logger.warning("Kernel start_replay returned %s: %s", response.status_code, response.text)
                    return None
            except Exception as e:
                logger.warning("Error starting Kernel replay for session %s: %s", session_id, e)
                return None

    async def stop_replay(
        self,
        session_id: str,
        replay_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Stops a browser session video replay recording (POST /browsers/{id}/replays/{replay_id}/stop).
        Persists the video and returns replay details.
        """
        if not self.api_key or session_id.startswith("mock_") or session_id.startswith("fallback_"):
            logger.debug("Simulating replay stop for replay %s on session %s", replay_id, session_id)
            return {
                "status": "stopped",
                "replay_id": replay_id,
                "replay_view_url": f"https://api.onkernel.com/browser/replays?replay_id={replay_id}",
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/browsers/{session_id}/replays/{replay_id}/stop",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code in (200, 204):
                    logger.info("Kernel browser replay stopped: replay_id=%s (session=%s)", replay_id, session_id)
                    default_view_url = f"https://api.onkernel.com/browser/replays?replay_id={replay_id}"
                    data = response.json() if (response.content and response.status_code != 204) else {}
                    replay_view_url = data.get("replay_view_url") or default_view_url
                    data["replay_view_url"] = replay_view_url
                    if self.active_session and self.active_session.session_id == session_id:
                        self.active_session.replay_view_url = replay_view_url
                    return data
                else:
                    logger.warning("Kernel stop_replay returned %s: %s", response.status_code, response.text)
                    return None
            except Exception as e:
                logger.warning("Error stopping Kernel replay %s for session %s: %s", replay_id, session_id, e)
                return None

    async def get_telemetry_events(
        self,
        session_id: str,
        categories: Optional[list[str]] = None,
        event_types: Optional[list[str]] = None,
    ) -> list[Dict[str, Any]]:
        """
        Reads telemetry events for an active or completed browser session (GET /browsers/{id}/telemetry/events).
        Supports filtering by category (console, network, page) and event type.
        """
        if not self.api_key or session_id.startswith("mock_") or session_id.startswith("fallback_"):
            return []

        params: Dict[str, Any] = {}
        if categories:
            params["category"] = ",".join(categories)
        if event_types:
            params["type"] = ",".join(event_types)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/browsers/{session_id}/telemetry/events",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    return data.get("events", [])
                return []
            except Exception as e:
                logger.warning("Error fetching telemetry events for session %s: %s", session_id, e)
                return []

    # --------------------------------------------------------------------------
    # Managed Auth & Profile Management (Zoho India & Universal Authenticated Browsing)
    # --------------------------------------------------------------------------

    async def create_auth_connection(
        self,
        domain: str,
        profile_name: str,
        allowed_domains: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Managed Auth Connection attaching a domain's auth state to a browser profile.
        Calls POST /auth/connections. Handles 409 Conflict gracefully by returning existing connection ID.
        """
        if not self.api_key:
            logger.info("Simulating Managed Auth Connection creation for %s (profile=%s)", domain, profile_name)
            return {
                "id": f"conn_sim_{domain.replace('.', '_')}_{profile_name}",
                "domain": domain,
                "profile_name": profile_name,
                "status": "active",
                "is_simulated": True,
            }

        payload: Dict[str, Any] = {
            "domain": domain,
            "profile_name": profile_name,
        }
        if allowed_domains:
            payload["allowed_domains"] = allowed_domains

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/connections",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code == 201:
                    data = response.json()
                    logger.info("Managed Auth connection created: id=%s (domain=%s, profile=%s)", data.get("id"), domain, profile_name)
                    return data
                elif response.status_code == 409:
                    # Connection already exists for this domain & profile
                    data = response.json()
                    existing_id = data.get("existing_id")
                    logger.info("Auth connection already exists: existing_id=%s (domain=%s, profile=%s)", existing_id, domain, profile_name)
                    return {
                        "id": existing_id,
                        "domain": domain,
                        "profile_name": profile_name,
                        "status": "existing",
                    }
                else:
                    error_msg = f"Failed to create auth connection ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            except httpx.HTTPError as e:
                logger.error("HTTP error creating auth connection at %s: %s", self.base_url, e)
                raise RuntimeError(f"Kernel Auth API connection error: {e}") from e

    async def start_auth_login(
        self,
        connection_id: str,
        browser_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Starts a login flow for the auth connection (POST /auth/connections/{id}/login).
        Returns a hosted URL for user credential entry or triggers automatic re-auth.
        """
        if not self.api_key or connection_id.startswith("conn_sim_"):
            logger.info("Simulating Managed Auth login for connection: %s", connection_id)
            return {
                "id": connection_id,
                "flow_type": "LOGIN",
                "hosted_url": f"https://auth.onkernel.com/login/{connection_id}",
                "live_view_url": f"https://live.onkernel.com/{connection_id}",
                "flow_expires_at": "2026-10-02T23:59:59Z",
                "is_simulated": True,
            }

        payload: Dict[str, Any] = {}
        if browser_config:
            payload["browser"] = browser_config

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/auth/connections/{connection_id}/login",
                    json=payload if payload else None,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info("Managed Auth login flow initiated: connection_id=%s (hosted_url=%s)", connection_id, data.get("hosted_url"))
                    return data
                elif response.status_code == 409:
                    logger.info("Login flow already in progress for connection: %s", connection_id)
                    return {
                        "id": connection_id,
                        "status": "in_progress",
                        "message": "Login flow already in progress",
                    }
                else:
                    error_msg = f"Failed to start login flow ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            except httpx.HTTPError as e:
                logger.error("HTTP error starting login flow at %s: %s", self.base_url, e)
                raise RuntimeError(f"Kernel Auth API connection error: {e}") from e

    async def get_auth_connection(self, connection_id: str) -> Dict[str, Any]:
        """Retrieves auth connection status and flow state (GET /auth/connections/{id})."""
        if not self.api_key or connection_id.startswith("conn_sim_"):
            return {
                "id": connection_id,
                "status": "authenticated",
                "is_simulated": True,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/auth/connections/{connection_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if response.status_code == 200:
                    return response.json()
                return {"id": connection_id, "status": "unknown", "error": response.text}
            except Exception as e:
                logger.warning("Error fetching auth connection %s: %s", connection_id, e)
                return {"id": connection_id, "status": "error", "error": str(e)}

    # --------------------------------------------------------------------------
    # Zoho India (.in data residency) Convenience Methods
    # --------------------------------------------------------------------------

    async def create_zoho_auth_connection(
        self,
        profile_name: str = "zoho-india-profile",
    ) -> Dict[str, Any]:
        """
        Creates a Zoho India managed auth connection bound to the specified profile.
        Configures Indian data residency domains (.in) including accounts, books, crm, and mail.
        """
        allowed_domains = [
            "zoho.in",
            "accounts.zoho.in",
            "books.zoho.in",
            "crm.zoho.in",
            "mail.zoho.in",
            "desk.zoho.in",
            "invoice.zoho.in",
        ]
        return await self.create_auth_connection(
            domain="zoho.in",
            profile_name=profile_name,
            allowed_domains=allowed_domains,
        )

    async def start_zoho_login(
        self,
        profile_name: str = "zoho-india-profile",
    ) -> Dict[str, Any]:
        """
        Starts a Zoho India login flow for the given profile.
        Returns the hosted URL for user login and the live view URL for real-time observation.
        """
        connection = await self.create_zoho_auth_connection(profile_name=profile_name)
        connection_id = connection.get("id")
        if not connection_id:
            raise RuntimeError(f"Could not establish Zoho auth connection: {connection}")

        login_result = await self.start_auth_login(connection_id=connection_id)
        return {
            "connection_id": connection_id,
            "profile_name": profile_name,
            "domain": "zoho.in",
            "hosted_url": login_result.get("hosted_url"),
            "live_view_url": login_result.get("live_view_url"),
            "flow_type": login_result.get("flow_type", "LOGIN"),
            "flow_expires_at": login_result.get("flow_expires_at"),
            "status": login_result.get("status", "pending"),
        }

    async def create_zoho_browser(
        self,
        profile_name: str = "zoho-india-profile",
        headless: bool = False,
        timeout_seconds: int = 300,
    ) -> BrowserSession:
        """
        Provisions a stealth cloud browser attached to the persistent Zoho India authenticated profile.
        Navigations to https://accounts.zoho.in or https://books.zoho.in inherit saved authentication.
        """
        logger.info("Spawning Kernel browser with Zoho India profile: %s", profile_name)
        return await self.create_session(
            headless=headless,
            stealth=True,
            timeout_seconds=timeout_seconds,
            profile_name=profile_name,
        )

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
                "replay_id": None,
                "telemetry_enabled": False,
                "task": None,
            }
        return {
            "active": True,
            "session_id": self.active_session.session_id,
            "live_view_url": self.active_session.live_view_url,
            "replay_view_url": self.active_session.replay_view_url,
            "replay_id": self.active_session.replay_id,
            "telemetry_enabled": self.active_session.telemetry_enabled,
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
