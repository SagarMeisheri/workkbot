# Spec 00: Constitution, Operational Boundaries & Monorepo Scaffold (The 5-Framework Foundation)

## 1. Context & Motivation
Workkbot 2.0 is built for small-to-medium businesses (<100 employees) operating primarily in the Indian corporate landscape. It must combine high developer velocity with low operating costs while enforcing strict security, compliance, and architectural boundaries under India's **DPDP Act 2023** and **Apple App Store Review Guidelines**.

To eliminate technical debt, fragmented backends, and deployment risks, Workkbot centers every architectural and feature decision around **5 core frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Unified data, auth, RLS, hardware vault, vector, and realtime backbone.
2. **Google Cloud Platform (GCP `asia-south1`)**: Serverless compute (Cloud Run Multi-Container), edge WAF (Cloud Armor), statutory PII protection (Cloud DLP), secure storage (GCS), and immutable audit sinks (BigQuery).
3. **Google ADK 2.0 (`google-adk`)**: Python agentic execution runtime, toolset orchestration (`McpToolset`), session persistence, and user-centric in-chat HITL (`ToolContext.request_confirmation()`).
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: Unified, cross-platform conversational design system, canonical primitives, generative UI, and mobile native interface.
5. **Agentgateway 1.5.x (Rust)**: High-speed agentic data plane, dynamic MCP tool federation, OpenAPI virtualizer, anti-poisoning filter, and resilient LLM proxy.

### **The North Star: Security & Mobile App Approval**
- **Security Invariant**: Zero Trust tenant isolation via Supabase RLS, hardware-grade token encryption in Supabase Vault (`pgsodium`), Cloud Armor WAF with Indian geofencing, Cloud Run Direct VPC Egress blocking metadata SSRF (`169.254.169.254`), Agentgateway prompt injection / tool poisoning filtering, real-time Cloud DLP redaction, and DPDP Act 2023 statutory compliance.
- **Mobile App Store Approval Invariant**: Out-of-the-box compliance with Apple App Store Review Guidelines (1.2 UGC/AI moderation & report flag, 2.1 App completeness with dedicated Reviewer Sandbox, 2.5.2 sandboxed artifacts, 3.1.3c enterprise B2B login, 4.0 design, 5.1.1 in-app account & memory deletion, 5.1.2i AI data consent) and Google Play AI Safety Policies.

---

## 2. The 5-Framework Architecture Mapping for Spec 00

| Framework | Core Responsibility in Monorepo Foundation | Security & Mobile Compliance Guarantee |
|---|---|---|
| **1. Supabase** | Local & production PostgreSQL 16+ stack, GoTrue Auth, `pgsodium` Vault, `pgvector`, Realtime pub/sub. | All tables enforce RLS on `auth.uid()` and `auth.jwt() ->> 'org_id'`. Native `auth.admin.deleteUser()` supports Apple Guideline 5.1.1 in-app account deletion. |
| **2. Google Cloud Platform (GCP)** | Multi-container Cloud Run pod in Mumbai (`asia-south1`), Cloud Build CI/CD, Artifact Registry, Cloud Armor WAF. | Direct VPC Egress blocks `169.254.169.254/32` (metadata SSRF immunity). Cloud Armor enforces Indian geofencing (`origin.region_code == 'IN'`). |
| **3. Google ADK 2.0** | Embedded in-process inside FastAPI container; executes conversational turns and manages session lifecycle. | Runs in secure Python 3.12 sandbox; mutating actions gated by `ToolContext.request_confirmation()` directly in the user's chat stream. |
| **4. assistant-ui** | Unified component catalog for Next.js 15 web app and Expo SDK 52 mobile app (`@assistant-ui/react-native`). | Guarantees fluid 60fps mobile UI, instant in-app flag/report AI safety actions (Apple Guideline 1.2), and responsive canvas splits. |
| **5. Agentgateway 1.5.x** | Rust proxy sidecar on loopback `127.0.0.1:8080`, handling MCP federation, CEL RBAC, and LLM circuit breaking. | Eliminates prompt injection delimiters from tool definitions, blocks tool shadowing, and prevents SSRF probes before reaching tools. |

---

## 3. Architecture & File Structure

```text
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 (App Router) + @assistant-ui/react + @assistant-ui/react-google-adk + @supabase/ssr + Tailwind v4
│   ├── mobile/               # React Native (Expo SDK 52+) + @assistant-ui/react-native + @supabase/supabase-js + FCM
│   └── backend/              # Unified Python 3.12 FastAPI + Google ADK 2.0 + supabase-py -> Cloud Run
├── packages/
│   ├── shared-types/         # Shared Zod / TypeScript schemas (Messages, Tools, Approvals, Consent)
│   ├── ui/                   # Shared React UI & assistant-ui elements (web & admin)
│   ├── eslint-config/        # Monorepo linting rules
│   └── tsconfig/             # Base TypeScript configurations
├── skills/                   # Versioned markdown & script skills ("content as data")
├── supabase/                 # Supabase configuration, migrations, RLS policies, and seed data
│   ├── config.toml           # Supabase CLI project config
│   ├── migrations/           # Versioned SQL migrations (RLS, pgvector, Vault)
│   └── seed.sql              # Local development seed data
├── infra/                    # Google Cloud Build, Terraform, and Docker configurations
│   ├── agentgateway/         # Agentgateway 1.5.x Rust configuration, CEL policies & upstream routes
│   │   └── agentgateway.yaml # Declarative MCP federation, OpenAPI routes, and LLM failover
│   ├── gcp/
│   │   ├── cloudbuild.yaml   # Multi-stage container build and deploy pipeline
│   │   └── terraform/        # Cloud Run multi-container, Cloud Armor, VPC Firewall rules, and GCS
│   └── docker/
│       ├── Dockerfile.backend# Multi-stage Python 3.12 container for FastAPI & ADK
│       └── Dockerfile.web    # Next.js 15 standalone output container
├── turbo.json                # Turborepo task pipeline configuration
├── pnpm-workspace.yaml       # pnpm monorepo workspace definition
└── package.json              # Monorepo root scripts
```

---

## 4. Requirements & Implementation Details

### R00.1: Monorepo & Google Cloud Build Configuration (GCP + Monorepo)
- Configure `pnpm-workspace.yaml` referencing `apps/*` and `packages/*`.
- Configure `turbo.json` defining declarative pipelines: `build`, `lint`, `typecheck`, `test`, `dev`.
- Create `infra/gcp/cloudbuild.yaml`:
  - Step 1: Run Turborepo lint, typecheck, and unit tests.
  - Step 2: Build production container images for `apps/backend` and `apps/web`.
  - Step 3: Push images to Artifact Registry (`asia-south1-docker.pkg.dev/$PROJECT_ID/workkbot-containers/`).
  - Step 4: Deploy `workkbot-backend` (with `agentgateway` sidecar) and `workkbot-web` to Google Cloud Run in `asia-south1`.

### R00.2: Local Supabase Development Environment (`supabase/` - Supabase Framework)
- Initialize the Supabase local environment via the Supabase CLI (`npx supabase init`).
- Local Supabase stack provides:
  - PostgreSQL 16+ with extensions: `uuid-ossp`, `pgcrypto`, `pgsodium` (Vault), and `vector` (`pgvector`).
  - GoTrue authentication service with email, OAuth, and SAML mock endpoints.
  - In-memory Realtime engine (`postgres_changes` and Broadcast).
- Startup script:
  ```bash
  npx supabase start
  ```

### R00.3: Multi-Container Cloud Run Pod & Egress Firewall Shielding (GCP + Agentgateway)
- Deploy `workkbot-backend` as a multi-container Cloud Run service:
  - Container 1: FastAPI + ADK 2.0 Runner (listening on container port 8000).
  - Container 2: Agentgateway 1.5.x (listening on loopback `127.0.0.1:8080`).
- Configure Direct VPC Egress (`--vpc-egress=all-traffic`) attaching to `workkbot-vpc`.
- Terraform `infra/gcp/terraform/firewalls.tf`:
  - Enforce high-priority DENY rule on egress to `169.254.169.254/32` (Google Cloud Metadata Server), completely inoculating against container-level SSRF credential harvesting.

### R00.4: Canonical Assistant-UI Primitive Catalog Scaffold (assistant-ui Framework)
- Scaffold `@assistant-ui/react` elements catalog across `apps/web` and `packages/ui`:
  - `ThreadListSidebar` with collapsible toggle `[\|]`, `+ New thread`, and bottom user auth footer (`-> Sign in` / employee profile).
  - Floating Composer container embedding `ComposerPrimitive.Input`, `+` tool connector popover (`tool-popover.tsx`), `ModelSelector` pill, speech-to-text microphone, and send button (`↑`).
  - Staggered prompt chips (`SuggestionPrimitive`).
  - Streaming components: `Reasoning`, `Sources`, `BranchPickerPrimitive`, `ToolGroup`, and inline `ApprovalCard`.
  - Action bar: `ActionBarPrimitive` embedding instant **"Flag / Report AI Response"** button for Apple Guideline 1.2 compliance.

### R00.5: Agentic Data Plane Configuration (Agentgateway + Google ADK 2.0)
- Configure `infra/agentgateway/agentgateway.yaml`:
  - MCP tool federation mapping loopback `http://127.0.0.1:8080/mcp` to configured upstreams.
  - Primary LLM routing to Vertex AI `gemini-2.0-flash` with circuit-breaker fallback to `gemini-2.0-pro`.
  - Anti-poisoning content filter sanitizing tool description injection markers.
  - Common Expression Language (CEL) policy enforcement for tenant-scoped tool authorization.

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
| **VAL-00.7** | Agentgateway sidecar container boots and responds to loopback health probe | `curl -f http://127.0.0.1:8080/health` | [ ] |
| **VAL-00.8** | Cloud Run VPC firewall rule successfully drops egress calls to `169.254.169.254` | `pytest apps/backend/tests/test_metadata_ssrf_blocked.py` | [ ] |
| **VAL-00.9** | Mobile app builds on Expo SDK 52 without hermes or native crash | `cd apps/mobile && npx expo export --platform ios` | [ ] |
