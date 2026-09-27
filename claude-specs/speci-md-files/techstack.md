# Constitution: Tech Stack & Architecture

## 1. Architectural Overview

Monorepo (pnpm workspaces + Turborepo), five planes: client, API/orchestration (fronting an ADK 2.0 Runner), tool, execution (sandbox), and data.

```text
enterprise-assistant/
├── apps/
│   ├── web/                 # Next.js (App Router) chat + admin web client
│   ├── mobile/               # React Native (Expo) native app
│   ├── api/                  # Thin web API: auth, routing, SSE/WS fan-out (NestJS/Fastify)
│   ├── agent-runtime/         # Python ADK 2.0 app: Runner, Agent(s), Callbacks, tool wiring
│   ├── mcp-gateway/          # Per-user OAuth token store + tool permissioning in front of McpToolset
│   ├── sandbox-worker/       # Wraps the code-execution vendor SDK (E2B), exposed as an ADK tool
│   └── admin/                # Admin console (may be a route group inside web/ instead)
├── packages/
│   ├── ui/                   # Shared React component library
│   ├── design-tokens/        # Shared colors/spacing/typography
│   ├── api-client/           # Typed SDK generated from api/agent-runtime schemas
│   ├── shared-types/          # Message, Session, Tool, Skill, Artifact types/schemas
│   ├── memory-schema/         # Shared schema/validation for memory records
│   ├── eslint-config/
│   └── tsconfig/
├── skills/                   # Versioned skill/plugin content (markdown + scripts), not code
├── infra/                    # IaC (Terraform/Pulumi), Docker files, CI configs
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

## 2. Core Dependencies & Versions
- **Language & Runtime**: TypeScript 5.x (`web`, `mobile`, `api`, `admin`); Python 3.12 (`agent-runtime`, `mcp-gateway`, `sandbox-worker`)
- **Agentic harness**: Google ADK 2.0 (pin an explicit minor version; do not float `latest`) — Runner, `LlmAgent`, `SequentialAgent`/`ParallelAgent`/`LoopAgent`, graph-based `Workflow`, `McpToolset`, Callbacks, `BaseMemoryService`, Artifact Service
- **Web framework**: Next.js (App Router)
- **Mobile framework**: React Native via Expo (managed workflow, EAS Build/Submit)
- **Backend API framework**: NestJS or Fastify (web-facing `api`); FastAPI-style ASGI wrapper only if `agent-runtime` needs a raw HTTP surface beyond ADK's own server
- **UI/styling**: Tailwind CSS + shadcn/ui (Radix primitives)
- **State/data (web)**: TanStack Query (server state) + Zustand or React context (client/streaming state) — no Redux
- **Auth**: OIDC against the org's existing IdP (Entra ID / Okta / Google Workspace) via Auth.js or WorkOS AuthKit — never a hand-rolled auth system
- **Database**: PostgreSQL (single managed primary), `pgvector` extension enabled — also backs ADK's `DatabaseSessionService`
- **Cache / pub-sub**: Redis
- **Object storage**: S3-compatible bucket (S3, R2, or GCS) — backs ADK's Artifact Service
- **Model providers**: Anthropic / OpenAI / Gemini via ADK's model abstraction — no provider-specific code outside that abstraction
- **Code-execution sandbox**: E2B (Firecracker microVMs) as the default vendor; Daytona/Modal/Beam are acceptable substitutes; the GCP-only Vertex AI Agent Engine Sandbox is explicitly excluded to avoid cloud lock-in
- **Testing & verification**: Vitest/Playwright (TS apps), Pytest (`agent-runtime`), ADK's own evaluation tooling (`adk eval`, `RubricBasedMultiTurnTrajectoryEvaluator`) for agent-behavior regression tests

## 3. Architectural Constraints & Code Rules
1. **Separation of concerns**: `api` never talks to the model provider, memory store, or MCP servers directly — every agentic operation flows through `agent-runtime`. `agent-runtime` never serves the web/mobile client directly — it is only ever called by `api`.
2. **ADK is the harness, not the product**: auth, org/role model, tool-permission *policy*, the HITL approval gateway, the admin console, and the audit log are hand-built and owned by this codebase — never assume ADK provides them.
3. **Session/memory persistence rules**: ADK's `DatabaseSessionService` and Artifact Service are the source of truth for session/event and binary-artifact state respectively — do not duplicate their internals into hand-written tables. A separate, deliberately thin `conversations` summary table (populated via an `after_agent` callback) exists solely for admin/search use, not as a second source of truth.
4. **Multi-tenancy**: every hand-written table carries `org_id` and a Postgres RLS policy, even before a second tenant exists.
5. **Secrets**: OAuth tokens (`tool_connections`) are encrypted at rest via KMS-backed column encryption or a secrets manager — plaintext token columns are a constitution violation, not a style nit.
6. **HITL is mandatory, not optional, for write-capable tools**: any tool tagged as a critical/write action must route through the `pending_approvals` gateway (Section 5.8 of the architecture report) before execution — do not rely on ADK's built-in tool-confirmation alone, since it does not yet support `DatabaseSessionService` in production.
7. **Workflow-pattern discipline**: default to a single `LlmAgent` for ordinary chat and tool use; only introduce a coordinator/sub-agent pattern, a deterministic template workflow, or a graph-based workflow when the task shape genuinely requires it (see the architecture report's task-shape table) — do not add orchestration complexity to the core chat path speculatively.
8. **Code quality**: TypeScript apps use the shared `eslint-config`/`tsconfig` packages, no local overrides without a documented reason; Python apps use `ruff`/`black` and type-check with `mypy` or `pyright`.
