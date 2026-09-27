# Constitution: Tech Stack & Architecture (Google Cloud + Supabase Day 1)

## 1. Architectural Overview

Monorepo (pnpm workspaces + Turborepo), structured across four unified planes: client, Google Cloud serverless backend/agentic execution, tool (MCP), and the **Supabase Unified Data & Auth Platform (Mumbai)**.

```text
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 (App Router) + Supabase SSR + Tailwind v4 + shadcn/ui -> Cloud Run
│   ├── mobile/               # React Native (Expo SDK 52+) + Supabase Client + FCM
│   └── backend/              # Unified Python 3.12 FastAPI + Google ADK 2.0 + Supabase-py -> Cloud Run
├── packages/
│   ├── shared-types/         # Zod & TypeScript shared schemas (Message, Tool, Approval)
│   ├── ui/                   # Shared React UI component library (web & admin)
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

## 2. Core Dependencies & Versions

- **Google Cloud Platform (Day-1 Region: `asia-south1` / Mumbai)**:
  - **Compute Engine / Serverless**: **Google Cloud Run Multi-Container Pod**:
    - **Main Container**: `apps/backend` (Python 3.12 FastAPI + ADK 2.0 Runner, port 8000).
    - **Sidecar Container**: **Agentgateway 1.5.x** (Rust-based Agentic Data Plane & MCP Gateway, loopback `127.0.0.1:8080`).
    - **Frontend Container**: `apps/web` (Next.js 15 SSR).
  - **CI/CD Pipeline**: **Google Cloud Build** building and pushing multi-arch images directly to **Google Artifact Registry** (`asia-south1-docker.pkg.dev`).
  - **Edge & Security**: **Google Cloud Armor** (WAF, rate limiting, DDoS protection, Indian geofencing `origin.region_code == 'IN'`, and pre-configured OWASP/LFI/RCE rules) + **Google Cloud Load Balancing** (managed SSL certificates).
  - **Network Isolation & SSRF Shielding**: Cloud Run **Direct VPC Egress** (`--vpc-egress=all-traffic`) with VPC Firewall rules strictly blocking container egress to Link-Local Cloud Metadata (`169.254.169.254/32` and `metadata.google.internal`) and unauthorized RFC1918 subnets.
  - **Identity & IAM Least Privilege**: Dedicated Service Account (`workkbot-backend-sa`) restricted strictly to `roles/aiplatform.user`, `roles/dlp.user`, and `roles/logging.logWriter` (no Editor/Owner permissions).
  - **AI & Embedding Models**: **Google Vertex AI** (`gemini-2.0-flash`, `gemini-2.0-pro`, `text-embedding-004`) fronted by Agentgateway's LLM proxy with automated circuit breaking and secondary provider failover.
  - **DPDP PII Engine**: **Google Cloud Sensitive Data Protection (Cloud DLP)** with Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER`).
  - **Artifact Object Storage**: **Google Cloud Storage (GCS)** in `asia-south1` with V4 Signed URLs and Uniform Bucket-Level Access.
  - **Observability & Audit**: **Agentgateway OpenTelemetry (OTel)** metrics, traces, and logs streamed directly to **Google Cloud Logging**, **Google Cloud Trace**, and **Google BigQuery** (immutable 7-year audit retention).
- **Agentic Data Plane & Gateway**: **Agentgateway 1.5.x (Rust)**:
  - **MCP Tool Federation**: Aggregates disparate MCP servers (Google Workspace, Zoho Workplace, GitHub, Notion) behind a single loopback endpoint (`http://127.0.0.1:8080/mcp`), managing stateful JSON-RPC sessions and fanning out `tools/list`.
  - **OpenAPI-to-MCP Virtualization**: Automatically converts existing Indian SMB REST APIs (Tally, Zoho Books, internal CRMs) into MCP-native tools with CVE-2026-29791 parameter sanitization.
  - **Tool Poisoning & Shadowing Defense**: Native multi-layer content filters sanitizing prompt injection delimiters from tool descriptions and blocking unauthorized duplicate/shadowed tool registrations.
  - **Authorization**: Fine-grained Common Expression Language (CEL) policy engine enforcing role-based tool visibility and blocking SSRF targets.
  - **A2A Protocol**: Built-in Agent-to-Agent communication proxy for departmental agent collaboration.
- **Unified Data & Platform Backend**: **Supabase (Mumbai ap-south-1)**:
  - **Auth**: Supabase Auth (OIDC, Google Workspace OAuth, Zoho OAuth, Enterprise SAML, Passkeys, PKCE, native `deleteUser` account erasure).
  - **Database**: Supabase PostgreSQL 16+ with native **Row-Level Security (RLS)** using `auth.uid()` and `auth.jwt() ->> 'org_id'`.
  - **Vault**: Supabase Vault (`pgsodium` / `vault.secrets`) for hardware-grade encryption of user MCP OAuth tokens at rest.
  - **Vector**: Supabase Vector (`pgvector` `^0.8.0`) with HNSW cosine distance indexing (`<=>`) backing ADK's `BaseMemoryService`.
  - **Realtime**: Supabase Realtime (`postgres_changes` & Broadcast) driving live In-App Notification Center sync and approval state.
- **Agentic Harness**: **Google ADK 2.0** (`google-adk`, pinned explicit version) — Runner, `LlmAgent`, `McpToolset`, `DatabaseSessionService`, and `BaseMemoryService`.
- **Backend API & Streaming**: **FastAPI** `^0.115.x` + `supabase-py` `^2.11.x` + `asyncpg` `^0.30.x`; async SSE streaming over HTTP/2; Pydantic `^2.10.x`.
- **Web Frontend**: **Next.js** `15.2.x` / `16.x` (App Router), `@supabase/ssr` `^0.5.x`, **React** `19.0.x`, **Tailwind CSS** `^4.0.x`, **shadcn/ui**, **TanStack Query** `^5.66.x`.
- **Mobile Client**: **React Native 0.76+** via **Expo SDK 52+** (New Architecture enabled), `@supabase/supabase-js` `^2.48.x`, `expo-router`, `expo-secure-store`, `expo-local-authentication`, `react-native-webview`.
- **Code Execution Sandbox**: **E2B** Firecracker microVMs (`e2b-code-interpreter`) with zero container host filesystem access and strict path traversal sanitization.
- **Testing & Quality**: Pytest (`backend`), Playwright / Vitest (`web`), Ruff / Black (Python), ESLint / Prettier (TypeScript).

## 3. Architectural Constraints & Code Rules

1. **Day-1 Google Cloud Deployment with Multi-Container Cloud Run**: Services run natively on Google Cloud Serverless (`asia-south1`). The backend deploys as a multi-container Cloud Run instance with FastAPI (ADK Runner) and Agentgateway 1.5.x (Rust) communicating via ultra-fast loopback (`127.0.0.1:8080`), avoiding cross-service internet hops.
2. **Supabase as Single Source of Data Truth**: All identity, permissions, and database tables are managed within Supabase in Mumbai. Every table carries an `org_id` and strict Supabase RLS policies.
3. **Hardware Encryption in Supabase Vault**: User MCP OAuth tokens are stored in `vault.decrypted_secrets` or encrypted with `pgsodium`. Plaintext token columns are a strict constitutional violation.
4. **Agentgateway as Sole MCP & LLM Data Plane**: The FastAPI backend does not manage raw SSE connections or multi-server fan-out to external MCP endpoints. All MCP server sessions and LLM calls route through Agentgateway, enforcing anti-poisoning, CEL RBAC, and parameter sanitization.
5. **SSRF & Metadata Server Egress Immunity**: Cloud Run Direct VPC Egress firewall rules unconditionally drop traffic to `169.254.169.254` and `metadata.google.internal`. Dynamic URL inputs are verified against DNS rebinding, IPv4-mapped IPv6 (CVE-2026-31943), and private CIDR ranges prior to connection.
6. **In-App First Alerting via Supabase Realtime & FCM**: All approval requests, tool execution statuses, and notifications surface inside the Workkbot web and mobile apps via Supabase Realtime channels and Firebase Cloud Messaging (FCM).
7. **DPDP Statutory Compliance & Right to Erasure**: Statutory consent logged in Supabase. Real-time Indian PII masking (Aadhaar, PAN, UPI) in `before_model` callback via Google Cloud DLP and regex. DSR erasure cascades through Supabase Auth, database tables, and vector embeddings in a single atomic transaction.
8. **Isolated-Origin & Sanitized Artifact Execution**: Code execution executes exclusively in isolated E2B Firecracker microVMs. Artifact filenames are strictly sanitized against path traversal (`../`) prior to GCS persistence, and render exclusively on a separate subdomain iframe with a strict CSP.
