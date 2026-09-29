"""Workkbot Pytest Fixtures & Gemini Cost-Saver Mock Engine.

By default, suppresses live outbound calls to Google Gemini API during local and CI test runs.
Simulates canonical token streaming, reasoning blocks, and Supabase event tree persistence
in <10ms per turn with $0.00 cost.

To execute against the live Google Gemini API (asian-south1):
    RUN_LIVE_GEMINI=1 uv run pytest
    OR
    uv run pytest -m live_gemini
"""
import os
import uuid
import pytest
from typing import Any, AsyncIterator, Dict, Optional


from src.agent.runner import AdkRunnerSingleton
from src.compliance.callbacks import pii_anonymize_callback
from src.compliance.session_pii_vault import session_pii_vault

_ORIGINAL_RUN_TURN_STREAM = AdkRunnerSingleton.run_turn_stream


def is_live_gemini_enabled() -> bool:
    """Returns True if live Gemini calls are explicitly requested."""
    val = os.getenv("RUN_LIVE_GEMINI", "").lower()
    return val in ("1", "true", "yes")


async def mock_run_turn_stream(
    self,
    user_id: str,
    org_id: str,
    session_id: str,
    message: str,
    checkpoint_id: Optional[str] = None,
    model_preference: Optional[str] = None,
    state_delta: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    auth_token: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Deterministic, zero-cost mock for AdkRunnerSingleton.run_turn_stream.
    
    Persists user & model turns into self.session_service with accurate checkpoint
    tree branching, and yields streaming token deltas matching domain requirements.
    """
    # 1. Ensure persistent session exists
    await self.session_service.get_or_create_session(
        session_id=session_id,
        user_id=user_id,
        org_id=org_id,
        conversation_id=conversation_id,
        auth_token=auth_token,
    )

    branch_name = f"branch_{checkpoint_id[:8]}" if checkpoint_id else "main"
    user_event_id = f"evt_{uuid.uuid4().hex[:12]}_u"
    model_event_id = f"evt_{uuid.uuid4().hex[:12]}_m"

    # Sanitize user turn before persisting (DPDP Sec 8(5) tokenization at rest)
    sanitized_message, _ = pii_anonymize_callback(session_id, message)

    # 2. Persist user turn into session_service (satisfies durability & branching tests)
    await self.session_service.append_event(
        session_id=session_id,
        author="user",
        content={"role": "user", "parts": [{"text": sanitized_message}]},
        parent_event_id=checkpoint_id,
        branch=branch_name,
        event_id=user_event_id,
    )

    # 3. Determine mock response based on prompt context (satisfies test assertions)
    msg_lower = message.lower()
    if "dpdp" in msg_lower:
        part1 = "The Digital Personal Data Protection Act 2023 (DPDP Act) "
        part2 = "establishes India's statutory framework for processing digital personal data."
    elif "gst" in msg_lower or "gstr" in msg_lower:
        part1 = "Indian GST compliance: GSTR-1 is due on the 11th of each month, "
        part2 = "and GSTR-3B summary return is due on the 20th."
    elif "e-invoicing" in msg_lower:
        part1 = "E-Invoicing under GST: Generation of IRN (Invoice Reference Number) "
        part2 = "is mandatory for eligible B2B invoices."
    elif "inv-" in msg_lower or "invoice" in msg_lower:
        part1 = "Purchase invoice "
        part2 = "recorded successfully into ledger accounts."
    else:
        part1 = "Workkbot sovereign AI assistant: "
        part2 = f"Acknowledged query regarding '{message[:40]}'."

    full_reply = part1 + part2

    # 4. Persist model turn into session_service
    await self.session_service.append_event(
        session_id=session_id,
        author="model",
        content={"role": "model", "parts": [{"text": full_reply}]},
        parent_event_id=user_event_id,
        branch=branch_name,
        event_id=model_event_id,
    )

    # 5. Yield realistic SSE partial chunks with PII rehydration for user display
    yield {
        "id": model_event_id,
        "author": "model",
        "branch": branch_name,
        "content": {
            "role": "model",
            "parts": [{"text": session_pii_vault.rehydrate_text(session_id, part1)}],
        },
        "turnComplete": False,
    }

    yield {
        "id": model_event_id,
        "author": "model",
        "branch": branch_name,
        "content": {
            "role": "model",
            "parts": [{"text": session_pii_vault.rehydrate_text(session_id, part2)}],
        },
        "turnComplete": False,
    }

    # 6. Yield final completion turn
    yield {
        "id": model_event_id,
        "author": "model",
        "branch": branch_name,
        "content": {
            "role": "model",
            "parts": [],
        },
        "turnComplete": True,
    }


@pytest.fixture(autouse=True)
def auto_mock_gemini_runner(monkeypatch):
    """Automatically applies zero-cost mock runner unless RUN_LIVE_GEMINI=1."""
    AdkRunnerSingleton._original_run_turn_stream = _ORIGINAL_RUN_TURN_STREAM
    if is_live_gemini_enabled():
        return

    monkeypatch.setattr(AdkRunnerSingleton, "run_turn_stream", mock_run_turn_stream)
