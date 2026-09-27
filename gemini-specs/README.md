# Workkbot 2.0: Architecture & 10-Feature Specification Roadmap
## Sized for Indian SMBs (<100 Seats) Built & Deployed on Google Cloud (asia-south1) with Supabase & DPDP Compliance

---

### Project Constitution (Spec-Driven Development)
Per the [spec-driven-development](file:///Users/sagarmeisheri/.gemini/config/skills/spec-driven-development/SKILL.md) framework, the project constitution defines the non-negotiables, technical blueprint, and living roadmap:
- **[constitution/mission.md](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/constitution/mission.md)**: Vision, personas, product scope, and non-negotiable operational boundaries.
- **[constitution/techstack.md](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/constitution/techstack.md)**: Single FastAPI backend on Google Cloud Run, Google Vertex AI, Google Cloud Build, and Supabase unified platform rules.
- **[constitution/roadmap.md](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/constitution/roadmap.md)**: Living execution sequence with Gantt milestones for GCP deployment from Day 1.

---

### Executive Vision & Day-1 Google Cloud Architectural Foundation
Workkbot 2.0 is an enterprise-grade AI assistant platform designed specifically for organizations of under 100 employees, with direct focus on Indian SMB workflows, statutory compliance with the **Digital Personal Data Protection Act (DPDP Act) 2023**, and **guaranteed mobile App Store approval** on iOS and Android.

#### Key Architectural Pillars (GCP Day 1):
1. **Google Cloud Serverless & Agentic Compute Plane (asia-south1 / Mumbai)**:
   - **Google Cloud Run Multi-Container Pod**: Hosts the unified Python 3.12 FastAPI backend (running Google ADK 2.0 Runner in-process) paired with **Agentgateway 1.5.x** (Rust-based Agentic Data Plane & MCP Gateway) over loopback `127.0.0.1:8080`, offloading long-lived MCP SSE sessions and multi-LLM circuit breaking.
   - **Google Cloud Build & Artifact Registry**: Automated CI/CD pipeline building, scanning, and deploying container images into `asia-south1-docker.pkg.dev` on every commit.
   - **Google Cloud Armor & Direct VPC Egress**: Cloud Armor WAF with Indian geofencing (`origin.region_code == 'IN'`), preconfigured OWASP rules, and Direct VPC Egress firewall rules dropping all egress to Cloud Metadata (`169.254.169.254`) and internal RFC1918 subnets, eliminating SSRF attack vectors.
2. **Supabase as Unified Data & Security Backbone (Mumbai Region)**: Consolidates PostgreSQL 16+, GoTrue Auth, Row-Level Security (RLS), Supabase Vault (hardware token encryption via `pgsodium`), Supabase Vector (`pgvector` HNSW `<=>`), and Supabase Realtime (in-app alerts and HITL sync) into a single operational footprint.
3. **Agentgateway 1.5.x Federated MCP & Resilient LLM Gateway**:
   - **MCP Tool Federation & OpenAPI Virtualization**: Aggregates disparate MCP tools (Google Workspace, Zoho, GitHub) and converts internal SMB REST APIs (Tally, Zoho Books) into native MCP tools.
   - **Anti-Poisoning & Parameter Sanitization**: Defends against indirect prompt injection in tool definitions, blocks tool shadowing, and enforces parameter sanitization (mitigating CVE-2026-29791).
   - **Resilient LLM Routing**: Primary routing to Vertex AI Gemini 2.0 Flash with automatic circuit-breaking fallback to Gemini 2.0 Pro.
   - **Agent-to-Agent (A2A)**: Native A2A protocol gateway for cross-departmental agent task delegation.
4. **Google Vertex AI & Sensitive Data Protection (Cloud DLP)**:
   - **Gemini 2.0 Flash / Pro**: Primary agentic reasoning and Model Context Protocol (MCP) tool execution via Google ADK 2.0.
   - **Cloud DLP API + Fast-Path Regex**: Real-time Indian PII masking (Aadhaar, PAN, UPI, mobile) executed inside `before_model` callback before prompts reach the LLM.
5. **Google Cloud Storage (GCS) for Sandboxed Artifacts**: Secure bucket storage in `asia-south1` with V4 Signed URLs, path traversal sanitization (mitigating CVE-2026-34371), and isolated iframe rendering (`artifacts.workkbot.in`).
6. **Immutable Governance & Audit on GCP**:
   - Structured JSON audit logging to **Google Cloud Logging** and Cloud Trace via Agentgateway OpenTelemetry.
   - Cloud Logging export sink streaming immutable records to **Google BigQuery** in `asia-south1` with a 7-year lock for DPDP compliance.
   - Real-time token usage converted into Indian Rupees (INR) and monitored via **Google Cloud Monitoring** custom metrics and alerts.
7. **In-App Focused Workspace & 100% User-Centric In-Chat HITL**: Mutating actions are automatically classified and confirmed **inline in the chat stream by the individual user** via `ToolContext.request_confirmation()`. In-app notification drawers (synced via Supabase Realtime) and mobile push alerts (Firebase Cloud Messaging) notify users when away from the thread. Zero admin approval bottlenecks.
8. **Mobile App Store Readiness**: Complete pre-compliance for Apple App Store (Guidelines 1.2, 2.1, 3.2.2, 4.0, 5.1.1) and Google Play AI Safety:
   - In-app "Flag/Report AI Response" on every chat bubble.
   - In-app "Delete Account & Purge Memory" flow via Supabase Auth and RPC.
   - Pre-configured Reviewer Sandbox credentials bypassing corporate MFA.

---

### The 10-Feature Specification Ladder (Day 1 on Google Cloud)

```mermaid
graph TD
    S00[Spec 00: Constitution, Multi-Container Cloud Run & Agentgateway Scaffold] --> S01[Spec 01: Enterprise Identity, Google/Zoho MCP Connector + DPDP Consent]
    S01 --> S02[Spec 02: Core Chat on ADK 2.0 & Agentgateway Resilient LLM Proxy]
    S02 --> S03[Spec 03: DPDP Compliance, Cloud DLP Indian PII Redaction & DSR Erasure]
    S03 --> S04[Spec 04: Federated MCP Gateway, Anti-Poisoning & In-Chat HITL]
    S04 --> S05[Spec 05: Dynamic MCP Hub, OpenAPI Virtualization & Anti-SSRF FCM Alerts]
    S05 --> S06[Spec 06: Tri-Layer Memory via Vertex AI Embeddings & pgvector]
    S06 --> S07[Spec 07: Sandboxed Code Artifacts, Path Sanitization & GCS Persistence]
    S07 --> S08[Spec 08: Skills-as-Content, A2A Protocol Workflows & INR Cost Governance]
    S08 --> S09[Spec 09: Centralized Admin Console & Immutable Cloud Logging/BigQuery Audit]
    S09 --> S10[Spec 10: App-Store-Certified Native Mobile App - Expo SDK 52 & Cloud Armor]
```

| Spec | Title | Focus & Core Delivery on Google Cloud |
|:---:|---|---|
| **[Spec 00](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-00-constitution-and-monorepo.md)** | **Constitution & Monorepo** | Mission boundaries, Turborepo + pnpm layout, assistant-ui element catalog, Cloud Run Multi-Container Pod (FastAPI + Agentgateway 1.5.x), Cloud Armor, VPC metadata egress shielding in Mumbai. |
| **[Spec 01](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-01-auth-and-identity.md)** | **Auth, Identity & DPDP Consent** | Google Workspace OAuth, open-ended Connectors Hub (Google, Zoho, M365, Notion, Slack, Canva, Atlassian, HubSpot) with assistant-ui auth challenge cards, Supabase Vault token encryption, bilingual DPDP statutory consent. |
| **[Spec 02](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-02-core-chat-adk.md)** | **Core Chat on ADK 2.0 & assistant-ui** | Python ADK 2.0 Runner, `@assistant-ui/react-google-adk` (`useAdkRuntime`), Agentgateway LLM proxy with Vertex AI Gemini 2.0 Flash/Pro, HTTP/2 SSE streaming, message edit & branching (`BranchPickerPrimitive`). |
| **[Spec 03](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-03-dpdp-pii-and-erasure.md)** | **DPDP PII & Erasure Engine** | Google Cloud DLP (Sensitive Data Protection) + Regex fast-path for Indian PII (Aadhaar, PAN, UPI), assistant-ui PII redaction badges, cascading DSR Right to Erasure via Supabase RPC. |
| **[Spec 04](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-04-mcp-tools-and-hitl.md)** | **Dynamic MCP & In-Chat HITL** | Agentgateway MCP tool federation, tool poisoning defense, Supabase Vault, assistant-ui `useAdkToolConfirmations()` and inline `ApprovalCard` self-approval. |
| **[Spec 05](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-05-dynamic-mcp-hub.md)** | **Dynamic MCP Hub & Generative UI** | OpenAPI-to-MCP virtualization, `@assistant-ui/react-generative-ui` for SMB ledgers/invoices, strict anti-SSRF (CVE-2026-31943), Notification Center via Supabase Realtime + FCM. |
| **[Spec 06](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-06-tri-layer-memory.md)** | **Tri-Layer Memory System** | Episodic (Postgres), Semantic (Vertex AI `text-embedding-004` + `pgvector` HNSW `<=>`), Procedural (skills), assistant-ui "What AI Remembers" interactable panel. |
| **[Spec 07](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-07-sandboxed-artifacts.md)** | **Artifacts & GCS Persistence** | E2B microVMs + local Docker fallback, strict path traversal sanitization (CVE-2026-34371), GCS persistence with V4 signed URLs, assistant-ui split Canvas (`AssistantFrameProvider`). |
| **[Spec 08](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-08-skills-workflows-governance.md)** | **Skills, Workflows & Governance** | Content-as-data skills, `before_model` router, Agentgateway A2A protocol for cross-departmental agent delegation, assistant-ui agent badge updates, Cloud Monitoring in INR. |
| **[Spec 09](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-09-admin-console-and-audit.md)** | **Admin Console & Audit Engine** | Org-wide provider allowlisting, user roles, assistant-ui `@assistant-ui/react-o11y` trace timelines, terminal CLI via `@assistant-ui/react-ink`, immutable audit log streamed to BigQuery. |
| **[Spec 10](file:///Users/sagarmeisheri/Apps/workkbot/gemini-specs/spec-10-mobile-expo-app-store-ready.md)** | **App-Store-Ready Mobile App** | React Native Expo app with `@assistant-ui/react-native`, native `ActionBarPrimitive` with mandatory Apple Flag/Report AI safety action, reviewer demo mode, in-app deletion. |
