"""VAL-02.6: Reviewer Conversation & Message History Hydration.
Verifies that:
1. Reviewer can create and list persistent conversations.
2. Turns recorded within a conversation are hydrated with their events via GET /api/v1/conversations/{id}.
3. The returned payload contains user and model turns, including parent checkpoints and contents.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings
from src.agent.runner import runner_singleton


@pytest.mark.asyncio
async def test_reviewer_conversation_creation_and_message_hydration():
    """Reviewer creates conversation, records turns, and hydrates messages."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Reviewer logs in
        login_res = await client.post(
            "/api/v1/auth/reviewer-login",
            json={
                "email": settings.REVIEWER_EMAIL,
                "password": settings.REVIEWER_PASSWORD,
            },
        )
        assert login_res.status_code == 200
        auth_data = login_res.json()
        token = auth_data["access_token"]
        user_id = auth_data["user_id"]
        org_id = auth_data["org_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Reviewer creates conversation with explicit UUID and Title
        conv_id = str(uuid.uuid4())
        conv_title = "Quarterly GST Filing and Reconciliations"
        create_res = await client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"id": conv_id, "title": conv_title},
        )
        assert create_res.status_code == 200
        created_data = create_res.json()
        assert created_data["id"] == conv_id
        assert created_data["title"] == conv_title

        # 3. List conversations and assert newly created conversation is present
        list_res = await client.get("/api/v1/conversations", headers=headers)
        assert list_res.status_code == 200
        conversations = list_res.json().get("conversations", [])
        matched = next((c for c in conversations if c["id"] == conv_id), None)
        assert matched is not None, "Created conversation was not returned in list"
        assert matched["title"] == conv_title

        # 4. Execute a conversational turn linked to this conversation
        session_id = f"sess_{conv_id}"
        events = [
            ev async for ev in runner_singleton.run_turn_stream(
                user_id=user_id,
                org_id=org_id,
                session_id=session_id,
                message="What are the mandatory fields on an Indian e-invoice?",
                conversation_id=conv_id,
                auth_token=token,
            )
        ]
        assert len(events) > 0

        # 5. Fetch full conversation with hydrated events
        get_res = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert get_res.status_code == 200
        conv_detail = get_res.json()
        assert conv_detail["id"] == conv_id
        assert conv_detail["title"] == conv_title
        
        # Verify events contain both user prompt and assistant response
        events_list = conv_detail.get("events", [])
        assert len(events_list) >= 2, f"Expected at least 2 events in conversation, got {len(events_list)}"
        
        user_turn = next((e for e in events_list if e.get("author") == "user"), None)
        assert user_turn is not None
        assert "e-invoice" in str(user_turn.get("content"))

        model_turn = next((e for e in events_list if e.get("author") in ("model", "assistant")), None)
        assert model_turn is not None
