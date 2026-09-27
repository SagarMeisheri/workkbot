# Spec 03: DPDP Compliance, Cloud DLP Indian PII Redaction & Supabase DSR Erasure (GCP Day 1)

## 1. Context & Motivation
India's **DPDP Act 2023** imposes heavy liabilities (penalties up to ₹250 Crore) on Data Fiduciaries that fail to implement reasonable security safeguards or ignore Data Subject Requests (DSRs). 
Sending raw employee Aadhaar numbers, PAN cards, or financial details to third-party model providers violates data minimization rules.

### The Tool Calling Dilemma:
If PII is destructively masked with static placeholders (e.g. `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`), the LLM cannot execute tools:
- User prompt: *"Send an invoice to customer Rahul at rahul@acme.in with PAN ABCDE1234F"*.
- If masked to: *"Send an invoice to customer [NAME_REDACTED] at [EMAIL_REDACTED] with PAN [PAN_REDACTED]"*, the model attempts to call `send_invoice(email="[EMAIL_REDACTED]", pan="[PAN_REDACTED]")`, failing execution.

This spec solves this on **Google Cloud (`asia-south1`)** using **Google Cloud Sensitive Data Protection (Cloud DLP) & Microsoft Presidio** with **Reversible In-Session Tokenization & Tool Argument Rehydration**. The LLM never sees real PII, but connected tools execute with 100% precision.

## 2. Objective & Non-Goals
- **Objective**: Use Google Cloud DLP and Microsoft Presidio to detect standard and Indian PII (Aadhaar, PAN, UPI, mobile); replace PII with deterministic in-session entity tokens (`<EMAIL_1>`, `<IN_PAN_1>`); rehydrate tool arguments in `before_tool` callbacks before MCP dispatch; enforce statutory DSR erasure across Supabase Auth, DB, and vectors; stream security events to Google Cloud Logging for CERT-In incident readiness.
- **Non-Goals**: No persistent storage of raw PII in model logs. Token vault mappings are short-lived and discarded after session turn completion.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/compliance/`
  * `dlp_engine.py`: Google Cloud Sensitive Data Protection (DLP API) client inspecting Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER`).
  * `presidio_engine.py`: Microsoft Presidio `AnalyzerEngine` with custom regex recognizers for UPI and Verhoeff-checksummed Aadhaar for zero-latency local fast-path filtering.
  * `session_pii_vault.py`: In-memory, ephemeral key-value vault mapping token IDs (`<EMAIL_1>`) to original sensitive strings for the active session.
  * `callbacks/`
    * `pii_anonymize_callback.py`: ADK `before_model` callback scanning prompt and replacing PII with reversible tokens.
    * `tool_rehydration_callback.py`: ADK `before_tool` callback intercepting tool arguments and restoring original PII before calling MCP servers.
    * `tool_output_mask_callback.py`: ADK `after_tool` callback masking any new PII returned in tool outputs before re-entering LLM context.
  * `dsr_service.py`: Automated Data Subject Request (DSR) erasure and export pipeline using Supabase Admin client.
  * `cert_in_logger.py`: Security event logging formatted for CERT-In incident reporting to Google Cloud Logging.
* `supabase/migrations/20260927000003_dsr_erasure.sql`:
  * PostgreSQL RPC function `execute_dsr_erasure(target_user_id UUID, executing_org_id UUID)` that atomically cascades deletion across sessions, events, memory items, and pseudonymizes audit records.
* `apps/web/src/app/settings/privacy/`: Employee Privacy & DPDP DSR portal.

---

## 4. Requirements & Implementation Details

### R03.1: The Reversible Tokenization & Tool Rehydration Lifecycle on Cloud Run

```
[1. User Input in Chat]
  "Send invoice to Rahul at rahul@acme.in with PAN ABCDE1234F"
                     │
                     ▼
[2. Cloud DLP / Presidio + In-Session PII Vault]
  • Detects: Rahul -> <PERSON_1>, rahul@acme.in -> <EMAIL_1>, ABCDE1234F -> <IN_PAN_1>
  • Stores in Ephemeral Vault: { "<EMAIL_1>": "rahul@acme.in", "<IN_PAN_1>": "ABCDE1234F", ... }
                     │
                     ▼ (Sanitized Prompt to Vertex AI)
  "Send invoice to <PERSON_1> at <EMAIL_1> with PAN <IN_PAN_1>"
                     │
                     ▼
[3. Vertex AI Reasoning & Tool Call Generation]
  Emits: send_invoice(recipient="<EMAIL_1>", tax_id="<IN_PAN_1>")
                     │
                     ▼ (Intercepted by ADK before_tool hook)
[4. Tool Argument Rehydration Callback]
  • Replaces <EMAIL_1> with "rahul@acme.in"
  • Replaces <IN_PAN_1> with "ABCDE1234F"
                     │
                     ▼ (Dispatched to MCP Server)
[5. Real Tool Execution on Connected Service (e.g. Zoho/Gmail)]
  send_invoice(recipient="rahul@acme.in", tax_id="ABCDE1234F")
                     │
                     ▼ (Tool Response)
  {"status": "success", "invoice_id": "INV-101", "sent_to": "rahul@acme.in"}
                     │
                     ▼ (Intercepted by ADK after_tool hook)
[6. Tool Output Masking Callback]
  Replaces "rahul@acme.in" -> <EMAIL_1> before re-entering LLM context
                     │
                     ▼
[7. Vertex AI Generates Final Completion]
  "I have successfully sent invoice INV-101 to <PERSON_1> at <EMAIL_1>."
                     │
                     ▼ (SSE Stream Rehydration)
[8. Rendered in Web/Mobile Chat UI]
  "I have successfully sent invoice INV-101 to Rahul at rahul@acme.in."
```

### R03.2: Two-Tier Indian PII Engine (Regex Fast-Path + Cloud DLP)
1. **Tier 1 (Zero-Latency Local Fast-Path via Presidio)**:
   - **Indian Aadhaar**: 12-digit pattern `\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b` validated via the Verhoeff checksum algorithm.
   - **Indian PAN**: Regex `\b[A-Z]{5}[0-9]{4}[A-Z]\b`.
   - **UPI Virtual Payment Address**: Regex `\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b`.
   - **Indian Mobile Series**: Regex `\b(?:\+91|91|0)?[6-9]\d{9}\b`.
2. **Tier 2 (Google Cloud Sensitive Data Protection API)**:
   - Executes asynchronously for unstructured document scans using `INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER` infoTypes located in Mumbai (`asia-south1`).

### R03.3: Statutory Right to Erasure via Supabase RPC (DPDP Act Sec 12)
- Calls Supabase PostgreSQL stored procedure `execute_dsr_erasure(target_user_id, org_id)`:
  ```sql
  CREATE OR REPLACE FUNCTION execute_dsr_erasure(target_user_id UUID, executing_org_id UUID)
  RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER AS $$
  BEGIN
    -- 1. Hard-delete episodic ADK sessions and events
    DELETE FROM public.sessions WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.conversations WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    -- 2. Hard-delete semantic memory and vectors
    DELETE FROM public.memory_items WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    -- 3. Pseudonymize tool audit logs (retain compliance counts, scrub PII)
    UPDATE public.tool_invocations
    SET user_id = NULL,
        arguments = '{"redacted": "DSR_ERASURE_APPLIED"}'::jsonb,
        result = '{"redacted": "DSR_ERASURE_APPLIED"}'::jsonb
    WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    RETURN jsonb_build_object('status', 'success', 'user_id', target_user_id);
  END;
  $$;
  ```
- If deleting account (Apple 5.1.1(v) & DPDP), `dsr_service.py` calls `supabase.auth.admin.delete_user(target_user_id)`.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-03.1** | Prompt containing Email, PAN, and Aadhaar replaces PII with tokens before reaching Vertex AI | `pytest apps/backend/tests/test_pii_redaction.py` | [ ] |
| **VAL-03.2** | Tool call emitted with tokens (`<EMAIL_1>`) is rehydrated to real email before tool executes | `pytest apps/backend/tests/test_tool_rehydration.py` | [ ] |
| **VAL-03.3** | Tool output containing sensitive PII is masked before re-entering LLM context | `pytest apps/backend/tests/test_tool_output_masking.py` | [ ] |
| **VAL-03.4** | Executing Supabase DSR RPC completely purges user chat logs and vector embeddings | `pytest apps/backend/tests/test_dsr_erasure_cascade.py` | [ ] |
| **VAL-03.5** | `tool_invocations` audit log is pseudonymized and unlinked from user identity | `pytest apps/backend/tests/test_audit_pseudonymization.py` | [ ] |
| **VAL-03.6** | Security events write CERT-In compliant JSON payloads to Google Cloud Logging | `pytest apps/backend/tests/test_cert_in_logging.py` | [ ] |
