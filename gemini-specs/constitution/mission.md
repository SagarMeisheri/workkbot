# Constitution: Mission, Boundaries & The 5 Frameworks

## 1. Project Vision
**Workkbot 2.0** is an enterprise-grade AI assistant platform purpose-built for organizations of under 100 employees, centered around **5 foundational frameworks**: **Supabase**, **Google Cloud Platform (GCP)**, **Google ADK 2.0**, **assistant-ui**, and **Agentgateway**.

### The North Star: Security & Mobile App Approval
Every product decision, technical implementation, and architectural design is guided by two non-negotiable North Stars:
1. **Uncompromising Enterprise Security**: Complete data isolation, zero-trust RLS policies in Supabase, hardware encryption in Supabase Vault, Cloud Armor WAF with Indian geofencing on GCP, metadata SSRF immunity via VPC firewall, real-time Cloud DLP PII sanitization, and Agentgateway tool poisoning defense, guaranteeing full statutory compliance with India's **DPDP Act 2023**.
2. **Guaranteed Mobile App Store Approval**: Complete, built-in adherence to **Apple App Store Review Guidelines** (Guidelines 1.2 & 1.2.1 UGC/AI safety & flagging, 2.1 App completeness with dedicated Reviewer Sandbox, 2.5.2 sandboxed artifact execution, 3.1.3c enterprise sign-in, 4.0 design excellence, 5.1.1 mandatory in-app account & memory deletion, 5.1.2i AI data consent) and **Google Play AI Safety Policies** delivered via `@assistant-ui/react-native`.

---

## 2. Target Audience & Personas
- **Primary Persona (The Employee)**: Interacts primarily inside the Workkbot web and mobile apps powered by `assistant-ui`. Connects work tools via the in-composer Connectors Hub (`+`), invokes dynamically discovered MCP tools federated by Agentgateway, and authorizes write actions inline in the chat stream via ADK 2.0 confirmation cards.
- **Secondary Persona (Org Admin / IT Lead)**: Governs provider allowlists in Supabase, monitors real-time token spend in Indian Rupees (INR) via GCP Cloud Monitoring, reviews immutable compliance logs streamed to Google BigQuery, and manages employee roles.
- **Auditor & Reviewer Persona (App Store Reviewer & DPDP Auditor)**: Given dedicated demo credentials (`apple-reviewer@workkbot.in`) allowing instantaneous login into an isolated Supabase tenant without corporate Google SSO, with pre-seeded data, ready to verify all AI safety and account deletion flows.

---

## 3. The 5-Framework Architecture Mapping

Every capability in Workkbot routes through these 5 pillars:
1. **Supabase (Unified Data Backbone)**: Manages authentication, tenant-isolated tables via PostgreSQL Row-Level Security (RLS), hardware token encryption via Supabase Vault (`pgsodium`), vector embeddings with `pgvector` HNSW (`<=>`), and instant UI sync via Supabase Realtime.
2. **Google Cloud Platform (GCP)**: Multi-container Cloud Run pod hosting backend services in Mumbai (`asia-south1`), Cloud Build CI/CD, Cloud Armor WAF and DDoS defense, Cloud DLP statutory Indian PII masking (Aadhaar, PAN, UPI), GCS signed artifact storage, and BigQuery immutable audit sinks.
3. **Google ADK 2.0 (`google-adk`)**: Python agentic runtime driving conversational turns, `LlmAgent`, `McpToolset`, `DatabaseSessionService`, `BaseMemoryService`, `before_model` interceptors, and user-centric in-chat HITL (`ToolContext.request_confirmation()`).
4. **assistant-ui**: Unified, cross-platform design system (`@assistant-ui/react` and `@assistant-ui/react-native`) providing canonical primitives (`ThreadListSidebar`, floating composer with `+` action menu, model selector, `BranchPickerPrimitive`, `Reasoning`, `Sources`, `ApprovalCard`, `@assistant-ui/react-generative-ui`, and `@assistant-ui/react-o11y`).
5. **Agentgateway 1.5.x**: High-performance Rust data plane running on loopback (`127.0.0.1:8080`), federating external MCP servers, virtualizing OpenAPI specs to MCP, blocking prompt injection and tool poisoning (CVE-2026-29791), enforcing CEL access control, and providing resilient LLM proxy routing to Vertex AI.

---

## 4. Non-Negotiable Boundaries & Constraints
- **Boundary 1 (Day-1 GCP & Supabase Deployment in Mumbai)**: All backend services and databases reside strictly in `asia-south1` (Mumbai) to satisfy Indian DPDP statutory data localization requirements.
- **Boundary 2 (In-App Exclusivity & Zero External Chat Bots)**: All workflows, approvals, and alerts occur inside the Workkbot web and mobile apps via assistant-ui primitives and native push notifications (FCM). External messaging platforms (WhatsApp, Slack bots) are strictly excluded from v1 to maintain data sovereignty.
- **Boundary 3 (Dynamic Tools via Standard MCP & Agentgateway)**: No proprietary, hardcoded tool connectors. All external integrations run as standard Model Context Protocol (MCP) servers federated by Agentgateway.
- **Boundary 4 (DPDP Statutory Compliance & Zero Residual Erasure)**: Bilingual statutory notice upon login. Real-time Indian PII masking via Cloud DLP prior to model dispatch. Right to Erasure cascades through Supabase Auth, database records, and vector embeddings in a single atomic transaction.
- **Boundary 5 (App Store Approval Guarantees)**: Native `@assistant-ui/react-native` client must include an in-app flag/report action on every AI response, a one-tap in-app account deletion flow that purges all user data immediately, and a dedicated Reviewer Sandbox login.
