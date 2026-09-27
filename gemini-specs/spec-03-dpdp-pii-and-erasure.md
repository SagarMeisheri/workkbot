# Spec 03: DPDP Compliance, Indian PII Redaction & Supabase DSR Erasure Engine

## 1. Context & Motivation
India's **DPDP Act 2023** imposes heavy liabilities (penalties up to ₹250 Crore) on Data Fiduciaries that fail to implement reasonable security safeguards or ignore Data Subject Requests (DSRs). 
Sending raw employee Aadhaar numbers, PAN cards, or financial details to third-party model providers violates data minimization rules. 
This spec establishes real-time Indian PII masking and an automated Right to Erasure engine integrated with **Supabase Auth and PostgreSQL cascading deletes**.

## 2. Objective & Non-Goals
- **Objective**: Redact Indian sensitive identifiers before dispatch to models; provide an automated DSR pipeline to permanently purge employee data across Supabase Auth, conversation sessions, and vector stores; enforce Indian data residency.
- **Non-Goals**: No manual email-driven deletion workflows. All erasure requests execute through verified API commands.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/compliance/`
  * `pii_masker.py`: High-speed regex and algorithmic maskers for Indian PII.
  * `callbacks/redaction_callback.py`: ADK `before_model` callback intercepting prompts.
  * `dsr_service.py`: Automated Data Subject Request (DSR) erasure and export pipeline using Supabase Admin client.
  * `cert_in_logger.py`: Security event logging formatted for CERT-In incident reporting.
* `supabase/migrations/20260927000003_dsr_erasure.sql`:
  * PostgreSQL RPC function `execute_dsr_erasure(target_user_id UUID, executing_org_id UUID)` that atomically cascades deletion across sessions, events, memory items, and pseudonymizes audit records.
* `apps/web/src/app/settings/privacy/`: Employee Privacy & DPDP DSR portal.

---

## 4. Requirements & Implementation Details

### R03.1: Real-Time Indian PII Redaction (`before_model` Callback)
- The ADK `before_model` callback intercepts user messages and tool outputs before they leave the application boundary.
- **Redaction Rules**:
  1. **Aadhaar Numbers**: Identifies 12-digit patterns validated via the Verhoeff algorithm. Replaced with `[AADHAAR_REDACTED]`.
  2. **Permanent Account Numbers (PAN)**: Identifies standard 10-character alphanumeric PAN format (`[A-Z]{5}[0-9]{4}[A-Z]`). Replaced with `[PAN_REDACTED]`.
  3. **UPI Virtual Payment Addresses**: Identifies patterns like `username@bank` or `mobile@upi`. Replaced with `[UPI_REDACTED]`.
  4. **Indian Mobile Numbers**: Identifies `+91` or 10-digit mobile series starting with 6, 7, 8, or 9. Replaced with `[PHONE_REDACTED]`.
- Redaction metadata (type, timestamp, redaction count) is recorded locally without storing the original sensitive string.

### R03.2: Statutory Right to Erasure via Supabase RPC (DPDP Act Sec 12)
- When an employee initiates a deletion request or is deprovisioned by an admin:
  1. Calls Supabase PostgreSQL stored procedure `execute_dsr_erasure(target_user_id, org_id)`:
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
  2. If the user is deleting their entire account (Apple Guideline 5.1.1(v) & DPDP), `dsr_service.py` calls `supabase.auth.admin.delete_user(target_user_id)` to purge credentials and revoke all active sessions.
  3. Generates a signed, verifiable DSR completion receipt.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-03.1** | Prompt containing Aadhaar, PAN, and UPI has all three masked before model call | Unit test on `pii_masker.py` and `redaction_callback.py` | [ ] |
| **VAL-03.2** | Executing Supabase DSR RPC completely purges user chat logs and vector embeddings | Execute `execute_dsr_erasure`; assert zero records in `sessions` and `memory_items` | [ ] |
| **VAL-03.3** | `tool_invocations` audit log is pseudonymized and unlinked from user identity | Assert `user_id` is null and payloads scrubbed in `tool_invocations` | [ ] |
| **VAL-03.4** | Calling `supabase.auth.admin.delete_user` removes user from `auth.users` | Verify user deleted via Supabase Admin API | [ ] |
