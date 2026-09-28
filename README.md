# Workkbot 2.0 ✳

> **Enterprise AI Workspace with Extensible MCP Connectors & Statutory DPDP Compliance**  
> *Built for modern Indian SMBs (<100 seats) on Google Cloud and Supabase.*

---

## 🌟 Overview

Workkbot 2.0 is an enterprise-grade AI conversational platform that combines the agility of modern chat interfaces with strict data isolation, statutory Indian privacy compliance (**DPDP Act 2023**), and **Apple App Store Review Guidelines** adherence.

The architecture is anchored across **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Unified identity (GoTrue), multi-tenant PostgreSQL with Row-Level Security (RLS), and hardware-encrypted **Supabase Vault (`pgsodium`)** for OAuth tokens.
2. **Google Cloud Platform (GCP `asia-south1`)**: Multi-container Cloud Run serverless hosting, Cloud Armor WAF with Indian geofencing, and Direct VPC Egress blocking metadata SSRF.
3. **Google ADK 2.0 (`google-adk`)**: In-process Python agentic runtime driving conversational sessions, `LlmAgent`, and in-stream human-in-the-loop (HITL) confirmations.
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: Canonical conversational design system, floating composer container with 8-item action popover, Connectors Hub modal, and mobile-native parity.
5. **Agentgateway 1.5.x (Rust)**: High-speed agentic data plane on loopback (`127.0.0.1:8080`), federating external MCP tools, evaluating per-session CEL access policies, and mitigating tool poisoning.

---

## 🚀 Key Features (Delivered in Feature 1)

- **Google-Exclusive Authentication & Domain Whitelisting**:
  - One-click Google Workspace sign-in requesting minimal identity scopes (`openid`, `email`, `profile`). Zero mailbox or drive scopes at login.
  - Domain whitelist hook (`public.handle_new_user`) strictly rejecting unauthorized consumer emails (e.g. `@gmail.com`).
- **App Store Reviewer Demo Sandbox (Apple Guideline 2.1)**:
  - Built-in Reviewer Sandbox credentials (`apple-reviewer@workkbot.in`) allowing instantaneous sign-in into an isolated demo tenant without corporate Google SSO.
- **DPDP Act 2023 Statutory Consent (Apple Guideline 5.1.2i)**:
  - Mandatory bilingual (English & Hindi) blocking interstitial itemizing statutory AI and data processing disclosures before unlocking chat.
- **Canonical Assistant-UI Workspace**:
  - Collapsible sidebar with `+ New thread`, date-categorized conversation buckets, and bottom auth footer (`-> Sign in` / employee profile).
  - Floating composer container with segmented mode pill `[ Chat | Cowork ]`, model selector pill (`Gemini 2.0 Flash` / `Pro`), dictation mic, and voice waveform.
  - Hierarchical Plus (`+`) action popover with 8 actions (`⌘U` file uploads, screenshots, skills, connectors, plugins, and web search toggle).
- **Interactive Connectors Hub Modal (`[ Yours | Discover ]`)**:
  - Browse verified MCP connectors: Google Workspace, Zoho Workplace (`accounts.zoho.in`), Notion, Slack, Atlassian, Canva, Figma, HubSpot, and custom MCP endpoints.
  - Symmetrical OAuth 2.0 flow with tokens sealed in **Supabase Vault (`pgsodium`)**.
- **Agentgateway Runtime Token Delegation**:
  - Dynamic token delegation injecting upstream bearer credentials with per-session CEL isolation: `request.auth.claims.sub == resource.owner`.
- **In-App Account & Data Deletion (Apple Guideline 5.1.1)**:
  - Destructive in-app action triggering atomic cascade deletion across Supabase Auth (`auth.admin.deleteUser`), profiles, consent records, and Vault secrets.

---

## 📁 Repository Structure

```text
workkbot/
├── apps/
│   ├── web/                  # Next.js 15 App Router + @assistant-ui/react + Tailwind CSS
│   └── backend/              # Python 3.12 FastAPI + Google ADK 2.0 + Supabase Admin
├── packages/
│   └── shared-types/         # Shared Zod & TypeScript schemas (Roles, Consents, MCP)
├── infra/
│   └── agentgateway/         # Agentgateway 1.5.x configuration & CEL security policies
├── supabase/
│   ├── config.toml           # Supabase CLI configuration
│   ├── migrations/           # SQL migrations (RLS, Vault, Profiles, Consents, Hooks)
│   └── seed.sql              # Development and Reviewer Sandbox seed data
├── gemini-specs/             # Living technical specifications & Constitution
├── pnpm-workspace.yaml       # Workspace definition
├── turbo.json                # Turborepo task pipeline
└── package.json              # Monorepo root scripts
```

---

## 🛠️ Getting Started

### Prerequisites
- **Node.js**: v20+ (v24 recommended)
- **Python**: v3.11+
- **uv**: Fast Python package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **pnpm**: Monorepo package manager (`corepack enable pnpm`)

### 1. Python Backend Setup (uv)
From the repository root:
```bash
# Sync dependencies and development tools (pytest, etc.)
uv sync --extra dev

# Run automated test suite (14 checks for VAL-01.1 through VAL-01.9)
uv run pytest

# Launch FastAPI Backend Dev Server on Port 8000
uv run uvicorn src.main:app --app-dir apps/backend --reload --port 8000
```

*(Alternatively, if working inside `apps/backend/`)*:
```bash
cd apps/backend
uv sync --extra dev
uv run pytest
uv run uvicorn src.main:app --reload --port 8000
```

### 2. Web Frontend Setup (pnpm)
If `pnpm` is not yet installed on your system:
```bash
npm install -g pnpm
# or: brew install pnpm
```

From the repository root:
```bash
# Install workspace dependencies
pnpm install

# Launch Next.js 15 dev server on Port 3000
pnpm --filter @workkbot/web dev
```

---

## 🔒 Security & Statutory Invariants

- **Zero Plaintext Tokens**: All third-party OAuth access and refresh tokens are encrypted into Supabase Vault via `pgsodium`.
- **Zero Cross-Tenant Leakage**: Supabase Row-Level Security (RLS) and Agentgateway Common Expression Language (CEL) policies ensure strict isolation.
- **DPDP Act 2023 Localization**: Compute and data services reside strictly in Mumbai (`asia-south1` / `ap-south-1`).
- **Apple & Google Play App Approval**: Pre-built compliance with Apple Guidelines 1.2 (AI report flag), 2.1 (Reviewer Sandbox), 5.1.1 (In-app account deletion), and 5.1.2i (AI consent).

---

## 📄 License

Proprietary — All rights reserved © 2026 Workkbot India.
