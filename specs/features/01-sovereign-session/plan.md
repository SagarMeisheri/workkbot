# Block 1 Plan: Sovereign FastAPI Backend, Cloud SQL RLS & Expo Shell

## 1. Objective
Establish the foundational infrastructure of the Enterprise AI Assistant:
1. Initialize the polyglot monorepo with `pnpm` workspaces for frontend/infra and Python 3.12 packaging for backend.
2. Deploy the foundational Cloud SQL migration (`001_adk_foundation.sql`) creating `public.users`, `consent_logs`, `adk_sessions`, and `adk_events` with strict Row-Level Security (RLS).
3. Implement `CloudSqlSessionService` adhering to the Google Agent Development Kit (ADK) 2.6+ session persistence contract.
4. Scaffold the FastAPI backend with health endpoints confirming sovereign deployment in `asia-south1`.
5. Create the multi-stage non-root Dockerfile and Cloud Build configuration for `asia-south1`.
6. Scaffold the Expo mobile/web application shell with Expo Router and `expo-secure-store` wrapper for hardware-backed token storage.

---

## 2. Architectural Blueprint

```
+--------------------------------------------------------------+
|                  Expo App (iOS / Android / Web)              |
|  - Expo Router (tabs: /chat, /consent, /settings)            |
|  - expo-secure-store (Hardware Keychain/KeyStore Session)    |
+------------------------------+-------------------------------+
                               | HTTPS / WSS / SSE
                               v
+--------------------------------------------------------------+
|               FastAPI Server (Google Cloud Run)              |
|                   Region: asia-south1 (Mumbai)               |
|  - Non-root user (appuser:10001), Port: 8080                 |
|  - GET /health -> {"status": "ok", "region": "asia-south1"}  |
|  - CloudSqlSessionService (ADK 2.6+ Session Persistence)     |
|  - Direct VPC Egress / google-cloud-sql-connector            |
+------------------------------+-------------------------------+
                               | Private IP / IAM Auth (asia-south1)
                               v
+--------------------------------------------------------------+
|             Google Cloud SQL for PostgreSQL 16               |
|  - public.users                                              |
|  - consent_logs (RLS: user_id = current_setting(...))        |
|  - adk_sessions (RLS: user_id = current_setting(...), 90d)   |
|  - adk_events   (RLS: user_id = current_setting(...))        |
+--------------------------------------------------------------+
```

---

## 3. Dependency Sequence
1. Root monorepo configuration:
   - `pnpm-workspace.yaml`
   - Root `package.json`
2. Cloud SQL Migration:
   - `infra/migrations/001_adk_foundation.sql`
3. Backend Setup:
   - `backend/pyproject.toml`
   - `backend/src/session/cloud_sql_session_service.py`
   - `backend/src/main.py`
   - `backend/tests/test_session_service.py`
   - `backend/tests/test_health.py`
4. Infrastructure:
   - `infra/docker/Dockerfile`
   - `infra/cloudbuild.yaml`
5. Frontend Setup:
   - `frontend/package.json`
   - `frontend/app/_layout.tsx`
   - `frontend/lib/auth.ts` (with `expo-secure-store`)

---

## 4. Risks & Mitigations
- **Risk**: Client-side auth tokens stored in insecure localStorage or AsyncStorage.
  - **Mitigation**: Implement a custom storage adapter using `expo-secure-store` with Keychain accessibility attributes.
- **Risk**: Cross-tenant data leakage in multi-tenant PostgreSQL.
  - **Mitigation**: Enforce PostgreSQL Row-Level Security on every table via `FORCE ROW LEVEL SECURITY` and transaction-scoped `SET LOCAL app.current_user_id`, with verification tests asserting that User B receives zero records when querying User A's data.
