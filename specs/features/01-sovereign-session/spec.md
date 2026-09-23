# Block 1 Specification: Sovereign FastAPI Backend, Cloud SQL RLS & Expo Shell

## 1. Functional Specification

### 1.1 Cloud SQL Database Schema (`infra/migrations/001_adk_foundation.sql`)

#### Extensions & Users Table
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX idx_users_email ON public.users(email);
```

#### Table: `consent_logs`
Records itemised Data Principal consent actions (DPDP Act Sec. 5 & 6).
```sql
CREATE TABLE public.consent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    consent_type VARCHAR(64) NOT NULL, -- 'CORE_CHAT', 'WORKSPACE_INTEGRATION', 'ZOHO_INTEGRATION'
    status VARCHAR(32) NOT NULL,       -- 'GRANTED', 'REVOKED'
    notice_version VARCHAR(32) NOT NULL,
    ip_address_hash VARCHAR(64),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX idx_consent_logs_user_type ON public.consent_logs(user_id, consent_type, created_at DESC);
```

#### Table: `adk_sessions`
Manages ADK 2.6+ conversational session state with a 90-day storage limitation TTL.
```sql
CREATE TABLE public.adk_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    app_name VARCHAR(64) NOT NULL DEFAULT 'workkbot',
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (timezone('utc', now()) + INTERVAL '90 days')
);
CREATE INDEX idx_adk_sessions_user_id ON public.adk_sessions(user_id);
CREATE INDEX idx_adk_sessions_expires_at ON public.adk_sessions(expires_at);
```

#### Table: `adk_events`
Stores ADK 2.6+ session event stream (user messages, agent invocations, tool events).
```sql
CREATE TABLE public.adk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.adk_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
CREATE INDEX idx_adk_events_session ON public.adk_events(session_id, created_at ASC);
```

#### Row-Level Security (RLS) Invariants
RLS must be enabled and forced on all tables with strict ownership checks via transaction-scoped `app.current_user_id`:
```sql
ALTER TABLE public.consent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE public.adk_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.adk_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.adk_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.adk_events FORCE ROW LEVEL SECURITY;

CREATE POLICY "consent_logs_user_isolation" ON public.consent_logs
    FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "adk_sessions_user_isolation" ON public.adk_sessions
    FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "adk_events_user_isolation" ON public.adk_events
    FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
```

---

### 1.2 ADK 2.6+ Session Service (`backend/src/session/cloud_sql_session_service.py`)
Implements session state persistence compatible with ADK 2.6+ session abstraction over Cloud SQL (`asyncpg` + `google-cloud-sql-connector`):
- `create_session(user_id: str, app_name: str, initial_state: dict = None) -> Session`:
  Inserts row into `adk_sessions` with calculated 90-day expiration.
- `get_session(session_id: str, user_id: str) -> Optional[Session]`:
  Fetches active session; returns None if session is expired or does not belong to `user_id`.
- `update_session_state(session_id: str, user_id: str, state_delta: dict) -> Session`:
  Merges JSONB state and updates `updated_at`. **Crucial Invariant**: Keys prefixed with `temp:` (e.g. `temp:pii_map`) are strictly filtered out and never saved to PostgreSQL, guaranteeing ephemeral in-flight data cannot leak into persistent storage.
- `append_event(session_id: str, user_id: str, event_type: str, content: dict) -> None`:
  Inserts an event record into `adk_events`.
- `list_events(session_id: str, user_id: str) -> List[dict]`:
  Returns chronological events for the session.

---

### 1.3 FastAPI Application (`backend/src/main.py`)
- **GET `/health`**:
  - Response (200 OK):
    ```json
    {
      "status": "healthy",
      "region": "asia-south1",
      "environment": "production",
      "timestamp": "2026-09-23T03:37:00Z"
    }
    ```
- **Lifespan Manager**: Validates database connectivity and regional variables on startup.
- **CORS Middleware**: Restricted to configured mobile/web origins.

---

### 1.4 Docker Specification (`infra/docker/Dockerfile`)
- Base image: `python:3.12-slim`
- Multi-stage build: builder stage for compilation, runtime stage for minimal footprint.
- Security constraints:
  - System user: `appuser` (UID 10001, GID 10001)
  - No `root` execution
  - Port `8080` exposed
  - Healthcheck configured against `GET /health`

---

### 1.5 Frontend Expo Shell (`frontend/`)
- Expo Router configuration with tab navigation:
  - `/(tabs)/chat`: Primary conversational interface.
  - `/(tabs)/consent`: Active consents and toggle controls.
  - `/(tabs)/settings`: Privacy and data rights controls.
- Secure store adapter (`frontend/lib/auth.ts`):
  - Manages session JWT tokens using `expo-secure-store`.
  - Guarantees auth tokens are stored strictly within device hardware keychain/keystore.
