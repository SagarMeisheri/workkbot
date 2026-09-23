# Block 2 Scorecard: ADK 2.0 Lifecycle Callbacks, ZDR Gemini & Expo Chat UI

## 1. Verification Rubric & Exit Gates

| Gate ID | Verification Item | Target | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **B2-G1** | Zero PII Leakage to Vertex AI | Network payload interceptor proves raw Aadhaar, PAN, phone number, and email never reach Vertex AI | Mock network assertion in `backend/tests/test_pii_scrubber.py` | [ ] PENDING |
| **B2-G2** | Bidirectional Pseudonym Rehydration | Model response containing `{{PSEUDO_...}}` tokens is rehydrated to original values prior to client stream | Integration test in `backend/tests/test_pii_rehydration.py` | [ ] PENDING |
| **B2-G3** | DPDP Consent Gate Enforcement | Unconsented chat requests fail at `before_agent` with HTTP 403 / Consent Required challenge | API test in `backend/tests/test_consent_gate.py` | [ ] PENDING |
| **B2-G4** | ZDR Vertex AI Client Sovereign Pinning | Client config sets endpoint `asia-south1-aiplatform.googleapis.com` and disables context caching | Configuration inspection test in `backend/tests/test_vertex_client.py` | [ ] PENDING |
| **B2-G5** | Assistant UI SSE Streaming | Expo client receives and renders incremental text tokens via SSE stream | End-to-end integration test with SSE consumer | [ ] PENDING |

---

## 2. Automated Test Execution Commands

```bash
# 1. Test PII scrubber scrubbing and rehydration
cd backend && pytest -v tests/test_pii_scrubber.py tests/test_pii_rehydration.py

# 2. Test Consent Gate blocking
cd backend && pytest -v tests/test_consent_gate.py

# 3. Test Vertex AI client configuration
cd backend && pytest -v tests/test_vertex_client.py

# 4. Test SSE Chat Streaming
cd backend && pytest -v tests/test_chat_route.py
```

---

## 3. Exit Criteria Sign-off
Block 2 is considered complete ONLY when all 5 scorecard gates have passed without exception.
