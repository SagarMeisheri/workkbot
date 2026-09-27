# Spec 00: Constitution, Operational Boundaries & Monorepo Scaffold

## 1. Context & Motivation
Workkbot is built for small-to-medium businesses (<100 employees) operating primarily in the Indian corporate landscape. It must combine high developer velocity with low operating costs while enforcing strict security, compliance, and architectural boundaries. 
This spec establishes the project constitution, non-negotiable boundaries, and the consolidated single-backend monorepo structure backed by **Supabase** as the unified data, auth, vector, and storage platform.

## 2. Project Boundaries & Non-Negotiables
- **Boundary 1 (Consolidated Backend Architecture)**: A single, unified **Python 3.12 FastAPI** backend (`apps/backend`) directly serves the REST/SSE endpoints, validates authentication via Supabase Auth, and runs the Google ADK 2.0 agent loop without intermediate proxy hops.
- **Boundary 2 (Supabase Unified Data & Security)**: All persistence, authentication, vector embeddings, binary artifacts, and real-time pub/sub are consolidated on Supabase. Every table carries `org_id` with native PostgreSQL Row-Level Security (RLS). User OAuth tokens are encrypted at rest using **Supabase Vault (`pgsodium`)**.
- **Boundary 3 (DPDP Act 2023 Compliance by Design)**: Personal data cannot be dispatched to untrusted models without explicit consent and automated Indian PII masking (Aadhaar, PAN, UPI). DSR erasure cascades atomically across Supabase Auth, database rows, and vector embeddings.
- **Boundary 4 (100% User-Centric In-App HITL)**: Critical/write tool actions initiated by a user must be confirmed **inline in the chat interface by that user**. IT Admins are never spammed with routine user emails or personal task approvals.
- **Boundary 5 (App Store Approval Invariant)**: The mobile client must implement Apple/Google Play mandatory AI safety controls (Flag/Report buttons, in-app data deletion via Supabase Auth, test reviewer credentials, and privacy manifests) from the foundation.

---

## 3. Architecture & File Structure

```
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 (App Router) + @supabase/ssr + Tailwind v4 + shadcn/ui
│   ├── mobile/               # React Native (Expo SDK 52+) + @supabase/supabase-js
│   └── backend/              # Unified Python 3.12 FastAPI + Google ADK 2.0 + supabase-py
├── packages/
│   ├── shared-types/         # Shared Zod / TypeScript schemas (Messages, Tools, Approvals)
│   ├── ui/                   # Shared React UI components (web & admin)
│   ├── eslint-config/        # Monorepo linting rules
│   └── tsconfig/             # Base TypeScript configurations
├── skills/                   # Versioned markdown & script skills ("content as data")
├── supabase/                 # Supabase configuration, migrations, RLS policies, and seed data
│   ├── config.toml           # Supabase CLI project config
│   ├── migrations/           # Versioned SQL migrations (RLS, pgvector, Vault)
│   └── seed.sql              # Local development seed data
├── turbo.json                # Turborepo task pipeline configuration
├── pnpm-workspace.yaml       # pnpm monorepo workspace definition
└── package.json              # Monorepo root scripts
```

### Core Dependency Matrix:
- **Build System**: Turborepo `^2.4.x` + pnpm `^9.15.x` or `^10.x`.
- **Unified Backend Platform**: Supabase (PostgreSQL 16+, GoTrue Auth, Realtime, Storage, Vault, pgvector).
- **Frontend Web**: Next.js `15.2.x` / `16.x`, `@supabase/ssr` `^0.5.x`, React `19.0.x`, Tailwind CSS `^4.0.x`.
- **Frontend Mobile**: Expo `SDK 52+`, React Native `0.76+` (New Architecture), `@supabase/supabase-js` `^2.48.x`.
- **Backend API & Agent Runtime**: Python `3.12.x`, FastAPI `^0.115.x`, `google-adk` (latest stable), `supabase-py` `^2.11.x`, Pydantic `^2.10.x`, SQLAlchemy `^2.0.x`, asyncpg `^0.30.x`.

---

## 4. Requirements & Implementation Details

### R00.1: Monorepo Configuration
- Configure `pnpm-workspace.yaml` referencing `apps/*` and `packages/*`.
- Configure `turbo.json` defining declarative pipelines: `build`, `lint`, `typecheck`, `test`, `dev`.
- Integrate `apps/backend` (Python) into Turborepo using a root `package.json` proxy script calling `uv` or `poetry run pytest`.

### R00.2: Local Supabase Development Environment (`supabase/`)
- Initialize the Supabase local environment via the Supabase CLI (`npx supabase init`).
- Local Supabase stack provides:
  - PostgreSQL 16+ with pre-installed extensions: `uuid-ossp`, `pgcrypto`, `pgsodium` (Vault), and `vector` (`pgvector`).
  - GoTrue authentication service with email, OAuth, and SAML mock endpoints.
  - In-memory Realtime engine (`postgres_changes` and Broadcast).
  - Storage API backed by local disk storage with S3 protocol compatibility.
- Startup script:
  ```bash
  npx supabase start
  ```

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-00.1** | `pnpm install` installs all workspace packages cleanly | `pnpm install` | [ ] |
| **VAL-00.2** | Turborepo pipeline builds shared packages without circular dependencies | `pnpm turbo run build` | [ ] |
| **VAL-00.3** | Supabase CLI starts up local stack (Postgres, Auth, Storage, Realtime, Vault) | `npx supabase start && npx supabase status` | [ ] |
| **VAL-00.4** | Python backend connects to local Supabase Postgres and verifies pgvector extension | `cd apps/backend && pytest tests/test_db_connection.py` | [ ] |
