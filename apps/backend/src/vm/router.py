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


@router.get("/session")
async def get_active_session() -> Dict[str, Any]:
    """Returns the current active cloud browser session and live view stream URL."""
    return kernel_browser_manager.get_active_session_info()


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
