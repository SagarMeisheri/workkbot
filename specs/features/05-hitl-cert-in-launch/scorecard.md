# Block 5 Scorecard: Async HITL (LongRunningFunctionTool), CERT-In Audit & Cloud Armor Launch

## 1. Verification Rubric & Exit Gates

| Gate ID | Verification Item | Target | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **B5-G1** | LongRunningFunctionTool HITL Suspension | Write operations suspend execution with `function_call_id` and resume strictly upon `POST /webhooks/hitl-resume` confirmation | Automated workflow test in `backend/tests/test_hitl_flow.py` | [ ] PENDING |
| **B5-G2** | Tamper-Resistant Audit Logging | Every agent interaction writes an immutable row in `audit_logs`; UPDATE and DELETE commands fail or do nothing | SQL immutability test in `backend/tests/test_audit_logging.py` | [ ] PENDING |
| **B5-G3** | Cloud Armor & Serverless NEG Security | Cloud Run service accepts traffic exclusively through the Load Balancer protected by Cloud Armor WAF policies in `asia-south1` | Infrastructure verification script in `scripts/verify_deployment.sh` | [ ] PENDING |
| **B5-G4** | NTP & Timestamp Synchronization | Audit timestamps match UTC/IST time within statutory tolerance limits | Automated timestamp precision checks | [ ] PENDING |
| **B5-G5** | Mobile Interactive Action Card | Action card UI renders params, prompts user, and handles reject/confirm gracefully | Component interaction test in `frontend` | [ ] PENDING |

---

## 2. Automated Test Execution Commands

```bash
# 1. Test LongRunningFunctionTool HITL suspension and resumption
cd backend && pytest -v tests/test_hitl_flow.py

# 2. Test audit logging append-only enforcement
cd backend && pytest -v tests/test_audit_logging.py

# 3. Verify Cloud Run container build & Cloud Armor configuration
./scripts/verify_deployment.sh --dry-run
```

---

## 3. Exit Criteria Sign-off
Block 5 is considered complete ONLY when all 5 scorecard gates have passed without exception.
