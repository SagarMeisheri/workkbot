# AGENTS.md

> **AI Agent Operating Guide & System Constitution for Workkbot 2.0**  
> *Target Audience: Autonomous AI Coding Agents (Antigravity, Cursor, Windsurf, Claude Code, Aider).*  
> *Last Verified: 2026-09-27 (Feature 1 Delivery).*

---

## 1. Core Operating Directive: The 5-Framework Architecture Law

Every code modification, feature addition, or architectural refactor in Workkbot **MUST** strictly route through the **5 Core Frameworks**. Writing scratchpad code or introducing ad-hoc third-party backends outside these 5 pillars is strictly forbidden:

1. **Supabase (Mumbai `ap-south-1`)**: Unified data backbone, GoTrue Auth, Row-Level Security (RLS) on all tables, hardware encryption in Supabase Vault (`pgsodium`), vector memory (`pgvector`), and Realtime sync.
2. **Google Cloud Platform (GCP `asia-south1`)**: Multi-container Cloud Run pod, Cloud Armor WAF with Indian geofencing, Direct VPC Egress blocking metadata SSRF (`169.254.169.254`), Cloud DLP Indian PII scrubbing, GCS signed artifacts, and BigQuery audit logs.
3. **Google ADK 2.0 (`google-adk`)**: Python agentic runtime driving conversational sessions, `LlmAgent`, `McpToolset`, session persistence, and in-stream HITL confirmation cards (`ToolContext.request_confirmation()`).
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: Declarative chat surface, canonical UI primitives (`ThreadListSidebar`, floating composer with `+` popover, `ModelSelector`, `Reasoning`, `Sources`, `ApprovalCard`), and mobile native parity.
5. **Agentgateway 1.5.x (Rust)**: High-speed agentic data plane on loopback (`127.0.0.1:8080`), federating external MCP tools, evaluating Common Expression Language (CEL) authorization policies, and defending against tool poisoning (CVE-2026-29791).

---

## 2. Agent Tooling, MCP Servers & Skills Mandate

Autonomous agents working on Workkbot **MUST** actively utilize the connected MCP servers, domain skills, and web search to solve tasks rather than guessing or relying on stale pre-trained weights:

### 1. Connected MCP Servers
- **Supabase MCP Server (`supabase`)**: Use for inspecting database schemas, listing tables/migrations, executing SQL queries, querying logs, and managing project configurations.
- **Google Cloud MCP Servers (`bigquery`, `cloudrun`, `cloud-sql`, `google-cloud-logging`, `google-cloud-monitoring`, `google-cloud-pubsub`)**: Use for querying GCP services, logs, BigQuery tables, Cloud Run deployments, and infrastructure state.

### 2. Specialized Skills Reference
- **assistant-ui Skills** (`setup`, `elements`, `runtime`, `tools`, `thread-list`, `markdown`, `copilots`, `generative-ui`): Mandatory reference when building or modifying chat UI components, client-side tools, and `@assistant-ui/react` runtime hooks.
- **Google ADK Skills** (`adk-agent-builder`, `adk-architecture`, `adk-debug`, `google-antigravity-sdk`): Mandatory reference when designing or debugging `google-adk` agents, runners, HITL confirmation cards, and workflow graphs.
- **Supabase Skills** (`supabase`, `supabase-postgres-best-practices`): Mandatory reference before altering schemas, authoring migrations, defining RLS policies, or tuning PostgreSQL performance.

### 3. Web Search & Documentation Verification
- Always use **Web Search** to verify current API signatures, breaking changes, framework release notes, and error codes before modifying application code.

---

## 3. Command Palette (Fast Execution Guide)

### Python Backend (`apps/backend`)
- **Package Manager**: Use `uv` strictly.
- **Sync Dependencies**:
  ```bash
  uv sync --extra dev
  ```
- **Run Tests (from Root)**:
  ```bash
  uv run pytest
  ```
- **Run Specific Test**:
  ```bash
  uv run pytest apps/backend/tests/auth/test_reviewer_login.py
  ```
- **Start Backend Dev Server (from Root)**:
  ```bash
  uv run uvicorn src.main:app --app-dir apps/backend --reload --port 8000
  ```
- **Direct Script Execution**:
  ```bash
  cd apps/backend && uv run python src/main.py
  ```

### Web Frontend (`apps/web`)
- **Package Manager**: `pnpm`.
- **Typecheck**:
  ```bash
  pnpm --filter @workkbot/web typecheck
  ```
- **Start Next.js 15 Dev Server**:
  ```bash
  pnpm --filter @workkbot/web dev
  ```

---

## 4. Strict Non-Negotiable Invariants

### 1. Security & Token Isolation
- **Zero Plaintext Tokens**: External OAuth credentials (Google Workspace, Zoho, Notion, Slack, Canva) must never be stored in plain text in database rows or logs. Always seal in Supabase Vault (`pgsodium`) as `mcp_token_${user_id}_${provider}`.
- **Tenant Isolation via Supabase RLS**: Every SQL table in `supabase/migrations/` must enable RLS and filter queries with `org_id = (auth.jwt() ->> 'org_id')::uuid` and `user_id = auth.uid()`.
- **Agentgateway CEL Isolation**: Every federated MCP tool execution must validate:
  `request.auth.claims.sub == resource.owner && request.auth.claims.org_id == resource.org_id`.
- **Metadata SSRF Shielding**: Cloud Run Direct VPC Egress firewall rules must strictly block `169.254.169.254/32` (Google Cloud metadata server).

### 2. Apple App Store & Google Play Review Guidelines
- **Guideline 1.2 (AI UGC Moderation)**: Every AI response bubble in `apps/web` and `apps/mobile` must provide an instant in-app **Flag / Report** button in `ActionBarPrimitive`.
- **Guideline 2.1 (App Completeness & Reviewer Sandbox)**:
  - The login screen (`/login`) must expose the **App Store Reviewer Mode** accordion.
  - Reviewer account `apple-reviewer@workkbot.in` (password: `ReviewerDemo2026!Secured`) must log in instantaneously into the isolated demo organization (`e0000000-0000-0000-0000-000000000002`) without requiring corporate Google SSO or MFA.
- **Guideline 5.1.1 (In-App Account & Memory Erasure)**:
  - The sidebar profile settings menu must provide a destructive **[Delete Account & Purge Memory]** button.
  - Must call `DELETE /api/v1/account/delete`, which invokes `auth.admin.deleteUser(user_id)` and cascades deletion across `profiles`, `user_consents`, `mcp_connections`, and Vault secrets.
- **Guideline 5.1.2(i) & India DPDP Act 2023 Statutory Consent**:
  - Unconsented users must encounter a mandatory blocking interstitial (`ConsentModal`) in English and Hindi itemizing the 4 statutory disclosures before calling `/api/v1/chat`.

---

## 5. Key Code Locations

| Responsibility | Path | Notes |
|---|---|---|
| **FastAPI App Entry** | `apps/backend/src/main.py` | Mounts auth, consent, account routers & `/healthz` |
| **Auth Dependencies** | `apps/backend/src/auth/dependencies.py` | Validates Supabase JWT, extracts `CurrentUser` |
| **Supabase Admin & Vault** | `apps/backend/src/auth/client.py` | Vault pgsodium storage & atomic account deletion |
| **Agentgateway Delegation**| `apps/backend/src/auth/delegation.py` | Upstream token delegation with CEL verification |
| **Reviewer & OAuth Router**| `apps/backend/src/routers/auth.py` | `/reviewer-login`, connector OAuth, connectors list |
| **DPDP Consent Router** | `apps/backend/src/routers/consent.py` | Bilingual statutory disclosures & consent logging |
| **Account Deletion Router**| `apps/backend/src/routers/account.py` | `/api/v1/account/delete` (Apple 5.1.1) |
| **Database Migrations** | `supabase/migrations/` | Versioned PostgreSQL DDL + RLS + Hooks |
| **Agentgateway Config** | `infra/agentgateway/agentgateway.yaml` | CEL policies, anti-poisoning, MCP routes |
| **Shared Schemas** | `packages/shared-types/src/index.ts` | Zod & TS schemas for roles, consents, MCP |
| **Next.js 15 Login** | `apps/web/src/app/login/page.tsx` | Google Workspace SSO & Reviewer Mode |
| **Sidebar Auth Footer** | `apps/web/src/components/sidebar/sidebar-auth-footer.tsx` | Canonical assistant-ui footer & account purge |
| **Hero Greeting** | `apps/web/src/components/chat/chat-hero-greeting.tsx` | State 1 vs. State 2 sunburst serif hero |
| **Floating Composer** | `apps/web/src/components/chat/floating-composer.tsx` | Floating container + mode pill + model selector |
| **Composer Plus Popover** | `apps/web/src/components/chat/composer-plus-popover.tsx`| 8-item hierarchical action popover |
| **Connectors Hub Modal** | `apps/web/src/components/chat/connectors-hub-modal.tsx` | `[ Yours \| Discover ]` card directory & OAuth |
| **DPDP Consent Modal** | `apps/web/src/components/auth/consent-modal.tsx` | Bilingual blocking interstitial |

---

## 6. Verification Checklist for New Changes

Before completing any task or opening a pull request, you **MUST**:
1. Run the backend test suite:
   ```bash
   uv run --python .venv/bin/python pytest -v apps/backend/tests
   ```
2. Verify zero test failures or regressions against the Validation Scorecard (**VAL-01.1** through **VAL-01.9**).
3. Ensure no plaintext secrets are committed or stored outside Supabase Vault.
4. Verify all modified UI components adhere to `@assistant-ui/react` design tokens and responsive layouts.
