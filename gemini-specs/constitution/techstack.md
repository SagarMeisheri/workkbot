# Constitution: Tech Stack & Architecture (The 5-Framework Canonical Pentagram)

## 1. Architectural Overview & The 5 Core Frameworks

Workkbot 2.0 is architecturally anchored by **5 foundational frameworks**. Every architectural, product, and implementation decision must explicitly route through one or a combination of these five pillars:

1. **Supabase (Mumbai `ap-south-1`)**: The Unified Identity, Relational Data, Hardware Vault, Vector (`pgvector`), and Realtime Data Backbone.
2. **Google Cloud Platform (GCP `asia-south1`)**: The Serverless Compute, Enterprise Edge (Cloud Armor WAF), Statutory PII Sanitization (Cloud DLP), Secure Object Storage (GCS), and Immutable Governance Sink (BigQuery / Cloud Logging).
3. **Google ADK 2.0 (`google-adk`)**: The Stateful Agentic Runtime, Multi-Turn Reasoning Engine, Model Context Protocol Toolset (`McpToolset`), Session Manager, and User-Centric In-Chat HITL Orchestrator (`ToolContext.request_confirmation()`).
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-google-adk`, `@assistant-ui/react-native`)**: The Declarative Chat Surface, Canonical UI Primitive Catalog, Streaming State Harness, Mobile Native Interface, and Generative UI Renderer.
5. **Agentgateway 1.5.x (Rust)**: The Agentic Data Plane, Dynamic MCP Tool Federation Engine, OpenAPI Virtualizer, Tool Poisoning / Shadowing Defense, CEL Policy Arbiter, Resilient LLM Router, and A2A Protocol Gateway.

### **The North Star: Security & Mobile App Approval**
- **Security Invariant**: Zero Trust, strict tenant isolation via Supabase RLS, hardware-grade credential encryption in Supabase Vault, Cloud Armor WAF with Indian geofencing, Cloud Run Direct VPC Egress blocking metadata SSRF (`169.254.169.254`), Agentgateway prompt injection / tool poisoning filtering, real-time Cloud DLP redaction, and DPDP Act 2023 statutory compliance.
- **Mobile App Store Approval Invariant**: Built-in compliance with **Apple App Store Review Guidelines** (Guideline 1.2 & 1.2.1 AI UGC moderation/flagging, Guideline 2.1 App Completeness & Reviewer Sandbox, Guideline 2.5.2 Sandboxed Artifacts, Guideline 3.1.3(c) Enterprise B2B sign-in, Guideline 4.0 Design excellence, Guideline 5.1.1 Mandatory In-App Account & Memory Erasure, Guideline 5.1.2(i) AI Third-Party Data Transmission Consent) and **Google Play AI Safety & Data Erasure Policies**.

```text
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 (App Router) + @assistant-ui/react + @assistant-ui/react-google-adk + Supabase SSR + Tailwind v4 -> Cloud Run
│   ├── mobile/               # React Native (Expo SDK 52+) + @assistant-ui/react-native + Supabase Client + FCM
│   └── backend/              # Unified Python 3.12 FastAPI + Google ADK 2.0 + Supabase-py -> Cloud Run
├── packages/
│   ├── shared-types/         # Zod & TypeScript shared schemas (Message, Tool, Approval, Consent)
│   ├── ui/                   # Shared React UI & assistant-ui elements (web & admin)
│   ├── eslint-config/        # Monorepo linting standards
│   └── tsconfig/             # Base TypeScript configurations
├── skills/                   # Content-as-data skills (versioned markdown + scripts)
├── supabase/                 # Supabase migrations, RLS policies, Vault secrets, seed data (Mumbai)
├── infra/                    # Google Cloud Build, Terraform (Cloud Run, Cloud Armor, GCS, IAM)
│   ├── agentgateway/         # Agentgateway 1.5.x Rust configuration, CEL policies & upstream routes
│   │   └── agentgateway.yaml # MCP tool federation, OpenAPI routes, anti-poisoning & LLM failovers
│   ├── gcp/
│   │   ├── cloudbuild.yaml   # Multi-stage CI/CD deploying containers to Artifact Registry & Cloud Run
│   │   └── terraform/        # Cloud Run multi-container, Cloud Armor, VPC Firewall rules, and GCS buckets
│   └── docker/               # Production container definitions for backend and web
├── turbo.json                # Turborepo task pipeline configuration
├── pnpm-workspace.yaml       # Workspace package definitions
└── package.json              # Monorepo root scripts
```

---

## 2. The 5 Core Frameworks: Deep Architecture & Version Pinning

### Framework 1: Supabase (Day-1 Region: Mumbai `ap-south-1`)
- **Authentication**: Supabase Auth (GoTrue) handling Google Workspace OAuth, Enterprise SAML, Passkeys, and secure token lifecycle. Native `auth.admin.deleteUser()` driving the Apple Guideline 5.1.1 in-app account deletion pipeline.
- **Relational Storage & RLS**: PostgreSQL 16+ where every single table enforces Row-Level Security bound to `auth.uid()` and `auth.jwt() ->> 'org_id'`, guaranteeing zero cross-tenant data leaks.
- **Hardware Vault (`pgsodium`)**: Supabase Vault stores connected MCP OAuth tokens (Google, Zoho, M365, Notion, Slack, Canva, HubSpot) encrypted with hardware-managed keys. Plaintext access tokens are strictly banned.
- **Vector Database**: `pgvector` (`^0.8.0`) configured with HNSW cosine distance indexing (`vector_cosine_ops`, `<=>`) backing ADK 2.0's Semantic Memory.
- **Realtime Pub/Sub**: Supabase Realtime (`postgres_changes` & Broadcast) driving instant In-App Notification Center updates, approval states, and presence.

### Framework 2: Google Cloud Platform (Day-1 Region: `asia-south1` / Mumbai)
- **Compute Plane**: **Google Cloud Run Multi-Container Pod**:
  - Main Container: `apps/backend` (Python 3.12 FastAPI + Google ADK 2.0 Runner, port 8000).
  - Sidecar Container: **Agentgateway 1.5.x** (Rust-based data plane, loopback `127.0.0.1:8080`).
  - Frontend Container: `apps/web` (Next.js 15 SSR).
- **CI/CD & Registries**: Google Cloud Build pushing multi-arch container images to Google Artifact Registry (`asia-south1-docker.pkg.dev`).
- **Edge Security & Anti-DDoS**: Google Cloud Armor with Indian geofencing (`origin.region_code == 'IN'`), OWASP Core Ruleset, rate-limiting, and Cloud Load Balancing SSL.
- **Network Egress Hardening**: Cloud Run Direct VPC Egress (`--vpc-egress=all-traffic`) with VPC Firewall rules strictly blocking access to Link-Local Metadata (`169.254.169.254/32` and `metadata.google.internal`), eliminating SSRF token theft.
- **AI Models & Embeddings**: Google Vertex AI (`gemini-2.0-flash`, `gemini-2.0-pro`, `text-embedding-004`) fronted by Agentgateway.
- **Statutory PII Sanitization**: Google Cloud Sensitive Data Protection (Cloud DLP) configured with Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER`).
- **Artifact Object Storage**: Google Cloud Storage (GCS) with V4 Signed URLs and Uniform Bucket-Level Access.
- **Immutable Audit**: Google Cloud Logging, Cloud Trace, and Google BigQuery with a 7-year retention lock for DPDP compliance.

### Framework 3: Google ADK 2.0 (`google-adk` Python Framework)
- **Runtime & Execution**: `google-adk` Runner hosting stateful `LlmAgent` and multi-turn conversation loops in-process.
- **Tool Orchestration**: `McpToolset` interfacing directly with Agentgateway's unified loopback endpoint (`http://127.0.0.1:8080/mcp`).
- **In-Chat HITL**: Mutating actions trigger `ToolContext.request_confirmation()`, pausing execution cleanly until the user approves or denies in the chat stream.
- **Session & Memory Persistence**: `DatabaseSessionService` persisting episodic sessions into Supabase PostgreSQL, and `BaseMemoryService` interfacing with Supabase `pgvector`.
- **Lifecycle Interceptors**: `before_model` callbacks orchestrating real-time Cloud DLP masking and skill routing prior to LLM dispatch.

### Framework 4: assistant-ui (`@assistant-ui/react` & `@assistant-ui/react-native`)
- **Web & Mobile Parity**: Powers both the Next.js 15 web application (`@assistant-ui/react`) and the Expo SDK 52 mobile application (`@assistant-ui/react-native`).
- **ADK Runtime Bridge**: Connected via `@assistant-ui/react-google-adk` (`useAdkRuntime`, `useAdkToolConfirmations`, `useAdkAuthRequests`).
- **Canonical UI Element Catalog**:
  - `ThreadListSidebar` with collapsible toggle `[\|]`, `+ New thread`, and bottom user auth footer (`-> Sign in` / employee profile).
  - Floating Composer with `+` action dropdown (`tool-popover.tsx`), model selector pill, dictation microphone, and send button (`↑`).
  - Staggered prompt chips (`SuggestionPrimitive`).
  - Chat stream with `Reasoning`, `Sources`, `BranchPickerPrimitive`, `ToolGroup`, and inline `ApprovalCard`.
  - **App Store Mandatory AI Controls**: Native `ActionBarPrimitive` embedding instant **"Flag / Report AI Response"** modal for Apple Guideline 1.2 compliance.
- **Generative UI**: `@assistant-ui/react-generative-ui` (`present({ display })`) dynamically rendering rich business ledgers, GST tables, and invoices.
- **Observability & Administration**: `@assistant-ui/react-o11y` for trace timeline visualizations and `@assistant-ui/react-ink` for terminal DevOps management.

### Framework 5: Agentgateway 1.5.x (Rust Agentic Data Plane)
- **MCP Tool Federation**: Aggregates disparate MCP servers (Google Workspace, Zoho Workplace, GitHub, Notion, Slack) behind a single loopback endpoint (`http://127.0.0.1:8080/mcp`), managing JSON-RPC connections and stateful sessions.
- **OpenAPI-to-MCP Virtualization**: Compiles OpenAPI 3.0 specs (Tally Prime, Zoho Books, internal SMB APIs) into native MCP tools at runtime.
- **Prompt Injection & Tool Poisoning Defense**: Multi-layer content filters sanitizing prompt injection delimiters from tool descriptions and blocking unauthorized duplicate/shadowed tool registrations.
- **Parameter Sanitization**: Automatic schema validation blocking shell metacharacters and parameter tampering (mitigating CVE-2026-29791).
- **Fine-Grained CEL Authorization**: Common Expression Language policy engine enforcing per-user, per-role tool execution permissions.
- **Resilient LLM Routing**: Upstream proxy to Vertex AI Gemini with automated circuit breaking, token rate limiting, and fallback routing.
- **Agent-to-Agent (A2A)**: Native protocol proxy for inter-agent delegation between specialized departmental agents.

---

## 3. The 5-Framework Decision Routing Rule

For every feature, architectural modification, or bug fix:
1. **Identify the Framework Mapping**: The solution must be mapped across Supabase, GCP, Google ADK 2.0, assistant-ui, and Agentgateway. Custom scratchpad code outside these 5 boundaries is strictly forbidden.
2. **Validate Security**:
   - Is all persistent tenant state protected by Supabase RLS?
   - Are third-party tokens sealed in Supabase Vault?
   - Does traffic egress comply with Cloud Run Direct VPC Egress rules (blocking `169.254.169.254`)?
   - Are tool calls filtered by Agentgateway anti-poisoning?
   - Is Indian PII scrubbed via Cloud DLP before reaching the model?
3. **Validate Mobile App Store Approval**:
   - Does this feature violate Apple App Store Review Guidelines (1.2, 2.1, 2.5.2, 3.1.3c, 4.0, 5.1.1, 5.1.2i) or Google Play policies?
   - Does every AI-generated message provide an in-app flag/report mechanism?
   - Is the user able to delete their account and purge all memory completely in-app?
   - Can an App Store reviewer test the complete feature using the demo credentials without corporate SSO?
   - Does UI render flawlessly on both web and `@assistant-ui/react-native`?
