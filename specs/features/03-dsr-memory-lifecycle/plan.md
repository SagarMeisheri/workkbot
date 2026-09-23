# Block 3 Plan: Data Principal Rights (DSR) & Storage Governance

## 1. Objective
Implement statutory Data Principal Rights and automated storage lifecycle controls under India DPDP Act 2023:
1. Implement automated 90-day Storage Limitation (Sec. 8(7)) via Cloud SQL retention functions.
2. Build self-service Data Principal Rights endpoints:
   - `POST /user/forget-me`: Immediate, cascading erasure across all relational and vector tables (Sec. 12).
   - `GET /user/export-data`: Cryptographically signed JSON data portability export of all user records (Sec. 11).
3. Develop `CloudSqlMemoryService` using sovereign `pgvector` embeddings with in-flight PII exclusion rules.
4. Build the mobile Privacy Settings screen (`frontend/app/(tabs)/settings.tsx`) with data export (via `expo-sharing`), erasure confirmation modal, and Grievance Redressal Officer contact drawer (Sec. 13).

---

## 2. Architectural Blueprint

```
+-------------------------------------------------------------+
|                 Expo Settings Screen (Tabs)                 |
|   - "Export My Data" -> Triggers GET /user/export-data      |
|   - "Erase All Data" -> Double-confirmation Modal -> POST   |
|   - Grievance Redressal Drawer -> DPO contacts (DPDP S.13)  |
+------------------------------+------------------------------+
                               | Authenticated REST
                               v
+-------------------------------------------------------------+
|                   FastAPI /user Endpoints                   |
|                                                             |
|  1. POST /user/forget-me:                                   |
|     - Deletes public.users row and cascades purge to:       |
|     - consent_logs, adk_sessions, adk_events, user_memories |
|     - workspace_tokens, audit_logs (anonymizes actor)       |
|                                                             |
|  2. GET /user/export-data:                                  |
|     - Bundles sessions, events, consents, memories into     |
|       deterministic, schema-validated JSON payload          |
+------------------------------+------------------------------+
                               | Private IP (asia-south1)
                               v
+-------------------------------------------------------------+
|           Google Cloud SQL Database (asia-south1)           |
|  - pgvector: user_memories table                            |
|  - Scheduled purge: purge_expired_sessions()                |
|    WHERE expires_at < NOW()                                 |
+-------------------------------------------------------------+
```

---

## 3. Dependency Sequence
1. Retention & Vector Migration:
   - `infra/migrations/002_retention.sql` (Creates `user_memories` table, `purge_expired_sessions()` function)
2. Long-Term Memory Service:
   - `backend/src/session/memory_service.py`
   - `backend/tests/test_memory_service.py`
3. User DSR Endpoints:
   - `backend/src/routes/user.py`
   - `backend/tests/test_user_dsr.py`
4. Mobile Settings & Redressal UI:
   - `frontend/app/(tabs)/settings.tsx`
   - `frontend/components/dsr/GrievanceDrawer.tsx`
