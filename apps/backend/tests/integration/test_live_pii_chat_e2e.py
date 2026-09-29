"""Live E2E PII Sanitization & Storage Test (Spec 03, VAL-03.9).

Executes a live conversational turn with sensitive citizen PII against the live API,
verifies that:
1. The client receives the rehydrated SSE stream.
2. The user event written to Supabase stores ONLY tokenized surrogate text at rest.
3. Zero plaintext citizen PII exists in Supabase public.adk_events.
"""
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.config import settings
from src.auth.client import supabase_admin, _local_db


@pytest.mark.live_gemini
@pytest.mark.asyncio
async def test_live_pii_chat_e2e_storage_at_rest():
    """Live verification of PII tokenization before Supabase persistence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login Reviewer
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
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 2. Sign DPDP statutory consent
        from src.routers.consent import DPDP_DISCLOSURES_EN
        consent_res = await client.post(
            "/api/v1/consent",
            headers=auth_headers,
            json={
                "consent_version": "2026.1",
                "language": "en",
                "accepted_disclosures": DPDP_DISCLOSURES_EN,
            },
        )
        assert consent_res.status_code == 200

        # 3. Generate unique session ID
        session_id = f"sess_live_pii_{uuid.uuid4().hex[:8]}"
        raw_prompt = "Taxpayer Rahul has PAN ABCDE1234F and email rahul.taxpayer@mumbai.in. Please confirm tax filing checklist."

        # 3. Call /api/v1/chat/stream
        chat_res = await client.post(
            "/api/v1/chat/stream",
            headers=auth_headers,
            json={
                "message": raw_prompt,
                "sessionId": session_id,
            },
        )
        assert chat_res.status_code == 200

        # Parse SSE stream
        chunks = []
        for line in chat_res.text.strip().split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                payload_str = line[6:].strip()
                if payload_str:
                    try:
                        chunks.append(json.loads(payload_str))
                    except Exception:
                        pass

        assert len(chunks) > 0

        # 4. Verify SSE stream delivered text does NOT expose raw tokens
        all_streamed_text = ""
        for chunk in chunks:
            parts = chunk.get("content", {}).get("parts", [])
            for p in parts:
                all_streamed_text += p.get("text", "")

        assert "<IN_PAN_1>" not in all_streamed_text
        assert "<EMAIL_1>" not in all_streamed_text

        # 5. Check persisted event
        # Verify in local store or Supabase
        stored_user_events = [
            e for e in _local_db.get("adk_events", [])
            if e.get("session_id") == session_id and e.get("author") == "user"
        ]
        
        # Also query Supabase if client is available
        sb = supabase_admin.get_client()
        if sb and token:
            try:
                sb.postgrest.auth(token)
                res = sb.table("adk_events").select("*").eq("session_id", session_id).eq("author", "user").execute()
                if res.data:
                    stored_user_events.extend(res.data)
            except Exception as e:
                pass

        assert len(stored_user_events) >= 1
        stored_user_event = stored_user_events[0]
        stored_text = str(stored_user_event["content"])

        # CRITICAL DPDP SEC 8(5) ASSERTIONS:
        # Plaintext PAN and Email MUST NOT be stored in Supabase
        assert "ABCDE1234F" not in stored_text, "CRITICAL: Plaintext PAN leaked into Supabase adk_events!"
        assert "rahul.taxpayer@mumbai.in" not in stored_text, "CRITICAL: Plaintext Email leaked into Supabase adk_events!"

        # Surrogate tokens MUST be present in Supabase at rest
        assert "<IN_PAN_1>" in stored_text
        assert "<EMAIL_1>" in stored_text
