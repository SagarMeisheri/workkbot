# Block 5 Specification: Async HITL (LongRunningFunctionTool), CERT-In Audit & Cloud Armor Launch

## 1. Functional Specification

### 1.1 Append-Only Audit Schema (`infra/migrations/004_audit.sql`)

```sql
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES public.adk_sessions(id) ON DELETE SET NULL,
    action_type VARCHAR(64) NOT NULL,
    tool_name VARCHAR(64),
    parameters_scrubbed JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL, -- 'SUCCESS', 'FAILED', 'REJECTED'
    ip_address_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs FORCE ROW LEVEL SECURITY;
CREATE POLICY "audit_logs_read_own" ON public.audit_logs
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- Enforce strict append-only invariance (tamper resistance)
CREATE RULE no_update_audit_logs AS ON UPDATE TO public.audit_logs DO INSTEAD NOTHING;
CREATE RULE no_delete_audit_logs AS ON DELETE TO public.audit_logs DO INSTEAD NOTHING;
```

---

### 1.2 Human-in-the-Loop via ADK 2.6+ `LongRunningFunctionTool`

#### 1. Tool Declaration
State-modifying actions are wrapped using ADK's native `LongRunningFunctionTool`:
```python
from google.adk.tools import LongRunningFunctionTool

async def submit_email_for_approval(recipient: str, subject: str, body: str) -> dict:
    """Submit an outbound email for human confirmation before transmission."""
    return {
        "status": "PENDING_CONFIRMATION",
        "action": "send_email",
        "recipient": recipient,
        "subject": subject,
        "body_preview": body[:120]
    }

email_tool = LongRunningFunctionTool(submit_email_for_approval)
```

#### 2. Resumption Endpoint (`POST /webhooks/hitl-resume`)
- **Headers**: `Authorization: Bearer <JWT>`
- **Request Body**:
  ```json
  {
    "function_call_id": "fn_call_9f82bc71",
    "decision": "CONFIRMED", // or "REJECTED"
    "client_timestamp": "2026-09-23T03:45:00Z"
  }
  ```
- **Execution**:
  - Validates `function_call_id` and user ownership.
  - Returns result back into the ADK runner context for that `function_call_id`.
  - If `CONFIRMED`, triggers the actual execution via the provider's MCP tool; if `REJECTED`, returns cancellation message to the conversation.

---

### 1.3 CERT-In & DPDP Audit Callback (`backend/src/callbacks/audit.py`)
- Hook: ADK 2.6+ `after_agent_callback`.
- Signature:
  ```python
  from google.adk.agents.callback_context import CallbackContext
  from google.genai import types

  async def cert_in_audit_callback(
      callback_context: CallbackContext
  ) -> types.Content | None:
      ...
  ```
- Extracts execution metadata, scrubs parameters via `pii_scrubber`, records NTP/UTC timestamps, and inserts an append-only row into `public.audit_logs`.
- Fail-safe: Any failure to write to `audit_logs` raises an alerting exception and halts sensitive operations.

---

### 1.4 Cloud Run & Google Cloud Armor Infrastructure (`infra/cloudbuild.yaml`)
- **Serverless NEG**: Connects Cloud Run service in `asia-south1` to Google Cloud External Application Load Balancer.
- **Cloud Armor Security Policy**:
  - Enforces OWASP Top 10 rules.
  - Rate limits requests to 100 requests per minute per IP.
  - Restricts ingress to Cloud Run so direct `*.run.app` access is denied (`--ingress=internal-and-cloud-load-balancing`).
- **Cloud Build Pipeline**:
  - Builds multi-stage Dockerfile.
  - Verifies non-root execution (`appuser`, UID 10001).
  - Deploys to Cloud Run in `asia-south1`.
