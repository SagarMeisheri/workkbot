# Block 3 Scorecard: Data Principal Rights (DSR) & Storage Governance

## 1. Verification Rubric & Exit Gates

| Gate ID | Verification Item | Target | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **B3-G1** | Zero Residual Records on Forget-Me | Executing `POST /user/forget-me` leaves exactly 0 records for that user ID across all database tables | Automated integration test in `backend/tests/test_forget_me.py` | [ ] PENDING |
| **B3-G2** | Complete Structured Data Export | `GET /user/export-data` returns JSON containing all and only the caller's consents, sessions, events, and memories | Schema validation test in `backend/tests/test_data_export.py` | [ ] PENDING |
| **B3-G3** | 90-Day Retention SQL Purge | `purge_expired_sessions()` successfully purges rows where `expires_at < NOW()` while retaining unexpired sessions | SQL procedure test in `backend/tests/test_retention.py` | [ ] PENDING |
| **B3-G4** | Vector Memory PII Scrubbing | Attempting to write unmasked PAN or Aadhaar to vector memory fails or redacts prior to insertion | Test suite in `backend/tests/test_memory_service.py` | [ ] PENDING |
| **B3-G5** | Mobile DSR & Redressal UI | Privacy screen renders DPO details and triggers export via `expo-sharing` | Component test and screenshot validation | [ ] PENDING |

---

## 2. Automated Test Execution Commands

```bash
# 1. Test Forget-Me cascading erasure
cd backend && pytest -v tests/test_forget_me.py

# 2. Test Data Export format and isolation
cd backend && pytest -v tests/test_data_export.py

# 3. Test 90-day retention procedure
cd backend && pytest -v tests/test_retention.py

# 4. Test vector memory service
cd backend && pytest -v tests/test_memory_service.py
```

---

## 3. Exit Criteria Sign-off
Block 3 is considered complete ONLY when all 5 scorecard gates have passed without exception.
