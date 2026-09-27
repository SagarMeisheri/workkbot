# Constitution: Tech Stack & Architecture

## 1. Architectural Overview

Monorepo (pnpm workspaces + Turborepo), structured across four unified planes: client, backend/agentic execution, tool (MCP), and the **Supabase Unified Data & Auth Platform**.

```text
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 (App Router) + Supabase SSR + Tailwind v4 + shadcn/ui
│   ├── mobile/               # React Native (Expo SDK 52+) + Supabase Client
│   └── backend/              # Unified Python 3.12 FastAPI + Google ADK 2.0 + Supabase-py
├── packages/
│   ├── shared-types/         # Zod & TypeScript shared schemas (Message, Tool, Approval)
│   ├── ui/                   # Shared React UI component library (web & admin)
│   ├── eslint-config/        # Monorepo linting standards
│   └── tsconfig/             # Base TypeScript configurations
├── skills/                   # Content-as-data skills (versioned markdown + scripts)
├── supabase/                 # Supabase migrations, RLS policies, Vault secrets, seed data
├── infra/                    # Docker Compose (Supabase local CLI stack), Terraform
├── turbo.json                # Turborepo task pipeline configuration
├── pnpm-workspace.yaml       # Workspace package definitions
└── package.json              # Monorepo root scripts
```

## 2. Core Dependencies & Versions

- **Language & Runtime**: TypeScript 5.x (`web`, `mobile`, `packages/*`); Python 3.12.x (`backend`).
- **Unified Data & Platform Backend**: **Supabase**:
  - **Auth**: Supabase Auth (OIDC, SAML 2.0 Enterprise SSO, Google/Zoho OAuth, Magic Links/Email OTP, Passkeys, PKCE, MFA, and native `deleteUser` account erasure).
  - **Database**: Supabase PostgreSQL 16+ with native **Row-Level Security (RLS)** using `auth.uid()` and `auth.jwt() ->> 'org_id'`.
  - **Vault**: Supabase Vault (`pgsodium` / `vault.secrets`) for hardware-grade encryption of user MCP OAuth tokens at rest.
  - **Vector**: Supabase Vector (`pgvector` `^0.8.0`) with HNSW cosine distance indexing (`<=>`) backing ADK's `BaseMemoryService`.
  - **Storage**: Supabase Storage (S3-compatible, RLS-governed, time-limited signed URLs) backing ADK's Artifact Service.
  - **Realtime**: Supabase Realtime (`postgres_changes` & Broadcast) driving live In-App Notification Center sync and approval state.
- **Agentic Harness**: **Google ADK 2.0** (`google-adk`, pinned explicit version) — Runner, `LlmAgent`, `McpToolset`, `DatabaseSessionService`, `BaseMemoryService`, and Artifact Service.
- **Backend API & Streaming**: **FastAPI** `^0.115.x` + `supabase-py` `^2.11.x` + `asyncpg` `^0.30.x`; async SSE streaming; Pydantic `^2.10.x`.
- **Web Frontend**: **Next.js** `15.2.x` / `16.x` (App Router), `@supabase/ssr` `^0.5.x`, **React** `19.0.x`, **Tailwind CSS** `^4.0.x`, **shadcn/ui**, **TanStack Query** `^5.66.x`.
- **Mobile Client**: **React Native 0.76+** via **Expo SDK 52+** (New Architecture enabled), `@supabase/supabase-js` `^2.48.x`, `expo-router`, `expo-secure-store`, `expo-local-authentication`, `expo-sqlite`, `react-native-webview`.
- **Tool Protocol**: **Model Context Protocol (MCP)** via ADK’s `McpToolset`; dynamic tool discovery via `tools/list`.
- **Code Execution Sandbox**: **E2B** Firecracker microVMs (`e2b-code-interpreter`) with local Docker/gVisor runner fallback.
- **Testing & Quality**: Pytest (`backend`), Playwright / Vitest (`web`), Ruff / Black (Python), ESLint / Prettier (TypeScript).

## 3. Architectural Constraints & Code Rules

1. **Supabase as Single Source of Truth**: All identity, permissions, data storage, vectors, and binary artifacts are managed within Supabase. No separate standalone Redis cluster or secondary database is introduced.
2. **Native Row-Level Security (RLS)**: Every database table carries an `org_id` and strict Supabase RLS policies. The FastAPI backend and client SDKs operate under authenticated Supabase JWT sessions, making cross-tenant data leaks impossible at the database engine level.
3. **Hardware Encryption in Supabase Vault**: User MCP OAuth tokens are stored in `vault.decrypted_secrets` or encrypted with `pgsodium`. Plaintext token columns are a strict constitutional violation.
4. **Single Backend Plane**: `apps/backend` (Python FastAPI) serves all API endpoints, auth verification via Supabase Auth, SSE streaming, and runs the ADK Runner directly.
5. **In-App First Alerting via Supabase Realtime**: All approval requests, tool execution statuses, and notifications surface inside the Workkbot web and mobile apps via Supabase Realtime channels and native Expo push notifications.
6. **Dynamic MCP Tool Discovery**: No hardcoded tool adapters. Workkbot manages MCP server endpoints; users complete OAuth, and tools are registered dynamically via `tools/list`.
7. **DPDP Statutory Compliance & Right to Erasure**: Statutory consent logged in Supabase. Real-time Indian PII masking (Aadhaar, PAN, UPI) in `before_model` callback. DSR erasure cascades through Supabase Auth, database tables, and vector embeddings in a single atomic transaction.
8. **Isolated-Origin Artifact Execution**: Generated HTML, SVG, and interactive scripts execute only in sandboxed environments and render exclusively on a separate subdomain iframe or sandboxed mobile WebView with a strict CSP.
