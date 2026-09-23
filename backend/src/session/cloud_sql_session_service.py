import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from db import get_connection

logger = logging.getLogger("workkbot.session")


class Session(BaseModel):
    id: str
    user_id: str
    app_name: str
    state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class Event(BaseModel):
    id: str
    session_id: str
    user_id: str
    event_type: str
    content: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


def sanitize_persistent_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    State Scoping Invariant:
    Keys prefixed with 'temp:' (e.g. 'temp:pii_map') are ephemeral and strictly
    filtered out to guarantee in-flight data never touches persistent storage.
    """
    clean_state = {}
    for k, v in state.items():
        if k.startswith("temp:"):
            logger.debug("Stripping ephemeral state key from persistent storage: %s", k)
            continue
        if isinstance(v, dict):
            clean_state[k] = sanitize_persistent_state(v)
        else:
            clean_state[k] = v
    return clean_state


class CloudSqlSessionService:
    """
    Google Agent Development Kit (ADK) 2.6+ compatible Session Service
    backed by Sovereign Cloud SQL PostgreSQL with Row-Level Security.
    """

    async def create_session(
        self,
        user_id: str,
        app_name: str = "workkbot",
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> Session:
        sanitized_state = sanitize_persistent_state(initial_state or {})
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=90)

        query = """
            INSERT INTO public.adk_sessions (user_id, app_name, state, created_at, updated_at, expires_at)
            VALUES ($1::uuid, $2, $3::jsonb, $4, $4, $5)
            RETURNING id, user_id, app_name, state, created_at, updated_at, expires_at;
        """

        async with get_connection(user_id=user_id) as conn:
            row = await conn.fetchrow(
                query,
                user_id,
                app_name,
                json.dumps(sanitized_state),
                now,
                expires_at,
            )

        return Session(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            app_name=row["app_name"],
            state=json.loads(row["state"]) if isinstance(row["state"], str) else row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )

    async def get_session(self, session_id: str, user_id: str) -> Optional[Session]:
        query = """
            SELECT id, user_id, app_name, state, created_at, updated_at, expires_at
            FROM public.adk_sessions
            WHERE id = $1::uuid
              AND user_id = $2::uuid
              AND expires_at > timezone('utc', now());
        """

        async with get_connection(user_id=user_id) as conn:
            row = await conn.fetchrow(query, session_id, user_id)

        if not row:
            return None

        return Session(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            app_name=row["app_name"],
            state=json.loads(row["state"]) if isinstance(row["state"], str) else row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )

    async def update_session_state(
        self, session_id: str, user_id: str, state_delta: Dict[str, Any]
    ) -> Session:
        # Crucial: Filter out temp: prefixed keys before persisting
        sanitized_delta = sanitize_persistent_state(state_delta)
        now = datetime.now(timezone.utc)

        # Merge JSONB state using PostgreSQL concatenation operator ||
        query = """
            UPDATE public.adk_sessions
            SET state = state || $3::jsonb,
                updated_at = $4
            WHERE id = $1::uuid
              AND user_id = $2::uuid
              AND expires_at > timezone('utc', now())
            RETURNING id, user_id, app_name, state, created_at, updated_at, expires_at;
        """

        async with get_connection(user_id=user_id) as conn:
            row = await conn.fetchrow(
                query,
                session_id,
                user_id,
                json.dumps(sanitized_delta),
                now,
            )

        if not row:
            raise ValueError(f"Active session '{session_id}' not found for user '{user_id}'")

        return Session(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            app_name=row["app_name"],
            state=json.loads(row["state"]) if isinstance(row["state"], str) else row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )

    async def append_event(
        self, session_id: str, user_id: str, event_type: str, content: Dict[str, Any]
    ) -> Event:
        now = datetime.now(timezone.utc)
        query = """
            INSERT INTO public.adk_events (session_id, user_id, event_type, content, created_at)
            VALUES ($1::uuid, $2::uuid, $3, $4::jsonb, $5)
            RETURNING id, session_id, user_id, event_type, content, created_at;
        """

        async with get_connection(user_id=user_id) as conn:
            row = await conn.fetchrow(
                query,
                session_id,
                user_id,
                event_type,
                json.dumps(content),
                now,
            )

        return Event(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            user_id=str(row["user_id"]),
            event_type=row["event_type"],
            content=json.loads(row["content"]) if isinstance(row["content"], str) else row["content"],
            created_at=row["created_at"],
        )

    async def list_events(self, session_id: str, user_id: str) -> List[Event]:
        query = """
            SELECT id, session_id, user_id, event_type, content, created_at
            FROM public.adk_events
            WHERE session_id = $1::uuid
              AND user_id = $2::uuid
            ORDER BY created_at ASC;
        """

        async with get_connection(user_id=user_id) as conn:
            rows = await conn.fetch(query, session_id, user_id)

        return [
            Event(
                id=str(r["id"]),
                session_id=str(r["session_id"]),
                user_id=str(r["user_id"]),
                event_type=r["event_type"],
                content=json.loads(r["content"]) if isinstance(r["content"], str) else r["content"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
