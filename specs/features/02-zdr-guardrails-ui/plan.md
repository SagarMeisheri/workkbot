# Block 2 Plan: ADK 2.0 Lifecycle Callbacks, ZDR Gemini & Expo Chat UI

## 1. Objective
Implement sovereign AI guardrails and conversational streaming:
1. Enforce India DPDP Act Notice & Itemised Consent (Sections 5 & 6) using an ADK 2.0 `before_agent` lifecycle hook that halts execution if `CORE_CHAT` consent is missing.
2. Build an in-memory PII scrubber running at `before_model` and `after_model` to pseudonymize Indian PAN, Aadhaar, phone numbers, and emails with deterministic tokens (`{{PSEUDO_...}}`), and restore them before streaming to the client.
3. Configure the Google GenAI SDK 2.0 client for Vertex AI in `asia-south1` with Zero Data Retention (ZDR, context caching disabled).
4. Implement a FastAPI Server-Sent Events (SSE) `/chat` endpoint streaming ADK runner events.
5. Integrate `@assistant-ui/react-native` in the Expo app connected to the `/chat` SSE stream with an itemised `ConsentSheet` modal.

---

## 2. Architectural Blueprint

```
+-------------------------------------------------------------+
|             Expo Mobile App (@assistant-ui/react-native)    |
|   - Native ConsentSheet (Itemised Consent for CORE_CHAT)    |
|   - SSE Chat Consumer -> Renders assistant & tool chunks    |
+------------------------------+------------------------------+
                               | POST /chat (SSE Stream)
                               v
+-------------------------------------------------------------+
|                     FastAPI /chat Route                     |
|  - Validates auth token & injects user_id into ADK Context  |
+------------------------------+------------------------------+
                               | In-memory ADK Execution Pipeline
                               v
+-------------------------------------------------------------+
|                 ADK 2.0 Lifecycle Pipeline                  |
|                                                             |
|  1. before_agent: [consent_gate.py]                         |
|     - Queries active consent; raises ConsentRequiredException|
|                                                             |
|  2. before_model: [pii_scrubber.py]                         |
|     - Masks Aadhaar/PAN/Phone/Email into {{PSEUDO_...}}      |
|     - Stores translation map in ephemeral request state     |
|                                                             |
|  3. Model Execution: [vertex_client.py]                     |
|     - Vertex AI Gemini 2.0 Flash in asia-south1             |
|     - ZDR: No context caching, ephemeral execution          |
|                                                             |
|  4. after_model: [pii_scrubber.py]                          |
|     - Rehydrates {{PSEUDO_...}} back to actual values       |
|                                                             |
|  5. SSE Stream Emitter -> Client                            |
+-------------------------------------------------------------+
```

---

## 3. Dependency Sequence
1. Backend Lifecycle Callbacks:
   - `backend/src/callbacks/consent_gate.py`
   - `backend/src/callbacks/pii_scrubber.py`
   - `backend/tests/test_consent_gate.py`
   - `backend/tests/test_pii_scrubber.py`
2. Vertex AI Sovereign Client:
   - `backend/src/agent/vertex_client.py`
   - `backend/tests/test_vertex_client.py`
3. Streaming Chat Route:
   - `backend/src/routes/chat.py`
   - `backend/tests/test_chat_route.py`
4. Mobile UI Integration:
   - `frontend/components/consent/ConsentSheet.tsx`
   - `frontend/components/chat/Thread.tsx` (using `@assistant-ui/react-native`)
   - `frontend/app/(tabs)/chat.tsx`
