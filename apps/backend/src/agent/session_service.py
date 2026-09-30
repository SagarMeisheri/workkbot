"""Supabase DatabaseSessionService for Google ADK 2.0 (Spec 02, R02.1 & R02.3).

Subclasses canonical google.adk.sessions.BaseSessionService to persist sessions and event trees
with parent checkpoint tracking into Supabase PostgreSQL tables (public.adk_sessions, public.adk_events,
public.conversations) with local memory mirroring for resilient test execution.
"""
from __future__ import annotations

import copy
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session
from google.genai import types

from src.auth.client import _local_db, supabase_admin

logger = logging.getLogger("workkbot.session_service")


class WorkkbotEvent(Event):
    """Canonical ADK Event with dictionary-like subscript access for test & framework compatibility."""

    parent_event_id: Optional[str] = None
    branch: str = "main"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)


class WorkkbotSession(Session):
    """Canonical ADK Session with dictionary-like access for backward compatibility."""

    conversation_id: Optional[str] = None
    org_id: Optional[str] = None

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)


import contextvars
from fastapi.encoders import jsonable_encoder
import json

def safe_json_dump(obj: Any) -> Any:
    """Robust JSON-safe encoder for ADK objects (EventActions, types.Content, bytes)."""
    if obj is None:
        return {}
    try:
        encoded = jsonable_encoder(obj)
        json.dumps(encoded)
        return encoded
    except Exception:
        try:
            return json.loads(json.dumps(obj, default=str))
        except Exception:
            return str(obj)

current_session_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_session_token", default=None)
_session_tokens: Dict[str, str] = {}


class SupabaseAdkSessionService(BaseSessionService):
    """Canonical ADK 2.0 BaseSessionService backed by Supabase PostgreSQL and local mirror."""

    def __init__(self):
        super().__init__()

    def _client(self, auth_token: Optional[str] = None, session_id: Optional[str] = None):
        token = auth_token or current_session_token.get() or (session_id and _session_tokens.get(session_id))
        return supabase_admin.get_authenticated_client(token)

    async def create_session(
        self,
        *,
        app_name: str = "workkbot_core",
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
        org_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> WorkkbotSession:
        """Creates a new canonical ADK session in Supabase public.adk_sessions."""
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        if auth_token:
            current_session_token.set(auth_token)
            _session_tokens[sid] = auth_token

        client = self._client(auth_token=auth_token, session_id=sid)
        now_ts = time.time()

        # 1. Ensure linked conversation exists in Supabase public.conversations
        if conversation_id and org_id:
            conv_row = {
                "id": conversation_id,
                "user_id": user_id,
                "org_id": org_id,
                "title": "New chat",
            }
            if client:
                try:
                    conv_check = client.table("conversations").select("id").eq("id", conversation_id).execute()
                    if not conv_check.data:
                        client.table("conversations").insert(conv_row).execute()
                except Exception as e:
                    logger.error("Live Supabase ensure conversation error: %s", e)
            convs = _local_db.setdefault("conversations", [])
            if not any(c["id"] == conversation_id for c in convs):
                convs.append(conv_row)
        elif not conversation_id and org_id:
            conv_id = str(uuid.uuid4())
            conv_row = {
                "id": conv_id,
                "user_id": user_id,
                "org_id": org_id,
                "title": "New chat",
            }
            if client:
                try:
                    client.table("conversations").insert(conv_row).execute()
                except Exception as e:
                    logger.error("Live Supabase insert conversation error: %s", e)
            convs = _local_db.setdefault("conversations", [])
            if not any(c["id"] == conv_id for c in convs):
                convs.append(conv_row)
            conversation_id = conv_id

        session_row = {
            "id": sid,
            "app_name": app_name,
            "user_id": user_id,
            "org_id": org_id,
            "conversation_id": conversation_id,
            "state": state or {},
        }

        # Persist to live Supabase with Postgres TIMESTAMPTZ default now()
        if client:
            try:
                insert_payload = {k: v for k, v in session_row.items() if v is not None}
                res = client.table("adk_sessions").insert(insert_payload).execute()
                if res.data:
                    _local_db.setdefault("adk_sessions", []).append(res.data[0])
            except Exception as e:
                logger.error("Live Supabase insert adk_sessions error: %s", e)

        _local_db.setdefault("adk_sessions", []).append(session_row)

        return WorkkbotSession(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            events=[],
            last_update_time=now_ts,
            conversation_id=conversation_id,
            org_id=org_id,
        )

    async def get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        org_id: str,
        conversation_id: Optional[str] = None,
        app_name: str = "workkbot_core",
        auth_token: Optional[str] = None,
    ) -> WorkkbotSession:
        """Retrieves an existing session or creates a new one."""
        if auth_token:
            current_session_token.set(auth_token)
            _session_tokens[session_id] = auth_token

        existing = await self.get_session(session_id=session_id, user_id=user_id, org_id=org_id)
        if existing:
            return existing
        return await self.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            org_id=org_id,
            conversation_id=conversation_id,
            auth_token=auth_token,
        )

    async def get_session(
        self,
        *args,
        **kwargs,
    ) -> Optional[WorkkbotSession]:
        """Retrieves session and its events from Supabase or local mirror."""
        # Parse flexible arguments
        session_id = kwargs.get("session_id")
        user_id = kwargs.get("user_id")
        app_name = kwargs.get("app_name", "workkbot_core")
        org_id = kwargs.get("org_id")
        auth_token = kwargs.get("auth_token")

        if not session_id and len(args) >= 1:
            session_id = args[0]
        if not user_id and len(args) >= 2:
            user_id = args[1]
        if not org_id and len(args) >= 3:
            org_id = args[2]

        client = self._client(auth_token=auth_token, session_id=session_id)

        session_row = None
        events_rows: List[Dict[str, Any]] = []

        if client and session_id:
            try:
                res = client.table("adk_sessions").select("*").eq("id", session_id).execute()
                if res.data and len(res.data) > 0:
                    session_row = res.data[0]
                    ev_res = (
                        client.table("adk_events")
                        .select("*")
                        .eq("session_id", session_id)
                        .order("created_at", desc=False)
                        .execute()
                    )
                    events_rows = ev_res.data or []
            except Exception as e:
                logger.debug("Live Supabase get adk_sessions error: %s", e)

        # Fallback to local mirror
        if not session_row and session_id:
            session_row = next(
                (s for s in _local_db.get("adk_sessions", []) if s["id"] == session_id),
                None,
            )

        if not events_rows and session_id:
            events_rows = [
                e for e in _local_db.get("adk_events", []) if e.get("session_id") == session_id
            ]

        if not session_row:
            return None

        # Format events into WorkkbotEvent instances
        adk_events: List[WorkkbotEvent] = []
        for r in events_rows:
            raw_content = r.get("content", {})
            if isinstance(raw_content, dict) and "parts" in raw_content:
                parts = []
                for p in raw_content.get("parts", []):
                    if isinstance(p, dict):
                        if p.get("thought"):
                            parts.append(types.Part.from_text(text=p.get("text", "")))
                        elif "text" in p:
                            parts.append(types.Part.from_text(text=p["text"]))
                        else:
                            parts.append(types.Part(p))
                    else:
                        parts.append(p)
                content = types.Content(role=raw_content.get("role", "user"), parts=parts)
            else:
                content = raw_content

            ev = WorkkbotEvent(
                id=r["id"],
                author=r.get("author", "user"),
                branch=r.get("branch", "main"),
                parent_event_id=r.get("parent_event_id"),
                content=content,
                turn_complete=r.get("turn_complete", True),
                actions=r.get("actions"),
            )
            adk_events.append(ev)

        return WorkkbotSession(
            id=session_row["id"],
            app_name=session_row.get("app_name", app_name),
            user_id=str(session_row.get("user_id", user_id or "")),
            state=session_row.get("state") or {},
            events=adk_events,
            last_update_time=float(session_row.get("updated_at", time.time()) if isinstance(session_row.get("updated_at"), (int, float)) else time.time()),
            conversation_id=session_row.get("conversation_id"),
            org_id=session_row.get("org_id", org_id),
        )

    async def list_sessions(
        self,
        *args,
        **kwargs,
    ) -> Any:
        """Lists sessions from Supabase or local mirror."""
        client = self._client()
        app_name = kwargs.get("app_name", "workkbot_core")
        user_id = kwargs.get("user_id")
        org_id = kwargs.get("org_id")

        if not user_id and len(args) >= 1:
            user_id = args[0]
        if not org_id and len(args) >= 2:
            org_id = args[1]

        rows = []
        if client and user_id:
            try:
                query = client.table("adk_sessions").select("*").eq("user_id", user_id)
                if org_id:
                    query = query.eq("org_id", org_id)
                res = query.order("updated_at", desc=True).execute()
                if res.data:
                    rows = res.data
            except Exception as e:
                logger.debug("Live Supabase list adk_sessions error: %s", e)

        if not rows:
            rows = [
                s for s in _local_db.get("adk_sessions", [])
                if (not user_id or s.get("user_id") == user_id)
                and (not org_id or s.get("org_id") == org_id)
            ]

        # If called by ADK internal runner
        if "app_name" in kwargs:
            sessions = [
                WorkkbotSession(
                    id=r["id"],
                    app_name=r.get("app_name", app_name),
                    user_id=str(r.get("user_id", "")),
                    state=r.get("state") or {},
                    events=[],
                    last_update_time=time.time(),
                )
                for r in rows
            ]
            return ListSessionsResponse(sessions=sessions)

        return rows

    async def append_event(
        self,
        *args,
        **kwargs,
    ) -> Any:
        """Appends an event to the session and persists to Supabase adk_events."""
        # Check if called as canonical ADK: append_event(session, event)
        if len(args) >= 2 and isinstance(args[0], Session) and isinstance(args[1], Event):
            return await self._append_adk_event(args[0], args[1])

        if "session" in kwargs and "event" in kwargs:
            return await self._append_adk_event(kwargs["session"], kwargs["event"])

        # Legacy call: append_event(session_id, author, content, parent_event_id, branch, actions, event_id)
        session_id = kwargs.get("session_id") or (args[0] if len(args) >= 1 else None)
        client = self._client(session_id=session_id)
        raw_author = kwargs.get("author") or (args[1] if len(args) >= 2 else "user")
        author = "model" if raw_author not in ("user", "model", "system", "workkbot_core") else raw_author
        content = kwargs.get("content") or (args[2] if len(args) >= 3 else {})
        parent_event_id = kwargs.get("parent_event_id") or (args[3] if len(args) >= 4 else None)
        branch = kwargs.get("branch") or (args[4] if len(args) >= 5 else "main")
        actions = kwargs.get("actions") or (args[5] if len(args) >= 6 else {})
        event_id = kwargs.get("event_id") or (args[6] if len(args) >= 7 else None) or f"evt_{uuid.uuid4().hex[:16]}"

        row = {
            "id": event_id,
            "session_id": session_id,
            "author": author,
            "content": safe_json_dump(content),
            "parent_event_id": parent_event_id,
            "branch": branch,
            "actions": safe_json_dump(actions),
            "turn_complete": True,
        }

        # Local mirror with float created_at for in-memory sort
        local_row = dict(row)
        local_row["created_at"] = time.time()
        existing = next((e for e in _local_db.get("adk_events", []) if e["id"] == event_id), None)
        if not existing:
            _local_db.setdefault("adk_events", []).append(local_row)

        if client:
            try:
                res = client.table("adk_events").insert(row).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                logger.error("Live Supabase insert adk_events error: %s", e)

        return local_row

    async def _append_adk_event(self, session: Session, event: Event) -> Event:
        """Canonical ADK append_event persistence."""
        # Skip empty internal framework lifecycle/error events that have no user/model content
        if event.content is None and not (event.actions and event.actions.state_delta):
            return event

        client = self._client(session_id=session.id)
        eid = event.id or f"evt_{uuid.uuid4().hex[:16]}"
        raw_author = event.author
        author = "model" if raw_author not in ("user", "model", "system", "workkbot_core") else raw_author

        row = {
            "id": eid,
            "session_id": session.id,
            "author": author,
            "content": safe_json_dump(event.content),
            "parent_event_id": getattr(event, "parent_event_id", None),
            "branch": getattr(event, "branch", "main") or "main",
            "actions": safe_json_dump(getattr(event, "actions", {})),
            "turn_complete": getattr(event, "turn_complete", True),
        }

        # Deduplicate in local mirror
        local_row = dict(row)
        local_row["created_at"] = time.time()
        existing = next((e for e in _local_db.get("adk_events", []) if e["id"] == eid), None)
        if not existing:
            _local_db.setdefault("adk_events", []).append(local_row)

        if client:
            try:
                client.table("adk_events").insert(row).execute()
            except Exception as e:
                logger.error("Live Supabase insert adk_events error: %s", e)

        # Wrap in WorkkbotEvent
        workkbot_ev = WorkkbotEvent(
            id=eid,
            author=event.author,
            branch=getattr(event, "branch", "main") or "main",
            parent_event_id=getattr(event, "parent_event_id", None),
            content=event.content,
            turn_complete=getattr(event, "turn_complete", True),
            actions=getattr(event, "actions", None),
        )

        return await super().append_event(session, workkbot_ev)

    async def delete_session(
        self,
        *args,
        **kwargs,
    ) -> None:
        """Deletes session and cascades to events and local mirror."""
        session_id = kwargs.get("session_id")
        user_id = kwargs.get("user_id")
        auth_token = kwargs.get("auth_token")

        if not session_id and len(args) >= 1:
            session_id = args[0]
        if not user_id and len(args) >= 2:
            user_id = args[1]

        client = self._client(auth_token=auth_token, session_id=session_id)

        if client and session_id:
            try:
                client.table("adk_sessions").delete().eq("id", session_id).execute()
            except Exception as e:
                logger.error("Live Supabase delete session error: %s", e)

        _local_db["adk_sessions"] = [
            s for s in _local_db.get("adk_sessions", []) if s["id"] != session_id
        ]
        _local_db["adk_events"] = [
            e for e in _local_db.get("adk_events", []) if e.get("session_id") != session_id
        ]


session_service = SupabaseAdkSessionService()
