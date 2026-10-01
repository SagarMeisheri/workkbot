"""FastAPI Router for E2B Desktop VM Sessions & Split View Interaction (Spec 11).

Provides endpoints for launching Zoho Books sandboxes, retrieving VNC stream URLs
for the Split View, tracking authentication status, and driving the Add Item workflow.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.auth.dependencies import CurrentUser, get_current_user
from src.vm.sandbox_manager import desktop_manager
from src.vm.zoho_books_operator import ZohoBooksItemOperator

logger = logging.getLogger("workkbot.vm.router")

router = APIRouter(prefix="/api/v1/vm", tags=["autonomous_vm"])


class StartVMSessionRequest(BaseModel):
    service: Optional[str] = "zohobooks"
    pending_item: Optional[Dict[str, Any]] = None


class ConfirmLoginRequest(BaseModel):
    session_id: Optional[str] = None


class ConfirmSaveRequest(BaseModel):
    session_id: Optional[str] = None


@router.get("/session")
async def get_vm_session(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retrieves current active VM session and live stream URL for the user."""
    # Lookup any active session matching user_id
    for sid, state in desktop_manager._session_states.items():
        if state.get("user_id") == current_user.id:
            return {
                "active": True,
                "session_id": sid,
                "status": state.get("status"),
                "stream_url": state.get("stream_url"),
                "is_logged_in": state.get("is_logged_in", False),
                "pending_item": state.get("pending_item"),
            }

    return {"active": False, "status": "idle"}


@router.post("/start")
async def start_vm_session(
    payload: StartVMSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Provisions an E2B Desktop Sandbox and returns the live VNC stream URL
    for embedding in Workkbot's Split View.
    """
    sandbox, session_id, stream_url = desktop_manager.get_or_create_sandbox(
        user_id=current_user.id,
        org_id=current_user.org_id,
    )

    if payload.pending_item:
        desktop_manager.set_pending_item(session_id, payload.pending_item)

    state = desktop_manager.get_session_state(session_id) or {}

    return {
        "success": True,
        "session_id": session_id,
        "stream_url": stream_url,
        "status": state.get("status", "awaiting_login"),
        "is_logged_in": state.get("is_logged_in", False),
        "pending_item": state.get("pending_item"),
    }


@router.post("/confirm-login")
async def confirm_login(
    payload: ConfirmLoginRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Triggered when the user clicks 'I Have Logged In - Proceed' in the Split View.
    Validates login status and, if a pending item exists, executes the Computer-Use
    'New Item' form filling sequence.
    """
    session_id = payload.session_id

    # Fallback to current user's session if not explicitly passed
    if not session_id:
        for sid, state in desktop_manager._session_states.items():
            if state.get("user_id") == current_user.id:
                session_id = sid
                break

    if not session_id or session_id not in desktop_manager._session_states:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active VM session found for user",
        )

    # Mark logged in
    desktop_manager.mark_logged_in(session_id)
    sandbox = desktop_manager._active_sandboxes.get(session_id)

    pending_item = desktop_manager.get_pending_item(session_id)
    form_result = None

    if pending_item and sandbox:
        operator = ZohoBooksItemOperator(sandbox)
        await operator.navigate_to_new_item_page()
        form_result = await operator.fill_new_item_form(pending_item)

    return {
        "success": True,
        "session_id": session_id,
        "status": "awaiting_save_confirmation" if form_result else "ready",
        "pending_item": pending_item,
        "form_result": form_result,
    }


@router.post("/confirm-save")
async def confirm_save(
    payload: ConfirmSaveRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Executes the final blue [Save] button click in Zoho Books."""
    session_id = payload.session_id
    if not session_id:
        for sid, state in desktop_manager._session_states.items():
            if state.get("user_id") == current_user.id:
                session_id = sid
                break

    if not session_id or session_id not in desktop_manager._active_sandboxes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active sandbox not found",
        )

    sandbox = desktop_manager._active_sandboxes[session_id]
    operator = ZohoBooksItemOperator(sandbox)
    save_result = await operator.submit_save()

    # Clear pending item
    desktop_manager.set_pending_item(session_id, None)

    return {
        "success": True,
        "session_id": session_id,
        "save_result": save_result,
        "message": "Item successfully saved in Zoho Books",
    }


@router.post("/close")
async def close_vm_session(
    payload: Optional[ConfirmSaveRequest] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Explicitly terminates and kills the active E2B sandbox for the current user."""
    session_id = payload.session_id if payload else None
    if not session_id:
        for sid, state in desktop_manager._session_states.items():
            if state.get("user_id") == current_user.id:
                session_id = sid
                break

    if session_id:
        desktop_manager.terminate_session(session_id)
        return {"success": True, "message": f"Sandbox session {session_id} terminated"}

    return {"success": True, "message": "No active sandbox found"}

