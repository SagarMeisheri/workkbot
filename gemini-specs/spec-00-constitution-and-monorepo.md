# Spec 00: Constitution, Operational Boundaries & Google Cloud Monorepo Scaffold

## 1. Context & Motivation
Workkbot is built for small-to-medium businesses (<100 employees) operating primarily in the Indian corporate landscape. It must combine high developer velocity with low operating costs while enforcing strict security, compliance, and architectural boundaries under India's **DPDP Act 2023**.
This spec establishes the project constitution, non-negotiable boundaries, and the consolidated single-backend monorepo structure built and deployed on **Google Cloud Platform (`asia-south1` / Mumbai)** from Day 1, with **Supabase (Mumbai)** as the unified data, auth, vector, and storage platform.

## 2. Project Boundaries & Non-Negotiables
- **Boundary 1 (Day-1 Google Cloud Serverless Compute)**: A single, unified **Python 3.12 FastAPI** backend (`apps/backend`) and **Next.js 15 SSR** frontend (`apps/web`) deploy natively to **Google Cloud Run** in `asia-south1` (Mumbai). Cloud Run manages concurrency (`--concurrency=80`), zero cold-starts (`--min-instances=1`), and native HTTP/2 SSE streaming without intermediary proxy servers.
- **Boundary 2 (Supabase Unified Data Backbone in Mumbai)**: All persistence, authentication, vector embeddings, and real-time pub/sub are consolidated on Supabase in Mumbai. Every table carries `org_id` with native PostgreSQL Row-Level Security (RLS). User OAuth tokens are encrypted at rest using **Supabase Vault (`pgsodium`)**.
- **Boundary 3 (DPDP Act 2023 Compliance by Design)**: Personal data cannot be dispatched to untrusted models without explicit consent and automated Indian PII masking (Aadhaar, PAN, UPI). DSR erasure cascades atomically across Supabase Auth, database rows, and vector embeddings.
- **Boundary 4 (100% User-Centric In-App HITL)**: Critical/write tool actions initiated by a user must be confirmed **inline in the chat interface by that user**. IT Admins are never spammed with routine user emails or personal task approvals.
- **Boundary 5 (App Store Approval Invariant)**: The mobile client must implement Apple/Google Play mandatory AI safety controls (Flag/Report buttons, in-app data deletion via Supabase Auth, test reviewer credentials, and privacy manifests) from the foundation.

---

## 3. Architecture & File Structure

```
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 (App Router) + @supabase/ssr + Tailwind v4 + shadcn/ui
│   ├── mobile/               # React Native (Expo SDK 52+) + @supabase/supabase-js + FCM
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
├── infra/                    # Google Cloud Build, Terraform, and Docker configurations
│   ├── gcp/
│   │   ├── cloudbuild.yaml   # Multi-stage container build and deploy pipeline
│   │   └── terraform/        # Cloud Run, Cloud Armor, Artifact Registry, GCS Terraform
│   └── docker/
│       ├── Dockerfile.backend# Multi-stage Python 3.12 container for FastAPI & ADK
│       └── Dockerfile.web    # Next.js 15 standalone output container
├── turbo.json                # Turborepo task pipeline configuration
├── pnpm-workspace.yaml       # pnpm monorepo workspace definition
└── package.json              # Monorepo root scripts
```

### Core Dependency Matrix:
- **Build System**: Turborepo `^2.4.x` + pnpm `^9.15.x` or `^10.x`.
- **Google Cloud Services**: Google Cloud Run, Google Cloud Build, Google Artifact Registry (`asia-south1-docker.pkg.dev`), Google Cloud Armor, Google Cloud Secret Manager.
- **Unified Backend Platform**: Supabase (PostgreSQL 16+, GoTrue Auth, Realtime, Vault, pgvector in Mumbai region).
- **Frontend Web**: Next.js `15.2.x` / `16.x`, `@supabase/ssr` `^0.5.x`, React `19.0.x`, Tailwind CSS `^4.0.x`.
- **Frontend Mobile**: Expo `SDK 52+`, React Native `0.76+` (New Architecture), `@supabase/supabase-js` `^2.48.x`.
- **Backend API & Agent Runtime**: Python `3.12.x`, FastAPI `^0.115.x`, `google-adk` (latest stable), `supabase-py` `^2.11.x`, Pydantic `^2.10.x`, SQLAlchemy `^2.0.x`, asyncpg `^0.30.x`.

---

## 4. Requirements & Implementation Details

### R00.1: Monorepo & Google Cloud Build Configuration
- Configure `pnpm-workspace.yaml` referencing `apps/*` and `packages/*`.
- Configure `turbo.json` defining declarative pipelines: `build`, `lint`, `typecheck`, `test`, `dev`.
- Create `infra/gcp/cloudbuild.yaml`:
  - Step 1: Run Turborepo lint, typecheck, and unit tests.
  - Step 2: Build production container images for `apps/backend` and `apps/web`.
  - Step 3: Push images to Artifact Registry (`asia-south1-docker.pkg.dev/$PROJECT_ID/workkbot-containers/`).
  - Step 4: Deploy `workkbot-backend` and `workkbot-web` to Google Cloud Run in `asia-south1`.

### R00.2: Local Supabase Development Environment (`supabase/`)
- Initialize the Supabase local environment via the Supabase CLI (`npx supabase init`).
- Local Supabase stack provides:
  - PostgreSQL 16+ with extensions: `uuid-ossp`, `pgcrypto`, `pgsodium` (Vault), and `vector` (`pgvector`).
  - GoTrue authentication service with email, OAuth, and SAML mock endpoints.
  - In-memory Realtime engine (`postgres_changes` and Broadcast).
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
| **VAL-00.4** | Python backend connects to local Supabase Postgres and verifies pgvector | `cd apps/backend && pytest tests/test_db_connection.py` | [ ] |
| **VAL-00.5** | Google Cloud Build pipeline compiles containers and executes dry-run deploy | `gcloud builds submit --config=infra/gcp/cloudbuild.yaml --substitutions=_DRY_RUN=true` | [ ] |
| **VAL-00.6** | Cloud Run service in `asia-south1` boots and passes health check | `curl -f https://$BACKEND_URL/healthz` | [ ] |
