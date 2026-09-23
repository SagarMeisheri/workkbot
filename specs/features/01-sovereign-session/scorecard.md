# Block 1 Scorecard: Sovereign FastAPI Backend, Cloud SQL RLS & Expo Shell

## 1. Verification Rubric & Exit Gates

| Gate ID | Verification Item | Target | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **B1-G1** | Cloud SQL RLS Tenant Isolation | User B receives 0 rows when attempting to select or mutate User A's sessions or consent logs using `SET LOCAL app.current_user_id` | Automated pytest suite with two distinct simulated auth contexts | [ ] PENDING |
| **B1-G2** | ADK Session Service Persistence | `create_session`, `update_session_state`, `append_event`, `list_events`, and 90-day TTL expiration calculation succeed against Cloud SQL | Unit and integration tests in `backend/tests/test_session_service.py` | [ ] PENDING |
| **B1-G3** | Sovereign Region Health Endpoint | `GET /health` returns HTTP 200 with JSON payload explicitly validating `"region": "asia-south1"` | `pytest backend/tests/test_health.py` | [ ] PENDING |
| **B1-G4** | Non-Root Docker Container Execution | Docker image builds successfully and executes as non-root user (`appuser`, UID 10001) binding to port 8080 | Docker build & container inspection script | [ ] PENDING |
| **B1-G5** | Expo Mobile Shell & Secure Store | Frontend initializes with Expo Router, and auth token storage relies on `expo-secure-store` | TypeScript type-check and storage adapter unit test | [ ] PENDING |

---

## 2. Automated Test Execution Commands

```bash
# 1. Run backend unit tests and RLS mock isolation tests
cd backend && pytest -v tests/

# 2. Test Docker build and non-root execution
docker build -t enterprise-ai-backend:block1 -f infra/docker/Dockerfile backend
docker run --rm enterprise-ai-backend:block1 whoami | grep "appuser"

# 3. Test frontend type checking
cd frontend && pnpm run tsc --noEmit
```

---

## 3. Exit Criteria Sign-off
Block 1 is considered complete ONLY when all 5 scorecard gates have passed without exception.
