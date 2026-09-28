# Spec: 5-Framework Live Integration Mandate & Zero-Mock Architecture Law

> **Workkbot 2.0 Engineering Constitution & Non-Negotiable System Law**  
> *Target Audience: Autonomous AI Coding Agents & Engineers (Antigravity, Cursor, Windsurf, Claude Code).*  
> *Applicability: Mandatory across all specifications (`spec-00` through `spec-10`, `spec-ui-canonical-workspace`, and all future additions).*  
> *Last Verified: 2026-09-28.*

---

## 1. Context & The Zero-Mock Law

A core vulnerability in AI-driven software development is "mock drift" — where features appear functional in development due to synthetic in-memory dictionaries, mocked databases, and simulated LLM replies, only to fail completely when exposed to real-world cloud network topologies, authentication handshakes, and third-party rate limits.

In Workkbot 2.0, **mock data, in-memory stubs (`_local_db`, `_local_vault`), hardcoded session states, and synthetic test fixtures are STRICTLY FORBIDDEN**.

Every feature, pull request, and validation check **MUST** be implemented and tested against **live frameworks** from the moment code is written:
1. **Never test as an afterthought**: Live integration is not a deployment-phase task; it is the entry requirement for writing line one of code for every spec.
2. **Zero In-Memory Fallbacks in Production Code**: Storing user profiles, sessions, or tokens in Python module dictionaries or browser `localStorage` is an immediate architectural rejection.
3. **Real Cloud Topologies**: All traffic must route through the real 5 Frameworks running in **Mumbai (`ap-south-1` / `asia-south1`)**.

---

## 2. The 5-Framework Live Boundary Definition

Every specification in Workkbot 2.0 routes through the **5 Core Frameworks**. Below are the mandatory live boundaries that cannot be substituted with mocks:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THE 5 CORE LIVE BOUNDARIES                             │
├────────────────────────┬───────────────────────────────────────────────────────────────┤
│ 1. Supabase            │ • Live GoTrue Auth (Google Workspace OAuth + Reviewer Demo)   │
│    (Mumbai ap-south-1) │ • Live PostgreSQL 16 DDL with Row-Level Security (RLS)        │
│                        │ • Live Supabase Vault (pgsodium) hardware encryption          │
│                        │ • Live pgvector (0.8.0) HNSW cosine similarity (<=>)          │
│                        │ • Live Supabase Realtime (postgres_changes & Broadcast)       │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 2. Google Cloud        │ • Live Cloud Run Multi-Container Pod (FastAPI + Agentgateway) │
│    Platform (GCP       │ • Live Cloud Armor WAF with Indian geofencing (origin: 'IN')  │
│    asia-south1)        │ • Direct VPC Egress blocking link-local metadata (169.254...) │
│                        │ • Live Vertex AI Gemini 2.0 Flash/Pro & text-embedding-004    │
│                        │ • Live Cloud Sensitive Data Protection (DLP) API (Indian PII) │
│                        │ • Live Google Cloud Storage (GCS) with V4 Signed URLs         │
│                        │ • Live Google Cloud Logging & BigQuery 7-Year Audit Sink      │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 3. Google ADK 2.0      │ • Live In-Process Python Runner & LlmAgent(name="workkbot")   │
│    (google-adk)        │ • Live DatabaseSessionService connected to Supabase Postgres  │
│                        │ • Live McpToolset connected to loopback :8080/mcp             │
│                        │ • Live lifecycle hooks (before_model, before_tool, after_tool)│
│                        │ • Live ToolContext.request_confirmation() for in-stream pauses│
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 4. assistant-ui        │ • Live Next.js 15 SSR & Expo SDK 52 Native mobile surfaces    │
│    (@assistant-ui)     │ • Live HTTP/2 SSE streaming via @assistant-ui/react-google-adk│
│                        │ • Live ThreadListSidebar bound to Supabase conversations      │
│                        │ • Live BranchPickerPrimitive mapped to ADK event checkpoints  │
│                        │ • Live in-chat ApprovalCard (useAdkToolConfirmations)         │
│                        │ • Live ActionBarPrimitive with Apple 1.2 Flag/Report Modal    │
├────────────────────────┼───────────────────────────────────────────────────────────────┤
│ 5. Agentgateway 1.5.x  │ • Live Rust daemon running on loopback 127.0.0.1:8080         │
│    (Rust)              │ • Live MCP Federation proxy (127.0.0.1:8080/mcp)              │
│                        │ • Live OpenAPI-to-MCP dynamic virtualization                  │
│                        │ • Live anti-tool poisoning & anti-shadowing filters           │
│                        │ • Live Common Expression Language (CEL) policy enforcement    │
│                        │ • Live Vertex AI LLM proxy with circuit-breaker failover      │
└────────────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## 3. Spec-by-Spec Live Integration Guidelines & Requirements

Every spec in `gemini-specs/` must reference this document and satisfy the following live criteria:

### Spec 00: Constitution, Multi-Container Cloud Run & 5-Framework Monorepo
* **Live Integration Requirement**:
  * Live Supabase project provisioned in Mumbai (`ap-south-1`).
  * Cloud Run multi-container pod definition running FastAPI (port 8000) and Agentgateway (port 8080).
  * Direct VPC Egress firewall rules deployed, actively rejecting `169.254.169.254`.
* **Prohibited Mocks**: Mocking container ports, mock gateway endpoints, or mock project URLs.
* **Live Test**: Deploy baseline container to Cloud Run and verify `/healthz` and loopback communication.

### Spec 01: Enterprise Identity, Connectors Hub & DPDP Consent
* **Live Integration Requirement**:
  * Live Supabase GoTrue Auth handling Google Workspace OAuth code exchanges.
  * Live domain whitelist database hook (`handle_new_user()`) rejecting non-whitelisted emails via PostgreSQL exception.
  * Live Supabase Vault (`pgsodium`) storing encrypted OAuth tokens (`vault.create_secret()`).
  * Live DPDP statutory consent records written to `public.user_consents`.
  * Dedicated reviewer account (`apple-reviewer@workkbot.in`) provisioned in Supabase Auth bound to demo org (`e0000000-0000-0000-0000-000000000002`).
* **Prohibited Mocks**: `_local_db["organizations"]`, `_local_vault`, synthetic JWT tokens generated without Supabase secret, `localStorage.getItem("workkbot_auth")`.
* **Live Test**: Real OAuth redirect to Google, real Supabase JWT signature verification, real Vault secret insertion and decryption.

### Spec UI: Canonical Assistant-UI Workspace, Floating Composer & Action Popover
* **Live Integration Requirement**:
  * Real Next.js 15 client wired to `supabase.auth.onAuthStateChange` via `@supabase/ssr`.
  * Real profile greeting: `public.profiles` query returning employee's first name for `"✳ Back at it, [name]"`.
  * Real token attachment: `Authorization: Bearer <session.access_token>` forwarded to all backend endpoints.
  * Real Apple Guideline 1.2 Flag Modal writing to `public.ai_content_reports`.
* **Prohibited Mocks**: Hardcoded `"sagar"` greeting without DB lookup; mock thread arrays in React state without Supabase sync.
* **Live Test**: Sign in with real account -> verify header updates to real user metadata.

### Spec 02: Core Chat on Google ADK 2.0 & Cloud Run Streaming
* **Live Integration Requirement**:
  * Live `google-adk` Python Runner executing in-process.
  * Agentgateway loopback `:8080/v1` routing to live **Vertex AI Gemini 2.0 Flash** in `asia-south1`.
  * Live HTTP/2 SSE streaming over Cloud Run consumed by `@assistant-ui/react-google-adk`.
  * Live session and event persistence in Supabase PostgreSQL via `DatabaseSessionService`.
  * Live event tree branching: editing a message creates a real child event row in Supabase Postgres.
* **Prohibited Mocks**: Mock chat responses, artificial sleep timers simulating streaming, in-memory session arrays.
* **Live Test**: Send query -> verify live token stream from Vertex AI with TTFT <800ms; verify session row in Supabase.

### Spec 03: DPDP Compliance, Cloud DLP Indian PII Redaction & DSR Erasure
* **Live Integration Requirement**:
  * Live Google Cloud Sensitive Data Protection (DLP API) in `asia-south1` inspecting `INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER`.
  * Real in-stream reversible tokenization (`<IN_PAN_1>`) in ADK `before_model` callback.
  * Live Supabase DSR stored procedure `execute_dsr_erasure()` and `client.auth.admin.delete_user()`.
  * Structured audit logging to live Google Cloud Logging sink.
* **Prohibited Mocks**: Client-side regex-only PII masking without DLP API; fake account deletion that leaves rows in Postgres.
* **Live Test**: Send real test Aadhaar/PAN -> verify prompt sent to Vertex AI has tokens; invoke account deletion -> verify zero residual rows across Supabase Auth, profiles, and sessions.

### Spec 04: Dynamic MCP Tools, Supabase Vault & In-Chat HITL
* **Live Integration Requirement**:
  * Real Agentgateway MCP federation on `127.0.0.1:8080/mcp` aggregating active MCP servers.
  * Real runtime token delegation: backend retrieves decrypted token from Supabase Vault and injects into Agentgateway headers.
  * Real heuristic tool classifier flagging write verbs as `critical: true`.
  * Live in-chat approval: ADK `ToolContext.request_confirmation()` pauses runner -> assistant-ui renders `ApprovalCard` -> user click resumes runner.
  * Real immutable audit record inserted into `public.tool_invocations` and Google Cloud Logging.
* **Prohibited Mocks**: Stub tools returning hardcoded JSON; auto-approving mutating actions without user interaction.
* **Live Test**: Trigger mutating action (`send_invoice`) -> verify runner pauses; verify `ApprovalCard` appears in browser; click Confirm -> verify tool executes and records audit log.

### Spec 05: Dynamic MCP Hub, OpenAPI Virtualization & Anti-SSRF FCM Alerts
* **Live Integration Requirement**:
  * Real Agentgateway OpenAPI-to-MCP compilation against live Indian ERP endpoints (Tally, Zoho Books).
  * Real anti-SSRF IP/DNS filter blocking DNS rebinding and IPv4-mapped IPv6 (`::ffff:169.254.169.254`).
  * Real Generative UI via `@assistant-ui/react-generative-ui` (`present({ display })`).
  * Real notification delivery via **Supabase Realtime** (`postgres_changes`) and live Firebase Cloud Messaging (FCM).
* **Prohibited Mocks**: Static mock connector catalog; hardcoded SVG invoice templates; simulated notification arrays.
* **Live Test**: Register OpenAPI spec -> verify live tool in Agentgateway; trigger notification -> verify Supabase Realtime broadcast arrives on frontend.

### Spec 06: Tri-Layer Memory via Vertex AI Embeddings & pgvector
* **Live Integration Requirement**:
  * Real Google Vertex AI `text-embedding-004` generating 768-dimensional embeddings in `asia-south1`.
  * Real Supabase `pgvector` table `public.user_memories` with HNSW cosine distance index (`vector_cosine_ops`, `<=>`).
  * Real ADK `after_agent` background fact extraction and `before_model` bounded top-K recall.
  * Real self-serve memory deletion drawer in assistant-ui.
* **Prohibited Mocks**: Fake embeddings (random floats); keyword search pretending to be vector search; in-memory vector lists.
* **Live Test**: Store user preference -> query unrelated topic -> verify vector recall retrieves fact into model context with similarity score >0.82.

### Spec 07: Sandboxed Code Artifacts & Google Cloud Storage
* **Live Integration Requirement**:
  * Real Google Cloud Storage (GCS) bucket in `asia-south1` generating V4 signed URLs.
  * Real sandboxed execution environment (E2B microVM / containerized runner).
  * Real isolated-origin iframe on subdomain (`artifacts.workkbot.in`) with strict CSP.
  * Real split Canvas workspace in assistant-ui (`AssistantFrameProvider`).
* **Prohibited Mocks**: Serving artifacts from local `/tmp`; executing code in the main backend process; fake GCS signed URLs.
* **Live Test**: Request Python data plot -> verify code executes in microVM; output uploaded to live GCS; rendered in sandboxed iframe.

### Spec 08: Skills-as-Content, Progressive Workflows & INR Cost Governance
* **Live Integration Requirement**:
  * Real markdown skills parsed from `skills/<name>/SKILL.md` with dynamic ADK router injection.
  * Real token consumption and INR cost conversion recorded in `public.token_ledger`.
  * Real custom metric `workkbot/token_cost_inr` emitted to Google Cloud Monitoring.
  * Real Agent-to-Agent (A2A) protocol proxy through Agentgateway.
* **Prohibited Mocks**: Hardcoded token prices; fake INR metrics; static agent handoffs.
* **Live Test**: Execute complex skill -> verify skill prompt injection; verify token count in Supabase matches Vertex AI usage; verify metric appears in Cloud Monitoring.

### Spec 09: Centralized Admin Console & Immutable BigQuery Audit Engine
* **Live Integration Requirement**:
  * Real Google Cloud Logging export sink streaming audit logs to **Google BigQuery** in `asia-south1`.
  * Real 7-year immutable retention policy lock applied to BigQuery dataset.
  * Real trace waterfall visualization via `@assistant-ui/react-o11y` in Admin Console.
  * Real administration CLI powered by `@assistant-ui/react-ink`.
* **Prohibited Mocks**: Mock BigQuery tables; browser console logs standing in for audit sinks.
* **Live Test**: Trigger audit event -> verify JSON record appears in BigQuery within streaming ingestion window.

### Spec 10: App-Store-Certified Native Mobile App & Google Cloud Armor
* **Live Integration Requirement**:
  * Real React Native Expo SDK 52 build communicating with Cloud Run backend.
  * Real Google Cloud Armor WAF policy enforcing Indian geofencing (`origin.region_code == 'IN'`).
  * Real mobile `ActionBarPrimitive` embedding Apple Guideline 1.2 Flag modal.
  * Real Reviewer Mode bypass (`apple-reviewer@workkbot.in`) on mobile login screen.
  * Real in-app memory erasure executing live Supabase RPC from mobile settings.
* **Prohibited Mocks**: Mock mobile network responses; simulated device frames.
* **Live Test**: Run Expo test suite against live Cloud Run backend; test Apple 1.2, 2.1, and 5.1.1 flows on physical iOS/Android device or simulator.

---

## 4. Live Testing & Verification Protocol (The Zero-Mock Scorecard)

To eliminate mocks from the test suite:

### 1. Isolated Test Tenants in Live Supabase
* Automated tests must NOT run against in-memory dictionaries.
* Tests run against the **live Supabase project**, using dedicated isolated test tenants:
  * Demo Tenant: `e0000000-0000-0000-0000-000000000002`
  * Ephemeral Test Organization: Created with prefix `test_org_<uuid>` and purged in fixture teardown.
* Every test suite cleans up after itself by executing the live `execute_dsr_erasure()` RPC.

### 2. Live Gateway & Model Probes
* Tests requiring model generation use live Vertex AI Gemini 2.0 Flash via Agentgateway loopback with small temperature (`0.0`) and max tokens (`100`) to guarantee deterministic evaluation.
* Circuit breaker tests simulate network disruption by sending synthetic 429 headers to Agentgateway proxy, testing live failover to secondary LLM endpoints.

### 3. Scorecard Gatekeeper Rule
No pull request, feature completion, or specification sign-off is accepted if:
1. Any code file imports `_local_db`, `_local_vault`, or static fixture stores.
2. Any test relies on monkeypatched HTTP clients when live endpoints are required by the spec.
3. Any table in Supabase fails Row-Level Security evaluation.
4. Any third-party OAuth token is found unencrypted outside Supabase Vault.

---

## 5. Localhost vs. Cloud Run Execution Matrix

The Zero-Mock Architecture Law distinguishes between **physical deployment target** and **system live-ness**:
- **Localhost Testing is 100% Zero-Mock Compliant** when connected to live cloud backbones (live Supabase Mumbai `ap-south-1`, live Vertex AI Gemini 2.0 Flash in `asia-south1`, and live GCP SDKs with Google Application Default Credentials).
- **Remote Cloud Run is Only Required** when validating network edge topologies, Google Cloud Armor WAF rules, container multi-pod routing, or external App Store reviewer access.

| Specification | Execution Target | Localhost Setup | Cloud Run Mandatory Rationale |
|---|:---:|---|---|
| **Spec 00: Constitution & Scaffold** | `Localhost` & `Staging Cloud Run` | Turborepo, local Next.js 15, local FastAPI | Dry-run Cloud Build container compile & deploy. |
| **Spec 01: Enterprise Identity & DPDP** | `Localhost (Zero-Mock)` | Next.js (`:3000`), FastAPI (`:8000`) | Live GoTrue OAuth, live Supabase Vault (`pgsodium`). |
| **Spec 02: Core Chat & ADK 2.0** | `Localhost (Zero-Mock)` | In-process ADK Runner, HTTP/2 SSE | Live Vertex AI Gemini 2.0 Flash, live Supabase sessions. |
| **Spec 03: DPDP PII & Erasure** | `Localhost (Zero-Mock)` | Presidio regex + Google Cloud DLP API via ADC | Live Cloud DLP in `asia-south1`, live Supabase DSR RPC. |
| **Spec 04: MCP Tools & In-Chat HITL** | `Localhost (Zero-Mock)` | Agentgateway on `127.0.0.1:8080/mcp` | Live Supabase Vault token decryption, live audit logging. |
| **Spec 05: Dynamic MCP Hub** | `Localhost (Zero-Mock)` | OpenAPI virtualizer, Generative UI | Live Supabase Realtime WebSocket broadcast from Mumbai. |
| **Spec 06: Tri-Layer Memory & Vector** | `Localhost (Zero-Mock)` | Vertex `text-embedding-004` via ADC | Live Supabase `pgvector` HNSW cosine index (`<=>`). |
| **Spec 07: Sandboxed Code Artifacts** | `Localhost` & `Staging Cloud Run` | Local container/microVM, GCS V4 signed URLs | Dry-run staging deploy to verify subdomain iframe CSP. |
| **Spec 08: Skills & Workflows** | `Localhost (Zero-Mock)` | Local markdown skills, SequentialAgent | Live Google Cloud Monitoring metric emission (`token_cost_inr`). |
| **Spec 09: Admin Console & BigQuery** | `Localhost (Zero-Mock)` | `/admin` dashboard, Admin CLI (`react-ink`)| Live BigQuery 7-yr audit dataset in `asia-south1` via ADC. |
| **Spec 10: Native Mobile (Expo)** | `Production Cloud Run Mandatory` | Expo SDK 52 simulator / TestFlight | **Hard Stop**: Cloud Armor WAF geofence (`origin: 'IN'`), VPC firewall (`169.254.169.254`), and Apple Reviewer credentials. |

---

## 6. Compliance & Implementation Checklist

Before declaring any spec complete:
- [ ] Spec's 4-Tier Validation Scorecard fully satisfied (Unit, Live, UI/E2E, and Manual).
- [ ] Live Supabase tables migrated and RLS policies verified.
- [ ] Live Supabase Vault RPCs confirmed storing and decrypting tokens.
- [ ] Live Vertex AI streaming verified over HTTP/2 SSE.
- [ ] Live Cloud DLP masking verified on prompt payloads.
- [ ] Live in-chat HITL confirmation confirmed functional in assistant-ui.
- [ ] Apple Guidelines 1.2 (Report AI), 2.1 (Reviewer Sandbox), and 5.1.1 (In-App Deletion) confirmed against live database.
- [ ] Zero mock data or in-memory dictionaries present in codebase.

