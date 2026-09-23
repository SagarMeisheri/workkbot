# Block 2 Specification: ADK 2.6 Lifecycle Callbacks, ZDR Gemini, SDP Guardrails & Expo Chat UI

## 1. Functional Specification

### 1.1 Consent Gate Callback (`backend/src/callbacks/consent_gate.py`)
- **Hook**: ADK 2.6+ `before_agent_callback`
- **Signature**:
  ```python
  from google.adk.agents.callback_context import CallbackContext
  from google.genai import types

  async def consent_gate_callback(callback_context: CallbackContext) -> types.Content | None:
      ...
  ```
- **Behavior**:
  - Extracts `user_id` from `callback_context.state['user:id']`.
  - Queries `consent_logs` for latest status of `consent_type = 'CORE_CHAT'`.
  - If status != `'GRANTED'`, aborts the execution immediately by returning a structured `types.Content` containing a `CONSENT_REQUIRED` challenge or raising an application challenge, preventing the agent from invoking models or tools.

---

### 1.2 In-Flight PII Redaction & Rehydration (`backend/src/callbacks/pii_scrubber.py`)
- **Hooks**: ADK 2.6+ `before_model_callback` and `after_model_callback`
- **Signatures**:
  ```python
  from google.adk.agents.callback_context import CallbackContext
  from google.adk.models.llm_request import LlmRequest
  from google.adk.models.llm_response import LlmResponse

  def pii_scrubber_before_model(
      callback_context: CallbackContext, llm_request: LlmRequest
  ) -> LlmResponse | None:
      ...

  def pii_scrubber_after_model(
      callback_context: CallbackContext, llm_response: LlmResponse
  ) -> LlmResponse | None:
      ...
  ```
- **InfoType Patterns (Aligned with Google Cloud Sensitive Data Protection)**:
  - **`INDIA_PAN_INDIVIDUAL`**: `r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'` -> `{{PSEUDO_PAN_N}}`
  - **`INDIA_AADHAAR_NUMBER`**: `r'\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b'` -> `{{PSEUDO_AADHAAR_N}}`
  - **`INDIA_GST_INDIVIDUAL`**: `r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b'` -> `{{PSEUDO_GST_N}}`
  - **`PHONE_NUMBER` (India)**: `r'\b(?:\+91|91)?[6-9]\d{9}\b'` -> `{{PSEUDO_PHONE_N}}`
  - **`EMAIL_ADDRESS`**: `r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b'` -> `{{PSEUDO_EMAIL_N}}`
- **Ephemeral Zero-Data-Retention Storage via `temp:` Scoping**:
  - The lookup dictionary mapping `{{PSEUDO_...}}` tokens to raw text is stored strictly in `callback_context.state['temp:pii_map']`.
  - Under ADK 2.6+ runtime rules, `temp:` prefixed keys are held only in memory during the execution turn and are never passed to the persistent session service (`CloudSqlSessionService`), mathematically guaranteeing zero persistent leakage of the translation table.
- **Rehydration (`after_model_callback`)**:
  - Inspects `llm_response.content` parts.
  - Replaces all pseudonyms using `callback_context.state.get('temp:pii_map', {})` before returning the final response to the SSE streaming pipeline.

---

### 1.3 Vertex AI Sovereign Client (`backend/src/agent/vertex_client.py`)
- **SDK**: `google-genai` (ADK 2.6+ compatible)
- **Configuration**:
  - `location`: `"asia-south1"`
  - `api_endpoint`: `"asia-south1-aiplatform.googleapis.com"`
  - `model`: `"gemini-2.0-flash"`
- **Zero Data Retention (ZDR)**:
  - Disables context caching (`cached_content=None`).
  - Strict compliance with signed Google Cloud Data Processing Addendum (DPA) and Abuse Monitoring Opt-Out form.

---

### 1.4 SSE Chat Endpoint (`backend/src/routes/chat.py`)
- **Method**: `POST /chat`
- **Accept**: `text/event-stream`
- **Stream Events**:
  - `data: {"type": "session_init", "session_id": "UUID"}\n\n`
  - `data: {"type": "content_delta", "delta": "Hello"}\n\n`
  - `data: {"type": "done"}\n\n`

---

### 1.5 Frontend Expo Integration (`frontend/`)
- **`ConsentSheet.tsx`**:
  - Statutory notice presentation detailing Mumbai processing (`asia-south1`), 90-day retention, and revocation rights.
  - "Grant Consent" button issues authenticated call to `/consent/grant`.
- **`Thread.tsx` / `chat.tsx`**:
  - Integrates `@assistant-ui/react-native`.
  - Consumes `/chat` SSE stream and handles real-time markdown token rendering.
