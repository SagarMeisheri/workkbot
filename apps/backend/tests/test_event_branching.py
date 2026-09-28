"""VAL-02.4: ChatGPT-Style Event Tree Branching (R02.3).
Verifies that editing a prior message references the parent checkpoint and creates
a new child branch in Supabase without overwriting earlier turns.
"""
import uuid
import pytest
from src.agent.runner import AdkRunnerSingleton
from src.config import settings


@pytest.mark.asyncio
async def test_event_branching_preserves_tree():
    """Editing turn 1 creates branch without modifying turn 1 original path."""
    runner = AdkRunnerSingleton()
    user_id = "00000000-0000-0000-0000-000000000002"
    org_id = settings.REVIEWER_ORG_ID
    session_id = f"sess_branch_{uuid.uuid4().hex[:8]}"

    # 1. Turn 1 (Original)
    turn1_events = [
        e async for e in runner.run_turn_stream(
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            message="Prompt Version 1: Explain GST tax rates",
        )
    ]
    assert len(turn1_events) > 0
    original_model_event_id = turn1_events[-1]["id"]

    # Retrieve stored events after turn 1
    session_state_1 = await runner.session_service.get_session(session_id, user_id, org_id)
    assert len(session_state_1["events"]) == 2
    parent_user_event_id = session_state_1["events"][0]["id"]

    # 2. Branch: User edits Prompt 1, creating Turn 1 (Branch 2) referencing root checkpoint
    branch_events = [
        e async for e in runner.run_turn_stream(
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            message="Prompt Version 2: Explain GST input tax credit (ITC)",
            checkpoint_id=parent_user_event_id,
        )
    ]
    assert len(branch_events) > 0

    # Retrieve all events for session: prior branch events MUST still exist!
    session_state_2 = await runner.session_service.get_session(session_id, user_id, org_id)
    all_events = session_state_2["events"]
    assert len(all_events) == 4, f"Expected 4 events (2 branches), found {len(all_events)}"

    # Verify both original prompt and branched prompt exist in history
    prompts = [str(ev["content"]) for ev in all_events if ev["author"] == "user"]
    assert any("Prompt Version 1" in p for p in prompts), "Original prompt was overwritten!"
    assert any("Prompt Version 2" in p for p in prompts), "Branched prompt not recorded!"

    # Clean up
    await runner.session_service.delete_session(session_id, user_id, org_id)
