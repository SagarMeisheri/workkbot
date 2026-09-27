# Spec 03: DPDP Compliance, Microsoft Presidio Reversible Tokenization & Supabase DSR Erasure

## 1. Context & Motivation
India's **DPDP Act 2023** imposes heavy liabilities (penalties up to ₹250 Crore) on Data Fiduciaries that fail to implement reasonable security safeguards or ignore Data Subject Requests (DSRs). 
Sending raw employee Aadhaar numbers, PAN cards, or financial details to third-party model providers violates data minimization rules.

### The Tool Calling Dilemma:
If PII is destructively masked with static placeholders (e.g. `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`), the LLM cannot execute tools! For example:
- User prompt: *"Send an invoice to customer Rahul at rahul@acme.in with PAN ABCDE1234F"*.
- If masked to: *"Send an invoice to customer [NAME_REDACTED] at [EMAIL_REDACTED] with PAN [PAN_REDACTED]"*.
- The model will attempt to call the tool: `send_invoice(email="[EMAIL_REDACTED]", pan="[PAN_REDACTED]")`, causing the tool to crash or fail.

This spec solves this with **Microsoft Presidio** using **Reversible In-Session Tokenization & Tool Argument Rehydration**. The LLM never sees real PII, but connected tools execute with 100% precision.

## 2. Objective & Non-Goals
- **Objective**: Use Microsoft Presidio to detect standard and Indian PII (Aadhaar, PAN, UPI, mobile); replace PII with deterministic in-session entity tokens (`<EMAIL_1>`, `<IN_PAN_1>`); rehydrate tool arguments in `before_tool` callbacks before MCP dispatch; enforce statutory DSR erasure across Supabase Auth, DB, and vectors.
- **Non-Goals**: No persistent storage of raw PII in model logs. Token vault mappings are short-lived and discarded after session turn completion.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/compliance/`
  * `presidio_engine.py`: Configures Microsoft Presidio `AnalyzerEngine` and `AnonymizerEngine` with custom Indian recognizers (Aadhaar with Verhoeff check, PAN, UPI, Indian mobile).
  * `session_pii_vault.py`: In-memory, ephemeral key-value vault mapping token IDs (`<EMAIL_1>`) to original sensitive strings for the active session.
  * `callbacks/`
    * `pii_anonymize_callback.py`: ADK `before_model` callback scanning prompt and replacing PII with reversible tokens.
    * `tool_rehydration_callback.py`: ADK `before_tool` callback intercepting tool arguments and restoring original PII before calling MCP servers.
    * `tool_output_mask_callback.py`: ADK `after_tool` callback masking any new PII returned in tool outputs before re-entering LLM context.
  * `dsr_service.py`: Automated Data Subject Request (DSR) erasure and export pipeline using Supabase Admin client.
  * `cert_in_logger.py`: Security event logging formatted for CERT-In incident reporting.
* `supabase/migrations/20260927000003_dsr_erasure.sql`:
  * PostgreSQL RPC function `execute_dsr_erasure(target_user_id UUID, executing_org_id UUID)` that atomically cascades deletion across sessions, events, memory items, and pseudonymizes audit records.
* `apps/web/src/app/settings/privacy/`: Employee Privacy & DPDP DSR portal.

---

## 4. Requirements & Implementation Details

### R03.1: The Reversible Presidio Tokenization & Tool Rehydration Lifecycle

```
[1. User Input in Chat]
  "Send invoice to Rahul at rahul@acme.in with PAN ABCDE1234F"
                     │
                     ▼
[2. Presidio Analyzer + In-Session PII Vault]
  • Detects: Rahul -> <PERSON_1>, rahul@acme.in -> <EMAIL_1>, ABCDE1234F -> <IN_PAN_1>
  • Stores in Ephemeral Vault: { "<EMAIL_1>": "rahul@acme.in", "<IN_PAN_1>": "ABCDE1234F", ... }
                     │
                     ▼ (Sanitized Prompt to LLM)
  "Send invoice to <PERSON_1> at <EMAIL_1> with PAN <IN_PAN_1>"
                     │
                     ▼
[3. LLM Reasoning & Tool Call Generation]
  Emits: send_invoice(recipient="<EMAIL_1>", tax_id="<IN_PAN_1>")
                     │
                     ▼ (Intercepted by ADK before_tool hook)
[4. Tool Argument Rehydration Callback]
  • Replaces <EMAIL_1> with "rahul@acme.in"
  • Replaces <IN_PAN_1> with "ABCDE1234F"
                     │
                     ▼ (Dispatched to MCP Server)
[5. Real Tool Execution on Connected Service (e.g. Zoho/Gmail/Stripe)]
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
[7. LLM Generates Final Completion]
  "I have successfully sent invoice INV-101 to <PERSON_1> at <EMAIL_1>."
                     │
                     ▼ (SSE Stream Rehydration)
[8. Rendered in Web/Mobile Chat UI]
  "I have successfully sent invoice INV-101 to Rahul at rahul@acme.in."
```

### R03.2: Custom Indian PII Recognizers for Microsoft Presidio
`presidio_engine.py` registers custom `PatternRecognizer` instances:
1. **Indian Aadhaar**: 12-digit pattern `\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b` validated via the Verhoeff checksum algorithm. Tagged as `IN_AADHAAR`.
2. **Indian PAN**: Regex `\b[A-Z]{5}[0-9]{4}[A-Z]\b`. Tagged as `IN_PAN`.
3. **UPI Virtual Payment Address**: Regex `\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b`. Tagged as `IN_UPI`.
4. **Indian Mobile Series**: Regex `\b(?:\+91|91|0)?[6-9]\d{9}\b`. Tagged as `IN_PHONE`.
5. Built-in Presidio recognizers for `EMAIL_ADDRESS`, `CREDIT_CARD`, `IBAN_CODE`, `PERSON`, `LOCATION`.

### R03.3: In-Session Ephemeral PII Vault (`session_pii_vault.py`)
- Mappings are scoped strictly to the current request and conversation ID:
  ```python
  class SessionPIIVault:
      def __init__(self):
          self._vault: dict[str, str] = {} # token -> original_value
          self._reverse_vault: dict[str, str] = {} # original_value -> token
      
      def tokenize(self, entity_type: str, original_val: str) -> str: ...
      def rehydrate(self, text_or_dict: Any) -> Any: ...
  ```
- Memory lifecycle:
  - Preserved in memory during multi-step tool calling within the active turn.
  - Flushed from active memory upon turn completion.
  - The model provider's servers **never receive the real PII**, satisfying data minimization under DPDP Sec 8(5).

### R03.4: Statutory Right to Erasure via Supabase RPC (DPDP Act Sec 12)
- When an employee initiates an erasure request or is deprovisioned:
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
| **VAL-03.1** | Prompt containing Email, PAN, and Aadhaar replaces PII with tokens before reaching model | Inspect raw prompt received by LLM mock | [ ] |
| **VAL-03.2** | Tool call emitted by model with tokens (`<EMAIL_1>`) is rehydrated to real email before tool executes | Inspect arguments dispatched to mock MCP tool | [ ] |
| **VAL-03.3** | Tool output containing sensitive PII is masked before re-entering LLM context | Verify tool response payload fed to model turn | [ ] |
| **VAL-03.4** | Executing Supabase DSR RPC completely purges user chat logs and vector embeddings | Execute `execute_dsr_erasure`; assert zero records in `sessions` and `memory_items` | [ ] |
| **VAL-03.5** | `tool_invocations` audit log is pseudonymized and unlinked from user identity | Assert `user_id` is null and payloads scrubbed in `tool_invocations` | [ ] |
| **VAL-03.6** | Calling `supabase.auth.admin.delete_user` removes user from `auth.users` | Verify user deleted via Supabase Admin API | [ ] |
