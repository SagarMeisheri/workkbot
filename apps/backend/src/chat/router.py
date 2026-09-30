"""FastAPI Chat Router: SSE Streaming, Conversation Management & Apple 1.2 AI Reporting (Spec 02)."""
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.auth.dependencies import CurrentUser, get_current_user
from src.auth.client import supabase_admin, _local_db
from src.agent.runner import runner_singleton
from src.agent.session_service import session_service
from src.chat.sse import format_adk_sse_stream

logger = logging.getLogger("workkbot.chat_router")

router = APIRouter(prefix="", tags=["chat"])


class ChatStreamRequest(BaseModel):
    message: Optional[str] = ""
    parts: Optional[List[Dict[str, Any]]] = None
    checkpointId: Optional[str] = None
    sessionId: Optional[str] = None
    conversationId: Optional[str] = None
    model: Optional[str] = None
    stateDelta: Optional[Dict[str, Any]] = None
    type: Optional[str] = "message"
    toolConfirmation: Optional[Dict[str, Any]] = None
    invocationId: Optional[str] = None


class ContentReportRequest(BaseModel):
    message_id: str
    content_snapshot: str
    reason: str = Field(..., pattern="^(inaccurate|offensive|pii_leak|copyright|other)$")
    details: Optional[str] = None
    session_id: Optional[str] = None


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New chat"
    id: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None


def _verify_dpdp_consent(current_user: CurrentUser) -> None:
    """Verifies statutory DPDP consent is active (VAL-01.4)."""
    client = supabase_admin.get_authenticated_client(current_user.token)
    has_consented = False
    if client:
        try:
            res = client.table("user_consents").select("id").eq("user_id", current_user.id).eq("status", "active").execute()
            if res.data:
                has_consented = True
        except Exception as e:
            logger.warning("Supabase consent check error: %s", e)

    if not has_consented:
        # Check in local fallback
        consent = next(
            (c for c in _local_db.get("user_consents", [])
             if c.get("user_id") == current_user.id and c.get("status") == "active"),
            None
        )
        if not consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="DPDP statutory consent required before initiating conversation",
            )


@router.post("/api/v1/chat/stream")
async def chat_stream_endpoint(
    payload: ChatStreamRequest,
    current_user: CurrentUser = Depends(get_current_user),
    x_model_tier: Optional[str] = Header(None, alias="X-Model-Tier"),
):
    """
    Main SSE Streaming Endpoint for @assistant-ui/react-google-adk (R02.2).
    Streams tokens over Cloud Run HTTP/2 with initial : ping keep-alive.
    Supports checkpointId branching (R02.3).
    """
    _verify_dpdp_consent(current_user)

    # Determine message content
    raw_message = payload.message or ""
    if not raw_message and payload.parts:
        text_parts = [p.get("text", "") for p in payload.parts if p.get("text")]
        raw_message = " ".join(text_parts)

    session_id = payload.sessionId or f"sess_{uuid.uuid4().hex[:12]}"
    model_choice = payload.model or x_model_tier

    event_generator = runner_singleton.run_turn_stream(
        user_id=current_user.id,
        org_id=current_user.org_id,
        session_id=session_id,
        message=raw_message,
        checkpoint_id=payload.checkpointId,
        model_preference=model_choice,
        state_delta=payload.stateDelta,
        conversation_id=payload.conversationId,
        auth_token=current_user.token,
        tool_confirmation=payload.toolConfirmation,
        invocation_id=payload.invocationId,
    )

    return StreamingResponse(
        format_adk_sse_stream(event_generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/v1/conversations")
async def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lists conversations for the authenticated user and org (R02.4)."""
    local_convs = [c for c in _local_db.get("conversations", []) if c["user_id"] == current_user.id and c["org_id"] == current_user.org_id]
    client = supabase_admin.get_authenticated_client(current_user.token)
    if client:
        try:
            res = client.table("conversations").select("*").eq("user_id", current_user.id).eq("org_id", current_user.org_id).order("updated_at", desc=True).execute()
            if res.data:
                existing_ids = {c["id"] for c in res.data}
                merged = list(res.data) + [c for c in local_convs if c["id"] not in existing_ids]
                merged.sort(key=lambda c: (bool(c.get("pinned")), c.get("updated_at") or ""), reverse=True)
                return {"conversations": merged}
        except Exception as e:
            logger.debug("Live Supabase list conversations fallback: %s", e)

    local_convs.sort(key=lambda c: (bool(c.get("pinned")), c.get("updated_at") or ""), reverse=True)
    return {"conversations": local_convs}


@router.post("/api/v1/conversations")
async def create_conversation(
    payload: CreateConversationRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Initializes a new conversation thread."""
    client = supabase_admin.get_authenticated_client(current_user.token)
    conv_id = payload.id or str(uuid.uuid4())
    row = {
        "id": conv_id,
        "user_id": current_user.id,
        "org_id": current_user.org_id,
        "title": payload.title or "New chat",
    }
    
    # Deduplicate in _local_db
    convs = _local_db.setdefault("conversations", [])
    existing_idx = next((i for i, c in enumerate(convs) if c["id"] == conv_id), None)
    if existing_idx is not None:
        convs[existing_idx] = row
    else:
        convs.append(row)

    if client:
        try:
            res = client.table("conversations").insert(row).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error("Live Supabase insert conversation fallback: %s", e)

    return row


@router.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Fetches a conversation thread and its events with RLS tenant isolation."""
    client = supabase_admin.get_authenticated_client(current_user.token)
    if client:
        try:
            conv_res = client.table("conversations").select("*").eq("id", conversation_id).eq("user_id", current_user.id).execute()
            if conv_res.data:
                conversation = conv_res.data[0]
                sessions_res = client.table("adk_sessions").select("id").eq("conversation_id", conversation_id).execute()
                events = []
                if sessions_res.data:
                    sess_id = sessions_res.data[0]["id"]
                    ev_res = client.table("adk_events").select("*").eq("session_id", sess_id).order("created_at", desc=False).execute()
                    events = ev_res.data or []
                conversation["events"] = events
                return conversation
        except Exception as e:
            logger.debug("Live Supabase get conversation fallback: %s", e)

    # Check local store with strict tenant isolation check
    conv = next((c for c in _local_db.get("conversations", []) if c["id"] == conversation_id and c["user_id"] == current_user.id and c["org_id"] == current_user.org_id), None)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv_copy = dict(conv)
    matched_session_ids = {
        s["id"] for s in _local_db.get("adk_sessions", [])
        if s.get("conversation_id") == conversation_id or s.get("id") == conversation_id
    }
    matched_session_ids.add(conversation_id)
    conv_copy["events"] = [
        e for e in _local_db.get("adk_events", [])
        if e.get("session_id") in matched_session_ids
    ]
    return conv_copy


@router.patch("/api/v1/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Updates conversation title or pinned status."""
    updates: Dict[str, Any] = {}
    if payload.title is not None:
        updates["title"] = payload.title
    if payload.pinned is not None:
        updates["pinned"] = payload.pinned
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    client = supabase_admin.get_authenticated_client(current_user.token)
    if client:
        try:
            client.table("conversations").update(updates).eq("id", conversation_id).eq("user_id", current_user.id).execute()
        except Exception as e:
            logger.error("Live Supabase update conversation fallback: %s", e)

    conv = next((c for c in _local_db.get("conversations", []) if c["id"] == conversation_id and c["user_id"] == current_user.id), None)
    if conv:
        conv.update(updates)
        return {"status": "updated", "id": conversation_id, **conv}

    return {"status": "updated", "id": conversation_id, **updates}


@router.delete("/api/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Deletes a conversation and cascades through its events and sessions."""
    client = supabase_admin.get_authenticated_client(current_user.token)
    if client:
        try:
            client.table("conversations").delete().eq("id", conversation_id).eq("user_id", current_user.id).execute()
        except Exception as e:
            logger.debug("Live Supabase delete conversation fallback: %s", e)

    _local_db["conversations"] = [c for c in _local_db.get("conversations", []) if c["id"] != conversation_id]
    return {"status": "deleted", "id": conversation_id}


@router.post("/api/v1/conversations/{conversation_id}/branch")
async def branch_conversation(
    conversation_id: str,
    payload: ChatStreamRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Explicitly branches a conversation from a given parent checkpoint ID."""
    if not payload.checkpointId:
        raise HTTPException(status_code=400, detail="checkpointId is required to branch conversation")
    if not payload.conversationId:
        payload.conversationId = conversation_id
    return await chat_stream_endpoint(payload=payload, current_user=current_user)


@router.post("/api/v1/chat/report")
async def report_ai_content(
    payload: ContentReportRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Apple App Store Review Guideline 1.2 Compliance.
    Records an immediate user incident report regarding AI-generated output.
    """
    report_id = str(uuid.uuid4())
    row = {
        "id": report_id,
        "user_id": current_user.id,
        "org_id": current_user.org_id,
        "session_id": payload.session_id,
        "message_id": payload.message_id,
        "content_snapshot": payload.content_snapshot,
        "reason": payload.reason,
        "details": payload.details,
        "status": "pending",
    }
    _local_db.setdefault("ai_content_reports", []).append(row)

    client = supabase_admin.get_authenticated_client(current_user.token)
    if client:
        try:
            res = client.table("ai_content_reports").insert(row).execute()
            if res.data:
                logger.info("Apple Guideline 1.2 Report recorded: %s (reason: %s)", report_id, payload.reason)
        except Exception as e:
            logger.error("Live Supabase insert report fallback: %s", e)

    return {"status": "recorded", "report_id": report_id}


# -------------------------------------------------------------------------
# ADK-Native REST Endpoints for @assistant-ui/react-google-adk createAdkSessionAdapter
# Matches: /apps/{appName}/users/{userId}/sessions...
# -------------------------------------------------------------------------

@router.get("/apps/{app_name}/users/{user_id}/sessions")
async def adk_adapter_list_sessions(
    app_name: str,
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lists sessions for createAdkSessionAdapter."""
    sessions = await session_service.list_sessions(user_id=current_user.id, org_id=current_user.org_id)
    return [{"id": s["id"]} for s in sessions]


@router.post("/apps/{app_name}/users/{user_id}/sessions")
async def adk_adapter_create_session(
    app_name: str,
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Creates a new session for createAdkSessionAdapter."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    sess = await session_service.get_or_create_session(
        session_id=session_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        app_name=app_name,
    )
    return {"id": sess["id"]}


@router.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def adk_adapter_get_session(
    app_name: str,
    user_id: str,
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Loads session and its events for createAdkSessionAdapter."""
    sess = await session_service.get_session(
        session_id=session_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        auth_token=current_user.token,
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    events = sess.get("events", [])
    formatted_events = []
    for ev in events:
        author_val = "user" if ev.get("author") == "user" else "model"
        formatted_events.append({
            "id": ev["id"],
            "author": author_val,
            "branch": ev.get("branch", "main"),
            "content": ev.get("content", {}),
            "turnComplete": ev.get("turn_complete", True),
        })

    return {
        "id": sess["id"],
        "events": formatted_events,
    }


@router.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def adk_adapter_delete_session(
    app_name: str,
    user_id: str,
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Deletes session for createAdkSessionAdapter."""
    await session_service.delete_session(
        session_id=session_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        auth_token=current_user.token,
    )
    return {"status": "deleted", "id": session_id}
