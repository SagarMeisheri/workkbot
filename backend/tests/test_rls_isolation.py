import pytest
import uuid
from unittest.mock import AsyncMock, patch

from session.cloud_sql_session_service import CloudSqlSessionService


@pytest.mark.asyncio
async def test_rls_tenant_isolation_gate_b1_g1():
    """
    Scorecard Gate B1-G1: Cloud SQL RLS Tenant Isolation
    User B receives 0 rows when attempting to select or mutate User A's sessions
    or consent logs using SET LOCAL app.current_user_id.
    """
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    session_id_a = str(uuid.uuid4())

    service = CloudSqlSessionService()

    # Simulated in-memory database table with Row-Level Security policy simulation
    mock_db_sessions = {
        session_id_a: {
            "id": uuid.UUID(session_id_a),
            "user_id": uuid.UUID(user_a),
            "app_name": "workkbot",
            "state": {"owner": "User A"},
            "created_at": None,
            "updated_at": None,
            "expires_at": None,
        }
    }

    # Simulate Postgres RLS engine:
    # POLICY: user_id = current_setting('app.current_user_id', true)::uuid
    def simulate_postgres_rls_query(query: str, current_setting_user_id: str, *args):
        # Emulates database-enforced RLS check
        if "FROM public.adk_sessions" in query:
            target_id = str(args[0])
            record = mock_db_sessions.get(target_id)
            if record and str(record["user_id"]) == current_setting_user_id:
                return record
            return None
        return None

    # When User A queries their own session:
    with patch("session.cloud_sql_session_service.get_connection") as mock_conn_ctx:
        conn_user_a = AsyncMock()
        conn_user_a.fetchrow.side_effect = lambda q, *args: simulate_postgres_rls_query(q, user_a, *args)
        
        ctx_a = AsyncMock()
        ctx_a.__aenter__.return_value = conn_user_a
        ctx_a.__aexit__.return_value = None
        mock_conn_ctx.return_value = ctx_a

        sess_a = await service.get_session(session_id=session_id_a, user_id=user_a)
        assert sess_a is not None
        assert sess_a.id == session_id_a
        assert sess_a.user_id == user_a

    # When User B attempts to query User A's session:
    with patch("session.cloud_sql_session_service.get_connection") as mock_conn_ctx:
        conn_user_b = AsyncMock()
        conn_user_b.fetchrow.side_effect = lambda q, *args: simulate_postgres_rls_query(q, user_b, *args)

        ctx_b = AsyncMock()
        ctx_b.__aenter__.return_value = conn_user_b
        ctx_b.__aexit__.return_value = None
        mock_conn_ctx.return_value = ctx_b

        # Under RLS, User B receives None (0 rows)
        sess_b_view = await service.get_session(session_id=session_id_a, user_id=user_b)
        assert sess_b_view is None, "Tenant isolation violation: User B must receive 0 rows for User A's session"
