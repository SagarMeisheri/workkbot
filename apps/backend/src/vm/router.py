"""Cloud Browser Micro-VM Session Router (Spec 11).

Exposes REST endpoints to query and manage active Kernel AI browser sessions
for real-time split-view observation in Workkbot chat.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from src.vm.kernel_manager import kernel_browser_manager

logger = logging.getLogger("workkbot.vm_router")

router = APIRouter(prefix="/api/v1/vm", tags=["Cloud Browser VM"])


class CloseSessionRequest(BaseModel):
    session_id: Optional[str] = None


class ReplayStartRequest(BaseModel):
    session_id: Optional[str] = None
    record_audio: bool = False
    framerate: Optional[int] = None
    max_duration_in_seconds: Optional[int] = None


class ReplayStopRequest(BaseModel):
    session_id: Optional[str] = None
    replay_id: str


@router.get("/session")
async def get_active_session() -> Dict[str, Any]:
    """Returns the current active cloud browser session, live view stream URL, and telemetry status."""
    return kernel_browser_manager.get_active_session_info()


@router.post("/replays/start")
async def start_replay(payload: Optional[ReplayStartRequest] = None) -> Dict[str, Any]:
    """Starts video replay recording for the active or specified browser session."""
    req = payload or ReplayStartRequest()
    session_id = req.session_id or (
        kernel_browser_manager.active_session.session_id
        if kernel_browser_manager.active_session
        else None
    )
    if not session_id:
        return {"status": "error", "message": "No active session ID specified."}

    replay_info = await kernel_browser_manager.start_replay(
        session_id=session_id,
        framerate=req.framerate,
        max_duration_in_seconds=req.max_duration_in_seconds,
        record_audio=req.record_audio,
    )
    return {"status": "started", "session_id": session_id, "replay": replay_info}


@router.post("/replays/stop")
async def stop_replay(payload: ReplayStopRequest) -> Dict[str, Any]:
    """Stops video replay recording and persists the video URL."""
    session_id = payload.session_id or (
        kernel_browser_manager.active_session.session_id
        if kernel_browser_manager.active_session
        else None
    )
    if not session_id:
        return {"status": "error", "message": "No active session ID specified."}

    stop_info = await kernel_browser_manager.stop_replay(
        session_id=session_id,
        replay_id=payload.replay_id,
    )
    return {"status": "stopped", "session_id": session_id, "replay": stop_info}


@router.get("/telemetry/events")
async def get_telemetry(
    session_id: Optional[str] = None,
    categories: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetches telemetry event stream for a browser session."""
    sid = session_id or (
        kernel_browser_manager.active_session.session_id
        if kernel_browser_manager.active_session
        else None
    )
    if not sid:
        return {"status": "error", "events": [], "message": "No session ID specified."}

    cats = [c.strip() for c in categories.split(",")] if categories else None
    events = await kernel_browser_manager.get_telemetry_events(sid, categories=cats)
    return {"status": "success", "session_id": sid, "events": events, "count": len(events)}


class ZohoLoginRequest(BaseModel):
    profile_name: Optional[str] = "zoho-india-profile"


class AuthConnectionCreateRequest(BaseModel):
    domain: str
    profile_name: str
    allowed_domains: Optional[list[str]] = None


class AuthConnectionLoginRequest(BaseModel):
    connection_id: str


@router.post("/auth/zoho/login")
async def start_zoho_auth(payload: Optional[ZohoLoginRequest] = None) -> Dict[str, Any]:
    """
    Initiates Kernel Managed Auth login flow for Zoho India (.in data residency).
    Creates/attaches to the Zoho profile and returns the hosted login URL and live stream view.
    """
    req = payload or ZohoLoginRequest()
    profile_name = req.profile_name or "zoho-india-profile"
    result = await kernel_browser_manager.start_zoho_login(profile_name=profile_name)
    return {"status": "success", "zoho_auth": result}


@router.get("/auth/zoho/status")
async def get_zoho_auth_status(connection_id: str) -> Dict[str, Any]:
    """Retrieves current authentication flow status for a Zoho India connection."""
    conn = await kernel_browser_manager.get_auth_connection(connection_id)
    return {"status": "success", "connection": conn}


@router.post("/auth/connections")
async def create_auth_connection(payload: AuthConnectionCreateRequest) -> Dict[str, Any]:
    """Creates a generic Managed Auth connection attaching a domain to a browser profile."""
    conn = await kernel_browser_manager.create_auth_connection(
        domain=payload.domain,
        profile_name=payload.profile_name,
        allowed_domains=payload.allowed_domains,
    )
    return {"status": "success", "connection": conn}


@router.post("/auth/connections/login")
async def login_auth_connection(payload: AuthConnectionLoginRequest) -> Dict[str, Any]:
    """Starts a login flow for an existing Managed Auth connection."""
    res = await kernel_browser_manager.start_auth_login(connection_id=payload.connection_id)
    return {"status": "success", "login": res}


@router.post("/close")
async def close_session(payload: Optional[CloseSessionRequest] = None) -> Dict[str, Any]:
    """Explicitly closes and tears down an active cloud browser micro-VM."""
    req = payload or CloseSessionRequest()
    session_id = req.session_id or (
        kernel_browser_manager.active_session.session_id
        if kernel_browser_manager.active_session
        else None
    )
    if session_id:
        closed = await kernel_browser_manager.close_session(session_id)
        return {"status": "closed", "session_id": session_id, "success": closed}
    return {"status": "none", "message": "No active session to close."}
