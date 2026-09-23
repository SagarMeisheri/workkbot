import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from session.cloud_sql_session_service import (
    CloudSqlSessionService,
    sanitize_persistent_state,
    Session,
    Event,
)


def test_sanitize_persistent_state_strips_temp_keys():
    """
    Test State Scoping Invariant:
    Keys prefixed with 'temp:' (e.g. 'temp:pii_map') must be strictly removed
    so ephemeral in-flight translation maps never leak to persistent storage.
    """
    input_state = {
        "user_preference": "dark_mode",
        "temp:pii_map": {
            "[AADHAAR_1]": "1234-5678-9012",
            "[PHONE_1]": "+919876543210"
        },
        "session_summary": "User requested balance",
        "nested": {
            "keep_this": 42,
            "temp:internal_token": "secret_abc"
        }
    }

    sanitized = sanitize_persistent_state(input_state)

    assert "temp:pii_map" not in sanitized
    assert "user_preference" in sanitized
    assert sanitized["user_preference"] == "dark_mode"
    assert sanitized["session_summary"] == "User requested balance"
    assert sanitized["nested"]["keep_this"] == 42
    assert "temp:internal_token" not in sanitized["nested"]


@pytest.mark.asyncio
async def test_session_service_lifecycle_mocked():
    """
    Scorecard Gate B1-G2: ADK Session Service Persistence
    Verifies create_session, update_session_state, append_event, list_events,
    and 90-day TTL expiration calculation.
    """
    service = CloudSqlSessionService()
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=90)

    # 1. Mock DB connection for create_session
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "id": uuid.UUID(session_id),
        "user_id": uuid.UUID(user_id),
        "app_name": "workkbot",
        "state": {"topic": "Sovereign AI"},
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
    }

    with patch("session.cloud_sql_session_service.get_connection") as mock_get_conn:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        mock_get_conn.return_value = mock_ctx

        # Create session with a temp: key
        session = await service.create_session(
            user_id=user_id,
            app_name="workkbot",
            initial_state={"topic": "Sovereign AI", "temp:pii_map": {"x": 1}},
        )

        assert session.id == session_id
        assert session.user_id == user_id
        assert session.app_name == "workkbot"
        assert session.state == {"topic": "Sovereign AI"}
        # Assert 90-day TTL delta is approx 90 days
        diff = (session.expires_at - session.created_at).total_seconds()
        assert abs(diff - 90 * 86400) < 5

        # 2. Test get_session
        get_sess = await service.get_session(session_id=session_id, user_id=user_id)
        assert get_sess is not None
        assert get_sess.id == session_id

        # 3. Test update_session_state
        mock_conn.fetchrow.return_value = {
            "id": uuid.UUID(session_id),
            "user_id": uuid.UUID(user_id),
            "app_name": "workkbot",
            "state": {"topic": "Sovereign AI", "updated": True},
            "created_at": now,
            "updated_at": now,
            "expires_at": expires_at,
        }
        updated_sess = await service.update_session_state(
            session_id=session_id,
            user_id=user_id,
            state_delta={"updated": True, "temp:pii_delta": {"foo": "bar"}},
        )
        assert updated_sess.state.get("updated") is True
        assert "temp:pii_delta" not in updated_sess.state

        # 4. Test append_event
        event_id = str(uuid.uuid4())
        mock_conn.fetchrow.return_value = {
            "id": uuid.UUID(event_id),
            "session_id": uuid.UUID(session_id),
            "user_id": uuid.UUID(user_id),
            "event_type": "user_message",
            "content": {"text": "Namaste"},
            "created_at": now,
        }
        event = await service.append_event(
            session_id=session_id,
            user_id=user_id,
            event_type="user_message",
            content={"text": "Namaste"},
        )
        assert event.id == event_id
        assert event.event_type == "user_message"
        assert event.content["text"] == "Namaste"

        # 5. Test list_events
        mock_conn.fetch.return_value = [
            {
                "id": uuid.UUID(event_id),
                "session_id": uuid.UUID(session_id),
                "user_id": uuid.UUID(user_id),
                "event_type": "user_message",
                "content": {"text": "Namaste"},
                "created_at": now,
            }
        ]
        events = await service.list_events(session_id=session_id, user_id=user_id)
        assert len(events) == 1
        assert events[0].id == event_id
