# Spec 03: DPDP Compliance, Cloud DLP Indian PII Redaction & Supabase DSR Erasure (The 5-Framework Model)

## 1. Context & Motivation
India's **DPDP Act 2023** imposes heavy liabilities (penalties up to ₹250 Crore) on Data Fiduciaries that fail to implement reasonable security safeguards or ignore Data Subject Requests (DSRs). Concurrently, **Apple App Store Review Guideline 5.1.1** mandates that any app supporting account creation must provide a friction-free, complete in-app account and data deletion mechanism.

Sending raw employee Aadhaar numbers, PAN cards, or financial details to model providers violates data minimization rules. However, destructively replacing PII with static placeholders (`[REDACTED]`) breaks tool execution.

Workkbot resolves this by routing all privacy, redaction, and erasure decisions through the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Stores user consents, executes atomic DSR cascading erasure via PostgreSQL stored procedures, and provides hard-deletion of users via `auth.admin.deleteUser()`.
2. **Google Cloud Platform (GCP `asia-south1`)**: Google Cloud Sensitive Data Protection (Cloud DLP) detecting Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER`), and Cloud Logging for statutory CERT-In incident reporting.
3. **Google ADK 2.0 (`google-adk`)**: Stateful lifecycle callbacks (`before_model`, `before_tool`, `after_tool`) executing reversible in-session tokenization and argument rehydration.
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: Renders inline "PII Protected" visual indicators and powers the in-app self-service DPDP Privacy & Account Deletion Portal.
5. **Agentgateway 1.5.x**: Sanitizes outgoing tool parameters, prevents prompt injection from tool responses, and verifies CEL permissions before tool execution.

### **The North Star: Security & Mobile App Approval**
- **Security**: Complete immunization of LLM prompts against Indian PII leaks; zero residual PII in model caches; atomic cascading deletion of all user records.
- **Mobile App Approval (Apple Guideline 5.1.1 & 5.1.2i)**: Fully functional in-app account deletion that immediately wipes user credentials, chat histories, vector embeddings, and third-party Vault secrets in a single transaction without requiring email or external support.

---

## 2. The 5-Framework Architecture Mapping for Spec 03

| Framework | Core Responsibility in DPDP & Redaction | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | `execute_dsr_erasure()` PostgreSQL RPC; `public.user_consents`; `auth.admin.deleteUser()`. | Complete atomic data purging across tables and `pgvector`; hard deletion meets Apple Guideline 5.1.1. |
| **2. Google Cloud Platform (GCP)** | Cloud Sensitive Data Protection (DLP API in Mumbai); Google Cloud Logging structured audit sinks for CERT-In. | Data stays in `asia-south1`; CERT-In incident logs retain 7-year immutable retention via BigQuery export. |
| **3. Google ADK 2.0** | `before_model` (PII tokenization), `before_tool` (PII rehydration), and `after_tool` (output masking) callbacks. | Reversible in-session tokenization prevents model from seeing raw PII while preserving tool execution accuracy. |
| **4. assistant-ui** | Visual PII redaction badges in message parts; in-app Privacy Portal with one-click **[Delete Account & Purge Data]** button. | Seamless web and mobile native (`@assistant-ui/react-native`) rendering; fulfills Apple 5.1.1 and 5.1.2i requirements. |
| **5. Agentgateway 1.5.x** | Parameter sanitization and CEL policy evaluation on rehydrated tool calls; downstream response filtering. | Blocks parameter injection (CVE-2026-29791) and prevents sensitive leaks in upstream tool failures. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
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
* `apps/web/src/app/settings/privacy/page.tsx`: Employee Privacy & DPDP DSR portal.
* `apps/mobile/src/screens/PrivacyScreen.tsx`: Native mobile privacy and account deletion interface.

---

## 4. Requirements & Implementation Details

### R03.1: The Reversible Tokenization & Tool Rehydration Lifecycle
```text
[1. User Input in assistant-ui]
  "Send invoice to Rahul at rahul@acme.in with PAN ABCDE1234F"
                     │
                     ▼
[2. Cloud DLP / Presidio + In-Session PII Vault (GCP + ADK before_model)]
  • Detects: Rahul -> <PERSON_1>, rahul@acme.in -> <EMAIL_1>, ABCDE1234F -> <IN_PAN_1>
  • Stores in Ephemeral Vault: { "<EMAIL_1>": "rahul@acme.in", "<IN_PAN_1>": "ABCDE1234F" }
                     │
                     ▼ (Sanitized Prompt to Vertex AI via Agentgateway)
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
                     ▼ (Dispatched to Agentgateway 1.5.x Loopback :8080/mcp)
[5. Agentgateway Federated Proxy & Parameter Sanitization]
  • Evaluates CEL policy & sanitizes parameters (CVE-2026-29791)
  • Injects Supabase Vault OAuth bearer token for upstream service
  • Executes tool on target provider (Zoho Books / Google Workspace)
  • Returns response: {"status": "success", "invoice_id": "INV-101", "sent_to": "rahul@acme.in"}
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
[8. Rendered in assistant-ui (Web / Mobile)]
  "I have successfully sent invoice INV-101 to Rahul at rahul@acme.in."
```

### R03.2: Two-Tier Indian PII Engine (Regex Fast-Path + Cloud DLP)
1. **Tier 1 (Zero-Latency Local Fast-Path via Presidio)**:
   - **Indian Aadhaar**: 12-digit pattern validated via Verhoeff checksum algorithm.
   - **Indian PAN**: Regex `\b[A-Z]{5}[0-9]{4}[A-Z]\b`.
   - **UPI VPA**: Regex `\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b`.
   - **Indian Mobile**: Regex `\b(?:\+91|91|0)?[6-9]\d{9}\b`.
2. **Tier 2 (Google Cloud Sensitive Data Protection API)**:
   - Executes asynchronously for unstructured document scans using `INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER` infoTypes in Mumbai (`asia-south1`).

### R03.3: Statutory Right to Erasure & Account Deletion (Apple Guideline 5.1.1 Compliance)
- Stored procedure in Supabase:
  ```sql
  CREATE OR REPLACE FUNCTION execute_dsr_erasure(target_user_id UUID, executing_org_id UUID)
  RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER AS $$
  BEGIN
    -- 1. Hard-delete episodic ADK sessions and events
    DELETE FROM public.sessions WHERE user_id = target_user_id AND org_id = executing_org_id;
    DELETE FROM public.conversations WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    -- 2. Hard-delete semantic memory and vectors
    DELETE FROM public.memory_items WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    -- 3. Delete connected MCP tokens from Supabase Vault
    DELETE FROM public.mcp_connections WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    -- 4. Pseudonymize tool audit logs (retain compliance counts, scrub PII)
    UPDATE public.tool_invocations
    SET user_id = NULL,
        arguments = '{"redacted": "DSR_ERASURE_APPLIED"}'::jsonb,
        result = '{"redacted": "DSR_ERASURE_APPLIED"}'::jsonb
    WHERE user_id = target_user_id AND org_id = executing_org_id;
    
    RETURN jsonb_build_object('status', 'success', 'user_id', target_user_id);
  END;
  $$;
  ```
- When initiated via the in-app **[Delete Account & Purge Data]** button in assistant-ui, `dsr_service.py` executes `execute_dsr_erasure()` and then calls `supabase.auth.admin.delete_user(target_user_id)`, guaranteeing zero residual data and 100% Apple Guideline 5.1.1 compliance.

---

## 5. Validation Scorecard & Execution Target

### **Execution Target**: `Localhost (Zero-Mock)`
- **Environment**: Next.js 15 (`localhost:3000`) and FastAPI (`localhost:8000`) on developer machine.
- **Live Cloud Boundaries**:
  - Live Google Cloud Sensitive Data Protection (DLP API in `asia-south1`) via Google Application Default Credentials (`gcloud auth application-default login`).
  - Live Supabase Mumbai (`ap-south-1`) executing `execute_dsr_erasure()` and `client.auth.admin.delete_user()`.
  - Live Google Cloud Logging sink for CERT-In compliant security events. No mock PII or synthetic deletions permitted.

---

### **Tier 1: Unit & Contract Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-03.1** | Presidio Tier-1 fast-path: Indian Aadhaar (Verhoeff checksum) and PAN regex redact accurately | `uv run pytest apps/backend/tests/test_pii_fast_path.py` | [ ] |
| **VAL-03.2** | Reversible tokenization: `<EMAIL_1>` and `<IN_PAN_1>` map to ephemeral session vault | `uv run pytest apps/backend/tests/test_pii_vault_lifecycle.py` | [ ] |
| **VAL-03.3** | Tool rehydration: ADK `before_tool` replaces tokens with real PII before tool dispatch | `uv run pytest apps/backend/tests/test_tool_rehydration.py` | [ ] |
| **VAL-03.4** | Tool output masking: ADK `after_tool` redacts newly returned PII before re-entering LLM context | `uv run pytest apps/backend/tests/test_tool_output_masking.py` | [ ] |

### **Tier 2: Zero-Mock Live Integration Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-03.5** | Live Google Cloud DLP API in `asia-south1` detects Indian Aadhaar, PAN, and GST numbers | `uv run pytest -m live_dlp apps/backend/tests/test_live_cloud_dlp.py` | [ ] |
| **VAL-03.6** | Live Supabase `execute_dsr_erasure()` RPC purges sessions, events, memory, and anonymizes audit records | `uv run pytest apps/backend/tests/test_dsr_erasure_cascade.py` | [ ] |
| **VAL-03.7** | Backend `/api/v1/account/delete` atomically deletes live Supabase Auth user & Vault secrets (Apple 5.1.1) | `uv run pytest apps/backend/tests/test_in_app_account_erasure.py` | [ ] |
| **VAL-03.8** | Security events write CERT-In compliant structured JSON to live Google Cloud Logging | `uv run pytest -m live_gcp apps/backend/tests/test_cert_in_logging.py` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-03.9** | Chat stream renders rehydrated text to user (e.g. Rahul, PAN), never displaying raw tokens like `<IN_PAN_1>` | `pnpm --filter @workkbot/web test:e2e tests/e2e/chat-pii-rehydration.spec.ts` | [ ] |
| **VAL-03.10** | Employee Privacy portal (`/settings/privacy`) displays DPDP statutory notices and DSR export buttons | `pnpm --filter @workkbot/web test:e2e tests/e2e/privacy-settings.spec.ts` | [ ] |
| **VAL-03.11** | Clicking **[Delete Account & Purge Data]** opens confirmation modal and redirects to `/login` | `pnpm --filter @workkbot/web test:e2e tests/e2e/account-deletion-ui.spec.ts` | [ ] |

### **Tier 4: Manual Verification Protocol**
1. **Chat PII Rehydration**: In `http://localhost:3000/chat`, prompt: *"Rahul's PAN is ABCDE1234F. Remind him to file taxes."* Verify assistant response addresses Rahul by name and refers to his PAN naturally. In backend terminal logs, verify prompt sent to Vertex AI was sanitized to `<PERSON_1>` and `<IN_PAN_1>`.
2. **DSR Data Export**: Navigate to `http://localhost:3000/settings/privacy`. Click **"Download My Data (JSON)"**. Open downloaded zip file and confirm all past conversations, consents, and connected providers are included in clean JSON format.
3. **In-App Account & Memory Purge (Apple 5.1.1)**: On the privacy page, click **[Delete Account & Purge Data]**. Type "DELETE" into the safety input and click Confirm. Verify immediate redirection to `/login`. In live Supabase SQL editor, execute:
   ```sql
   SELECT * FROM auth.users WHERE email = '<your_email>';
   SELECT * FROM public.profiles WHERE email = '<your_email>';
   ```
   Confirm zero records remain across all tables.

