# Block 5 Plan: Async HITL (LongRunningFunctionTool), CERT-In Audit & Cloud Armor Launch

## 1. Objective
Complete the production readiness, auditability, and edge protection of the Sovereign Enterprise AI Assistant:
1. Implement Human-in-the-Loop (HITL) safeguards using ADK 2.6+ `LongRunningFunctionTool` for state-changing write operations (`send_email`, `create_calendar_event`, `zoho_create_lead`).
2. Build an interactive mobile action card (`NativeActionCard.tsx`) rendering pending actions with "Confirm" and "Reject" buttons.
3. Build the webhook resumption endpoint (`backend/src/routes/webhooks.py`) to resume suspended ADK agent runs matching the pending `function_call_id`.
4. Implement an append-only, tamper-resistant `audit_logs` table and ADK `after_agent_callback` (`audit.py`) satisfying CERT-In directions and DPDP compliance (NTP-synchronized timestamp, user ID, action, status).
5. Configure and validate the Cloud Run deployment pipeline in Mumbai (`asia-south1`) protected by Google Cloud Armor WAF and a Serverless Network Endpoint Group (NEG).

---

## 2. Architectural Blueprint

```
+-------------------------------------------------------------+
|                      Internet Traffic                       |
+------------------------------+------------------------------+
                               | HTTPS (Port 443)
                               v
+-------------------------------------------------------------+
|               Google Cloud Armor WAF (Mumbai)               |
|  - OWASP Top 10 Rules, DDoS Shield, Rate-limiting           |
|  - Geo-protection & India IP verification                   |
+------------------------------+------------------------------+
                               | Serverless NEG (asia-south1)
                               v
+-------------------------------------------------------------+
|               FastAPI Server (Google Cloud Run)             |
|  - Non-root user (appuser:10001), Port: 8080                 |
|  - LongRunningFunctionTool: Pauses on write actions         |
|  - POST /webhooks/hitl-resume: Resumes with function_call_id|
|  - after_agent_callback: NTP-synced CERT-In audit logging   |
+------------------------------+------------------------------+
                               | Append-only SQL (Private IP)
                               v
+-------------------------------------------------------------+
|               Cloud SQL public.audit_logs                   |
|  - Strict append-only (RULES prevent UPDATE / DELETE)       |
|  - CERT-In 180-day compliance retention                     |
+-------------------------------------------------------------+
```

---

## 3. Dependency Sequence
1. Audit Schema Migration:
   - `infra/migrations/004_audit.sql` (Creates append-only `audit_logs` table)
2. LongRunningFunctionTool & Webhook Resumption:
   - `backend/src/tools/hitl_tools.py`
   - `backend/src/routes/webhooks.py`
   - `backend/tests/test_hitl_flow.py`
3. Audit Callback:
   - `backend/src/callbacks/audit.py`
   - `backend/tests/test_audit_logging.py`
4. Frontend Action Cards:
   - `frontend/components/tools/NativeActionCard.tsx`
5. Cloud Run & Cloud Armor Infrastructure:
   - `infra/cloudbuild.yaml`
   - `infra/armor/security_policy.yaml`
   - `scripts/verify_deployment.sh` (Health check targeting `asia-south1`)
