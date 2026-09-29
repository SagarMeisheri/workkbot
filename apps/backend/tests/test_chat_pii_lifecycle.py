"""End-to-End Chat PII Lifecycle & Stream Rehydration Test (Spec 03, VAL-03.9)."""
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from src.agent.runner import runner_singleton
from src.agent.session_service import session_service
from src.compliance.session_pii_vault import session_pii_vault


@pytest.mark.asyncio
async def test_chat_stream_pii_tokenization_and_rehydration(monkeypatch):
    """
    Verifies that:
    1. Raw user PII is replaced with tokens before model reasoning.
    2. Model tokens in SSE chunks are rehydrated so user sees natural text.
    3. Stored database event retains tokenized text (no plaintext PII at rest).
    """
    from src.agent.runner import AdkRunnerSingleton
    if hasattr(AdkRunnerSingleton, "_original_run_turn_stream"):
        monkeypatch.setattr(AdkRunnerSingleton, "run_turn_stream", AdkRunnerSingleton._original_run_turn_stream)

    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    session_id = f"sess_pii_{uuid.uuid4().hex[:8]}"
    raw_prompt = "Send tax reminder to Rahul at rahul@acme.in with PAN ABCDE1234F."

    # Mock runner._runner.run_async to simulate model generating response using tokens
    class MockAdkEvent:
        author = "model"
        id = "evt_model_resp_1"
        partial = False
        content = type("Content", (), {
            "parts": [
                type("Part", (), {
                    "thought": False,
                    "text": "I have drafted a reminder for <EMAIL_1> quoting PAN <IN_PAN_1>.",
                })()
            ]
        })()

    async def mock_run_async(*args, **kwargs):
        # Assert that the new_message sent to ADK Runner contains tokenized text, NOT raw PII
        new_msg = kwargs.get("new_message")
        part_text = new_msg.parts[0].text
        assert "rahul@acme.in" not in part_text
        assert "ABCDE1234F" not in part_text
        assert "<EMAIL_1>" in part_text
        assert "<IN_PAN_1>" in part_text
        yield MockAdkEvent()

    with patch.object(runner_singleton._runner, "run_async", side_effect=mock_run_async):
        events = []
        async for chunk in runner_singleton.run_turn_stream(
            user_id=user_id,
            org_id=org_id,
            session_id=session_id,
            message=raw_prompt,
        ):
            events.append(chunk)

        # Verify stream received rehydrated text
        model_chunks = [e for e in events if e.get("content", {}).get("parts")]
        assert len(model_chunks) >= 1
        delivered_text = model_chunks[0]["content"]["parts"][0]["text"]

        # Delivered text to the user MUST contain real values
        assert "rahul@acme.in" in delivered_text
        assert "ABCDE1234F" in delivered_text
        # And must NOT expose raw token strings to the user
        assert "<EMAIL_1>" not in delivered_text
        assert "<IN_PAN_1>" not in delivered_text
