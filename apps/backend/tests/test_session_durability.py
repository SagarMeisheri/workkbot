"""VAL-02.3: Session Durability & History Preservation.
Verifies that restarting or recreating backend container instances preserves conversation
and event history in Supabase PostgreSQL via DatabaseSessionService.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings
from src.agent.runner import AdkRunnerSingleton
from src.agent.session_service import SupabaseAdkSessionService


@pytest.mark.asyncio
async def test_session_durability_across_runner_recreation():
    """Simulates backend container teardown and verifies session retrieval from Supabase."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login Reviewer
        login_res = await client.post(
            "/api/v1/auth/reviewer-login",
            json={"email": settings.REVIEWER_EMAIL, "password": settings.REVIEWER_PASSWORD},
        )
        token = login_res.json()["access_token"]
        user_id = login_res.json()["user_id"]
        org_id = login_res.json()["org_id"]

        session_id = f"sess_durable_{uuid.uuid4().hex[:8]}"

        # 1. First turn on Instance A
        runner_instance_a = AdkRunnerSingleton()
        events_a = [
            e async for e in runner_instance_a.run_turn_stream(
                user_id=user_id,
                org_id=org_id,
                session_id=session_id,
                message="Turn 1: Record purchase invoice #INV-9021",
            )
        ]
        assert len(events_a) > 0

        # 2. Simulate container restart / crash: discard Instance A and instantiate Instance B
        del runner_instance_a
        runner_instance_b = AdkRunnerSingleton()

        # Fetch session from new instance
        stored_session = await runner_instance_b.session_service.get_session(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
        )
        assert stored_session is not None
        assert stored_session["id"] == session_id
        
        events = stored_session.get("events", [])
        assert len(events) >= 2  # 1 user event + 1 model event
        user_event = next(e for e in events if e["author"] == "user")
        assert "INV-9021" in str(user_event["content"])

        # 3. Clean up
        await runner_instance_b.session_service.delete_session(session_id, user_id, org_id)
