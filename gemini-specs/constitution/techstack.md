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
│   ├── gcp/
│   │   ├── cloudbuild.yaml   # Multi-stage CI/CD deploying containers to Artifact Registry & Cloud Run
│   │   └── terraform/        # Cloud Run, Cloud Armor, Service Accounts, and GCS buckets
│   └── docker/               # Production container definitions for backend and web
├── turbo.json                # Turborepo task pipeline configuration
├── pnpm-workspace.yaml       # Workspace package definitions
└── package.json              # Monorepo root scripts
```

## 2. Core Dependencies & Versions

- **Google Cloud Platform (Day-1 Region: `asia-south1` / Mumbai)**:
  - **Compute Engine / Serverless**: **Google Cloud Run** running both `apps/backend` (Python 3.12 FastAPI + ADK 2.0 Runner) and `apps/web` (Next.js 15 SSR).
  - **CI/CD Pipeline**: **Google Cloud Build** building and pushing multi-arch images directly to **Google Artifact Registry** (`asia-south1-docker.pkg.dev`).
  - **Edge & Security**: **Google Cloud Armor** (WAF, rate limiting, DDoS protection) + **Google Cloud Load Balancing** (managed SSL certificates).
  - **AI & Embedding Models**: **Google Vertex AI** (`gemini-2.0-flash`, `gemini-2.0-pro`, `text-embedding-004`).
  - **DPDP PII Engine**: **Google Cloud Sensitive Data Protection (Cloud DLP)** with Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_NUMBER`, `INDIA_GST_NUMBER`).
  - **Artifact Object Storage**: **Google Cloud Storage (GCS)** in `asia-south1` with V4 Signed URLs and Uniform Bucket-Level Access.
  - **Observability & Audit**: **Google Cloud Logging** (structured JSON sinks), **Google Cloud Trace** (distributed tracing), and **Google BigQuery** (immutable 7-year audit retention).
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
- **Tool Protocol**: **Model Context Protocol (MCP)** via ADK’s `McpToolset`; dynamic tool discovery via `tools/list`.
- **Code Execution Sandbox**: **E2B** Firecracker microVMs (`e2b-code-interpreter`) with local Docker/gVisor runner fallback.
- **Testing & Quality**: Pytest (`backend`), Playwright / Vitest (`web`), Ruff / Black (Python), ESLint / Prettier (TypeScript).

## 3. Architectural Constraints & Code Rules

1. **Day-1 Google Cloud Deployment**: Every service runs natively on Google Cloud Serverless (`asia-south1`) from Day 1. Deployments are automated through `infra/gcp/cloudbuild.yaml` into Google Cloud Run.
2. **Supabase as Single Source of Data Truth**: All identity, permissions, and database tables are managed within Supabase in Mumbai. Every table carries an `org_id` and strict Supabase RLS policies.
3. **Hardware Encryption in Supabase Vault**: User MCP OAuth tokens are stored in `vault.decrypted_secrets` or encrypted with `pgsodium`. Plaintext token columns are a strict constitutional violation.
4. **Single Backend Plane on Cloud Run**: `apps/backend` (Python FastAPI) serves all API endpoints, auth verification via Supabase Auth, SSE streaming, and runs the ADK Runner directly with zero proxy hops.
5. **In-App First Alerting via Supabase Realtime & FCM**: All approval requests, tool execution statuses, and notifications surface inside the Workkbot web and mobile apps via Supabase Realtime channels and Firebase Cloud Messaging (FCM).
6. **DPDP Statutory Compliance & Right to Erasure**: Statutory consent logged in Supabase. Real-time Indian PII masking (Aadhaar, PAN, UPI) in `before_model` callback via Google Cloud DLP and regex. DSR erasure cascades through Supabase Auth, database tables, and vector embeddings in a single atomic transaction.
7. **Isolated-Origin Artifact Execution**: Generated HTML, SVG, and interactive scripts execute only in sandboxed environments, persist to Google Cloud Storage (GCS), and render exclusively on a separate subdomain iframe with a strict CSP.
