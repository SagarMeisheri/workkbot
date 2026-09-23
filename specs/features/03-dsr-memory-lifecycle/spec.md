# Block 3 Specification: Data Principal Rights (DSR) & Storage Governance

## 1. Functional Specification

### 1.1 Retention & Memory Schema (`infra/migrations/002_retention.sql`)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE public.user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_memories FORCE ROW LEVEL SECURITY;
CREATE POLICY "user_memories_user_isolation" ON public.user_memories
    FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE INDEX idx_user_memories_embedding ON public.user_memories USING ivfflat (embedding vector_cosine_ops);

-- Retention procedure for DPDP Sec. 8(7) Storage Limitation
CREATE OR REPLACE FUNCTION public.purge_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM public.adk_sessions
    WHERE expires_at < timezone('utc', now());
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

### 1.2 Vector Memory Service (`backend/src/session/memory_service.py`)
- **Embedding Model**: Vertex AI `text-embedding-004` via `asia-south1-aiplatform.googleapis.com` (768 dimensions).
- **PII Guardrail**: Before embedding or persisting any memory, passes text through `pii_scrubber` aligned with Google Cloud Sensitive Data Protection Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_INDIVIDUAL`, `INDIA_GST_INDIVIDUAL`, `PHONE_NUMBER`, `EMAIL_ADDRESS`). If any unmasked PII is detected, memory persistence is aborted.
- **Methods**:
  - `add_memory(user_id: str, text: str, metadata: dict) -> str`
  - `search_memories(user_id: str, query: str, limit: int = 5) -> List[dict]`
  - `delete_memory(user_id: str, memory_id: str) -> bool`

---

### 1.3 User DSR Endpoints (`backend/src/routes/user.py`)

#### `POST /user/forget-me`
- **Purpose**: DPDP Section 12 Right to Erasure.
- **Security**: Requires active authenticated session.
- **Action**: Cascading deletion of:
  - `public.consent_logs`
  - `public.adk_sessions` (cascades to `adk_events`)
  - `public.user_memories`
  - `public.workspace_tokens`
- **Response (200 OK)**:
  ```json
  {
    "status": "ERASED",
    "user_id": "UUID",
    "timestamp": "2026-09-23T03:40:00Z",
    "message": "All personal data and session state have been permanently purged."
  }
  ```

#### `GET /user/export-data`
- **Purpose**: DPDP Section 11 Right to Access / Portability.
- **Response (200 OK)**:
  ```json
  {
    "export_version": "1.0",
    "user_id": "UUID",
    "generated_at": "2026-09-23T03:40:00Z",
    "consents": [...],
    "sessions": [...],
    "events": [...],
    "memories": [...]
  }
  ```

---

### 1.4 Frontend Settings & Grievance Drawer (`frontend/app/(tabs)/settings.tsx`)
- Displays current user identity and consent status.
- "Export Personal Data" button: Calls `/user/export-data` and triggers `expo-sharing` to save or send the JSON bundle.
- "Erase All Personal Data (Forget Me)" button: Prompts with a destructive confirmation dialog; upon confirmation, calls `/user/forget-me` and signs the user out.
- Grievance Redressal Drawer: Discloses the designated Data Protection Officer (DPO) name, email, address, and response timeline (within 72 hours) compliant with DPDP Section 13.
