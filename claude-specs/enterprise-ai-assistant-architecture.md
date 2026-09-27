# Enterprise AI Assistant Platform — Architecture Report
### A ChatGPT/Claude-style assistant for offices under 100 seats
*Prepared September 2026 — updated to adopt Google ADK 2.0 as the agentic harness*

---

## 1. Executive summary

You're building an internal "ChatGPT-style" assistant: chat UI, MCP tool connectors, login/auth, persistent sessions, long-term memory, skills, plugins, and Artifacts (generative UI / code execution). Target scale is **under 100 employees** — meaning you should optimize for low operating cost, low ops burden, and fast time-to-value over hyperscale distributed-systems complexity. Most "enterprise AI platform" reference architectures are written for thousands of seats; at <100 seats, a large fraction of that complexity (Kafka, service mesh, multi-region, dedicated MLOps team) is waste. This report gives you a right-sized architecture, plus what to upgrade if you outgrow it.

**This revision swaps the hand-built "conversation orchestrator" for Google's Agent Development Kit (ADK) 2.0** as the agentic harness — it supplies Sessions, Memory, Tools/MCP integration, Callbacks, Artifacts, and (new in 2.0) a multi-agent workflow engine as pluggable primitives, so you're wiring services together rather than hand-rolling an event loop. Section 5.1 explains what ADK replaces vs. what you still build yourself; Section 5.8 covers human-in-the-loop approval for critical actions (and a real gap in ADK's built-in mechanism you need to design around); Section 5.9 maps chat vs. multi-step task shapes onto the right ADK workflow pattern.

**Recommended stack at a glance:**

| Layer | Recommendation |
|---|---|
| Monorepo tooling | pnpm workspaces + Turborepo |
| Web frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui |
| Native mobile | React Native (Expo) sharing logic with web via a shared package |
| Backend API | Node.js (NestJS/Fastify) for the web-facing API; **Python for the agent runtime**, since ADK is Python/Java/Go/Kotlin/TS-native and the ecosystem (tools, samples, memory backends) is deepest in Python |
| **Agentic harness** | **Google ADK 2.0** — Runner + Sessions + Memory + Tools/MCP + Callbacks + Artifacts + multi-agent workflow engine |
| Realtime/streaming | WebSockets or SSE from backend, no separate realtime vendor needed at this scale |
| Auth | OIDC via your existing IdP (Entra ID / Okta / Google Workspace) + a library like Auth.js/WorkOS AuthKit — do **not** build your own auth |
| Database | Postgres (single managed instance) with `pgvector` for embeddings; also backs ADK's `DatabaseSessionService` |
| Cache/session store | Redis |
| Object storage | S3-compatible bucket (S3, R2, or GCS) — backs ADK's Artifact Service |
| LLM access | Model provider API (Anthropic/OpenAI/Gemini) called through ADK's model abstraction — ADK is multi-provider, not Gemini-only, including native support for Anthropic's extended-thinking blocks |
| MCP tool layer | ADK's built-in `McpToolset` for the client/connection side; a thin permissions layer of your own in front of it (Section 5.5) |
| Code execution / Artifacts sandbox | Firecracker-based managed sandbox (e.g., E2B) invoked as an ADK tool — kept vendor-neutral rather than adopting ADK 2.0's GCP-only Agent Engine Sandbox |
| Deployment | Single-region managed platform (Vercel/Fly.io/Railway for app tier + ADK Runner container, managed Postgres/Redis) behind your VPN or SSO gate |

---

## 2. What "state of the art" looks like in 2026 (research findings)

A few engineering shifts matter directly for your design:

- **Memory is now a first-class subsystem, not a prompt trick.** The industry has moved from "stuff a profile summary into the system prompt" toward dedicated memory layers with distinct memory *classes*: episodic (what happened), semantic (facts/preferences), and procedural (learned workflows — how *this* team writes PRs, runs tests, formats reports). Frameworks like Mem0/Zep treat memory as its own service with its own retrieval and write path, separate from the chat transcript. Several commentators describe 2026 as the year memory became "a moat" rather than a nice-to-have, since context that has to be re-established every session is a measurable productivity tax.
- **MCP has become the default integration standard**, not a niche protocol. It's now adopted across Anthropic, OpenAI, Google, Microsoft, and AWS, with tens of thousands of public servers in production. The architectural pattern that has emerged is a three-layer split: **host** (your app), **client** (the connection manager inside your app), and **server** (the tool/data provider — Slack, Jira, your internal systems). The emerging enterprise best practice is to put a **gateway in front of MCP servers** that does SSO-integrated auth, per-tool role-based permissioning, and audit logging — because an agent that can call arbitrary tools is a much bigger blast radius than a chatbot that can only talk.
- **MCP vs. A2A is a boundary decision, not a competition.** MCP standardizes how one app calls tools/data. A2A (agent-to-agent) standardizes how independent agents delegate objectives to each other. At <100 seats you almost certainly only need MCP — A2A becomes relevant if you later spin up autonomous agents that need to hand off work to each other without your app owning the whole loop.
- **Prompt injection via tool outputs is treated as the top agentic security risk**, above classic jailbreaks. Any content an MCP tool reads (a web page, an email, a ticket body) is untrusted input that can try to redirect the agent. The mitigation isn't smarter prompting — it's **scoping what each tool call is allowed to do** (least privilege, explicit user confirmation for write actions, structured tool schemas) rather than relying on the model to "notice" the injection.
- **Code execution ("Artifacts"-style generative UI/analysis) has converged on microVM sandboxes**, not raw containers. Docker namespaces alone are considered insufficient isolation for untrusted, LLM-generated code. The two production-proven approaches are Firecracker microVMs (AWS Lambda's own tech, ~125ms cold boot, dedicated kernel per sandbox) and gVisor (user-space kernel interception, slightly faster cold start, slightly weaker isolation). For a <100-seat org, renting this capability from a vendor (E2B, Daytona, Modal) is far cheaper than operating Firecracker yourself — self-hosting only pays off past a certain volume of code-execution sessions per day.
- **"Skills" and "plugins" are converging on the same pattern across vendors**: a skill is a markdown/instruction bundle (+ optional scripts) that's loaded on demand rather than kept permanently in context, and a plugin bundles a skill with the MCP tools and slash-commands it needs. The engineering lesson is to keep these as **data, not code** — store them as versioned content (files/DB rows) that a "skill router" retrieves and injects, so non-engineers can author them without a deploy.
- **Agentic harnesses have matured into a standard set of primitives**, and Google's ADK is a good example of where the whole category converged: **Sessions** (conversation state + event log), **Memory** (long-term knowledge across sessions, pluggable backend), **Tools** (function tools, MCP toolsets, OpenAPI tools, tool auth and human-confirmation), **Callbacks** (hooks before/after the agent, the model call, and each tool call), **Artifacts** (binary/file persistence separate from the conversation transcript), and — new in **ADK 2.0 (GA)** — a **multi-agent workflow engine** with graph-based execution and native inter-agent routing, plus `AutoTracingPlugin` for OpenTelemetry, support for Anthropic's thinking blocks, and A2A protocol support for delegating to (or being called as) another agent. The practical implication for you: this is no longer a component worth hand-rolling — it's the same "buy vs. build" call as auth, and the harness is the "buy."
- **ADK's built-in tool-confirmation feature is real but explicitly experimental, with a specific, documented production gap**: as of the current release line, it does not support the two session backends meant for production (`DatabaseSessionService`, `VertexAiSessionService`), doesn't trigger inside a wrapped `AgentTool` or across A2A boundaries, and ships with no structured approval UI, audit trail, or persistence layer of its own — community patches exist (a session-agnostic "HITL approval gateway" pattern) precisely because teams hit this gap trying to go to production. There's also an open, publicly disclosed class of bug where a forged confirmation event (one not actually checked as originating from the model, or relayed across an A2A boundary) can trick the confirmation processor into running a tool without genuine human approval — worth designing around rather than trusting the raw mechanism as-is (Section 5.8).
- **Workflow orchestration in ADK has two distinct tiers, and picking the wrong one for the job is the most common design mistake**: deterministic "template" workflow agents (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) for known, fixed-shape pipelines, versus LLM-driven dynamic routing (a coordinator agent delegating via `transfer_to_agent` or `AgentTool`) for anything where the next step depends on reasoning about the request. ADK 2.0 adds a third, more general option — **graph-based workflows** — as the explicit successor to nesting template agents once you need conditional branching, mixed code/agent/tool/human-input steps, or precise control that a purely prompt-driven agent can't guarantee (Section 5.9).

---

## 3. High-level system architecture

Five planes, each independently scalable but simple enough that at <100 seats it can run as 3–5 deployable services rather than dozens of microservices:

1. **Client plane** — Next.js web app, React Native mobile app, both talking to the same API.
2. **API/orchestration plane** — a thin web API (auth verification, request routing, SSE/WebSocket fan-out) in front of an **ADK Runner** process that owns the actual agent loop: session/state management, memory read/write, calling the model provider, and dispatching tool calls.
3. **Tool plane** — ADK's `McpToolset` (the MCP *client*) plus the actual MCP servers (Slack, Google Workspace, internal ticketing, custom internal-data connectors), fronted by your own thin permissions/audit layer.
4. **Execution plane** — the sandboxed code-execution service that powers Artifacts (charts, generated mini-apps, file conversions), wired in as an ADK tool.
5. **Data plane** — Postgres (relational + vector; also backs ADK's session/event storage), Redis (cache/streaming pub-sub), object storage (uploads, generated files, artifact bundles — backs ADK's Artifact Service).

A request's life cycle: client authenticates via your IdP → the web API verifies the session and forwards the message to the ADK Runner → the Runner loads session state and injects relevant memory + skills via a `before_agent`/`before_model` callback → the agent streams a completion from the model provider → if the model requests a tool call, ADK's tool layer invokes it (running it through your permissions check and, for write actions, a confirmation step) → if the model wants to run code or render a UI, an ADK tool hands that off to the execution plane → results stream back to the client, and an `after_agent` callback writes anything durable (facts learned, artifacts produced) back to the data plane via the Memory and Artifact services.

---

## 4. Monorepo layout

Use **pnpm workspaces + Turborepo** (not Nx) for a team this size — Turborepo's single `turbo.json` and reliance on the package manager's native workspace feature is dramatically less to operate than Nx's full platform, and Nx's extra power (generators, dependency-graph tooling, distributed task execution) only pays off once you have 50+ internal packages or a platform team dedicated to tooling.

```
enterprise-assistant/
├── apps/
│   ├── web/                  # Next.js chat web app
│   ├── mobile/                # React Native (Expo) app
│   ├── api/                   # Thin web API (auth, routing, SSE/WS fan-out) — NestJS/Fastify
│   ├── agent-runtime/          # Python ADK app: Runner, agent/sub-agent defs, callbacks, tool wiring
│   ├── mcp-gateway/           # Per-user OAuth token store + tool permissioning in front of ADK's McpToolset
│   ├── sandbox-worker/        # Wraps the code-execution vendor SDK (E2B, etc.), exposed to ADK as a tool
│   └── admin/                 # Internal admin console (user/tool/skill management)
├── packages/
│   ├── ui/                    # Shared React component library (web + admin; RN uses its own primitives but shares tokens)
│   ├── design-tokens/         # Colors, spacing, typography shared across web/mobile
│   ├── api-client/            # Typed SDK generated from the API's OpenAPI/tRPC schema, used by web + mobile
│   ├── shared-types/           # Zod/TypeScript types shared across all apps (Message, Session, Tool, Skill, Artifact)
│   ├── memory-schema/          # Shared schema + validation for memory records
│   ├── eslint-config/
│   └── tsconfig/
├── skills/                    # Versioned skill/plugin content (markdown + scripts), loaded by agent-runtime, not code
├── infra/                     # IaC (Terraform/Pulumi), Docker files, CI configs
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

`agent-runtime` is the one Python app in an otherwise TypeScript monorepo — that's expected, not a smell: pnpm workspaces happily coexist with a Python app as long as it isn't part of the JS dependency graph. Point Turborepo at it with a thin `package.json` wrapper (scripts that shell out to `uv`/`poetry`) so it still participates in `turbo run build/test` even though its actual dependency management is Python-native.

Key rules that keep this maintainable:
- **`packages/shared-types` is the contract.** Define your `Message`, `Conversation`, `ToolCall`, `MemoryItem`, and `Artifact` types once; every app imports from there. On the Python side, mirror the same shapes as Pydantic models (generated from the same JSON Schema, or kept in sync by hand at this scale) so `agent-runtime`'s event payloads match what `web`/`mobile` expect.
- Prefer a **typed API client generated from the backend's schema** (tRPC for the `api` app, OpenAPI-generated for `agent-runtime`) over hand-writing fetch calls in three different apps.
- Keep **skills/plugins as content, not code** in their own top-level folder, loaded at runtime by `agent-runtime` — this lets you iterate on assistant behavior without a full app deploy, and lets non-engineers (ops, support leads) contribute skills via PR review.
- Use **Turborepo remote caching** from day one (even the free tier) — with 3–5 apps sharing packages, cache hits meaningfully shorten CI once the repo grows past a few dozen commits a week.

---

## 5. Backend design

### 5.1 Language/framework choice, and where ADK 2.0 fits

Adopting ADK settles a decision from the earlier revision of this plan: **the agent runtime is Python**, because ADK is Python-first (also available in Java, Go, Kotlin, TypeScript, but the tool/sample/memory-backend ecosystem is deepest in Python). Your web-facing API can stay in Node/TypeScript if that's your team's strength — it just becomes a thinner layer that authenticates requests and proxies them to the ADK Runner over HTTP/gRPC, rather than the thing that runs the chat loop.

**What ADK 2.0 replaces vs. what you still build:**

| Concern | Before (hand-built) | With ADK 2.0 |
|---|---|---|
| Chat loop / event loop | Custom orchestrator code | ADK **Runner** — a production-grade event loop connecting your Agent, Tools, and Callbacks; you configure it, you don't write it |
| Conversation state | Custom `conversations`/`messages` tables, hand-rolled | ADK **Session** + **Event** model, persisted via `DatabaseSessionService` pointed at your Postgres |
| Long-term memory | Custom memory service, hand-rolled retrieval | ADK **Memory** service interface (`BaseMemoryService`) — you implement one backend (Section 5.4), not the whole read/write/inject pipeline |
| Tool calling / MCP | Custom MCP gateway proxying calls | ADK's `McpToolset` (the MCP client), plus built-in **tool auth schemes and tool confirmations** (human-in-the-loop approval) — you still own *permissions policy*, not the plumbing |
| Cross-cutting hooks (audit, redaction, cost tracking) | Ad hoc middleware | ADK **Callbacks** (`before/after_agent`, `before/after_model`, `before/after_tool`) and **Plugins** (global hooks across every agent) |
| Binary/file output (Artifacts) | Custom `artifacts` table + storage glue | ADK **Artifact Service**, backed by your S3-compatible bucket |
| Multi-agent workflows | N/A — you'd have hand-rolled routing | ADK 2.0's **Multi-Agent Workflow Engine** — graph-based execution graphs and native inter-agent routing, for when a skill needs to become a real sub-agent (Section 5.6) |
| Auth, org/role model, admin UI, tool-permission policy, audit storage, billing/usage dashboards | You build these | **Still you build these** — ADK is an agent harness, not an enterprise app platform |

That last row matters: ADK gives you the agent's internals, not your product. You still need the web API, auth, admin console, and the permissioning *policy* layer described throughout this report — ADK just means you're no longer writing a bespoke event loop, session store, and memory-injection pipeline to get there.

Structure the backend as a small number of services, same count as before, with responsibilities shifted:

| Service | Responsibility |
|---|---|
| **Auth/session service** | Validates IdP tokens, issues app sessions, manages refresh, enforces org/role scoping |
| **Agent runtime (`agent-runtime`)** | Hosts the ADK **Runner**: agent/sub-agent definitions, Session/Memory/Artifact service wiring, callbacks, and the model-provider connection. This *is* the conversation orchestrator now. |
| **Memory backend** | Your `BaseMemoryService` implementation (Postgres + `pgvector`, or Mem0/Redis-backed) that ADK's Memory interface calls into |
| **MCP gateway** | Holds per-user OAuth tokens for connected tools and enforces per-tool/per-role permissions *in front of* ADK's `McpToolset`; ADK handles the protocol plumbing and confirmation UX, you still own the policy and the audit log |
| **Skills/plugins service** | Resolves which skills/plugins apply to a request, retrieves and injects skill content via a `before_model` callback (or promotes a skill to a full ADK sub-agent), exposes an admin API for managing the skill catalog |
| **Execution/artifacts service** | Talks to the sandbox vendor SDK, exposed to the Runner as a plain ADK `FunctionTool`; results are written through ADK's Artifact Service into your object store |
| **Admin service** | User management, tool connection management, usage/cost dashboards, audit log viewer |

At <100 seats, `agent-runtime` and the MCP gateway can run as two processes (Python + whatever fronts it) rather than a sprawl of microservices — keep the module boundaries clean so a future split is a config change, not a rewrite.

### 5.2 Auth, sessions, and multi-tenancy
- **Don't build auth.** Federate to the company's existing identity provider via OIDC/SAML (Entra ID, Okta, Google Workspace) using a library like Auth.js, WorkOS AuthKit, or your framework's OIDC middleware. This gets you SSO, MFA, and deprovisioning-on-offboarding for free, which matters a lot for a security review at a company this size.
- Session tokens: short-lived JWT access token (10–15 min) + refresh token stored `httpOnly`/`secure`, rotated on use. Store the refresh-token family in Redis so you can revoke a whole session tree instantly (lost laptop, offboarding).
- Even at one company, model it as **single-tenant-per-deployment** if you're building this once for your own org, or **row-level multi-tenant** (an `org_id` on every table + Postgres RLS policies) if you might resell it or host multiple business units. RLS is cheap to add now and painful to retrofit later — add it even if you only have one tenant today.
- **Roles**: keep it simple — `member`, `tool-admin` (can approve/connect new MCP tools), `org-admin` (billing, user management, audit log access). Map these to IdP groups rather than inventing a separate permission UI.

### 5.3 Conversation state and streaming
- Use ADK's **`DatabaseSessionService`** pointed at your existing Postgres instance as the source of truth for session/event state — it persists ADK's Session and Event objects via SQLAlchemy, so you're not hand-rolling the message-persistence layer. Note ADK 2.0's sessions are readable by ADK 1.28+ but not older 1.x — pin your version and don't mix.
- ADK's Session/Event schema is optimized for replaying and driving the agent, not for cross-user analytics or admin search. Keep a thin `conversations` summary table of your own (title, org_id, user_id, last-message-at) populated via an `after_agent` callback, so the admin console and search don't have to query ADK's internal tables directly. This is the one place where you deliberately keep a bit of duplication rather than forcing everything through one schema.
- Stream tokens to the client over **SSE** (simpler, proxies/CDNs handle it better) or a WebSocket if you need bidirectional push (e.g., mid-stream tool-approval prompts, which ADK's tool-confirmation flow can trigger).
- Use Redis as the **pub/sub backbone** between the `agent-runtime` process handling the model call and whichever process/socket is holding the client connection — this is what lets you scale to multiple Runner instances without sticky sessions being a hard requirement.
- Conversation branches (edits/regenerations) map onto ADK's Session/Event log naturally, since each edit or regeneration is just a new Event referencing its parent — you get the ChatGPT-style edit/regenerate tree without inventing your own schema for it.

### 5.4 Memory architecture

ADK defines memory behind a `BaseMemoryService` interface with an `add_session_to_memory` write path and a `load_memory`/`preload_memory` tool for retrieval — you pick the backend. ADK ships three options out of the box, and none of them is quite your answer by itself:

- **`InMemoryMemoryService`** — dev/test only, gone on restart.
- **`VertexAiMemoryBankService`** — Google's managed, semantic-search-backed memory store. Turnkey, but it's GCP-only, and you've deliberately kept the model layer multi-provider (Anthropic/OpenAI/Gemini) — adopting it would quietly re-introduce the GCP lock-in you avoided elsewhere in this stack.
- **Third-party backends** (e.g., Mem0's ADK integration, or the Redis-backed `adk-redis` package) — real options if you'd rather not maintain a memory backend at all.

**Recommended for your case: implement a small custom `BaseMemoryService` backed by the Postgres + `pgvector` you're already running.** It's a thin adapter, not a new system — `add_session_to_memory` writes structured facts (same `subject`/`predicate`/`object`/`confidence`/`source_message_id` shape as before) plus an embedding; retrieval does a vector search scoped to the user/org. This keeps memory on the same database as everything else, avoids both GCP lock-in and a new vendor dependency, and still gets you ADK's orchestration around *when* memory is written and injected — you're just supplying the storage.

Keep the same three memory classes conceptually, now expressed as ADK plumbing:

1. **Episodic (session) memory** — this is just ADK's Session/Event log (Section 5.3); nothing extra to build.
2. **Semantic memory** — your custom `BaseMemoryService` above. Trigger the write asynchronously via an **`after_agent` callback** (`callback_context.add_session_to_memory()`), not synchronously in the hot path — this keeps latency down and is a natural place to insert a human/review gate before something sensitive gets remembered.
3. **Procedural memory** — still a special class of **skill**, not something ADK's memory service auto-mines from transcripts; keep it in `skills/` and load it the same way as other skills (Section 5.6).

Retrieval on each turn: attach ADK's `preload_memory` (or `load_memory`) tool to the agent so the model decides when to pull memory, or inject top-K semantic facts unconditionally via a `before_model` callback if you want deterministic recall rather than model-initiated lookup — the latter is usually the better default for an internal assistant where you want memory use to be predictable and auditable. Keep the injected memory budget small (a few hundred tokens) and visible to the user (a "memory used" panel).

`pgvector` on your existing Postgres instance is still enough at this scale — you do not need a dedicated vector database (Pinecone/Weaviate/Qdrant) until you're indexing many millions of chunks or need sub-20ms ANN search at high QPS, neither of which applies at <100 seats, and it means your custom `BaseMemoryService` has no new infrastructure to operate.

### 5.5 MCP tool layer
- ADK's **`McpToolset`** is the MCP *client* — point it at each MCP server (Slack, Jira, Google Drive, your internal wiki, a custom internal-tools server you write) and it handles the protocol plumbing, including auth-scheme/credential support and tool discovery. This replaces the hand-built proxy layer from the earlier version of this plan.
- ADK also has a **built-in tool-confirmation mechanism** — a tool can be marked as requiring human approval before it executes, which is exactly the "approve" step any *write* action needs (sending an email, creating a ticket, modifying a record). Use it instead of building your own approval-prompt plumbing; you still decide *which* tools require it and for which roles.
- What you still build: a **thin permissions/audit layer** sitting between your per-user OAuth token store and ADK's `McpToolset` — which roles can use which tool, and a `before_tool`/`after_tool` **callback pair** that logs every invocation (who, what tool, what arguments, what result, latency) to your `tool_invocations` table. ADK gives you the hook points; the policy and the audit log are yours.
- Treat every tool *result* as untrusted data that flows back into the model's context — this is where prompt injection lives. A `before_model` or `after_tool` callback is a reasonable place to run a lightweight content check on tool output before it re-enters the prompt, but don't rely on the model to "notice" an injection — permissions and confirmations (server-side) are the real control, not model judgment.
- For internal systems with no existing MCP server, write thin custom MCP servers (a Node/Python process implementing the MCP spec) rather than giving the model raw API keys — `McpToolset` will happily connect to a server you wrote yourself the same way it connects to a third party's.

### 5.6 Skills and plugins

One naming note: **ADK's own "Plugin" concept is different from the product-level "skills/plugins" in this report** — an ADK Plugin is a global hook across every agent (used for things like the built-in `AutoTracingPlugin`, or an internal one you write for org-wide cost tracking or PII redaction), whereas *your* skills/plugins are user-facing capability bundles. Don't conflate the two; you'll likely use both.

- **Skill** (your concept) = a folder of instructions (+ optional helper scripts) with a manifest describing what triggers it (keywords, task type). Loaded on demand, not always-on — inject it via a `before_model` callback in `agent-runtime` rather than a separate always-running service, since ADK's callback already sits at the right point in the loop.
- **Plugin** (your concept) = a skill bundled with the MCP tools/connectors and slash-commands it needs, packaged so an admin can enable it for their org/team with one click.
- Build a small **skill router**: given the incoming message + conversation context, retrieve the top few candidate skills (keyword match is enough at this scale; embedding-based retrieval is a nice upgrade later) and inject only those via the callback above. Log which skills fired so you can tune triggering over time.
- **Upgrade path with ADK 2.0's Multi-Agent Workflow Engine**: a skill that just needs different instructions is a prompt-injected skill as above; a skill that needs its *own* tool access, its own model choice, or should run somewhat independently (e.g., a "deep research" skill that does multiple search/read passes before returning) is a good candidate to graduate into a real **ADK sub-agent** with graph-based routing to it, rather than stretching prompt injection to cover it. You don't need this on day one — start every skill as prompt content, and only promote the handful that outgrow it.
- Use an **ADK Plugin** (the global-hook kind) for the cross-cutting concerns that apply regardless of which skill fired: audit logging, cost/usage tracking, and PII/secret redaction on tool output. This is a better home for these than duplicating the same callback on every individual agent.
- Store skills as versioned files in the repo (or a simple CMS/DB table if you want non-engineers editing without PRs) — either way, version them, because a bad skill edit should be revertable like code.

### 5.7 Artifacts / code execution
- ADK has a native **Artifact Service** for binary/file persistence, separate from the conversation transcript — back it with your S3-compatible bucket rather than building your own storage glue. This is the natural home for generated charts, files, and mini-app bundles.
- **Don't adopt ADK 2.0's new Vertex AI Agent Engine Sandbox** (added for "computer use") as your code-execution layer unless you're fully committing to GCP — it's a GCP-managed offering, and you've deliberately kept the model/infra layer provider-agnostic elsewhere in this plan. Keep renting the sandbox from a portable vendor instead: a managed Firecracker-based provider (E2B is the most chatbot-oriented; Daytona/Modal/Beam are alternatives if you need GPU or want a self-hostable option later), wired into `agent-runtime` as a plain ADK `FunctionTool` that calls the vendor's SDK.
- Each artifact request (a generated chart, a small interactive tool, a data-analysis script) gets its own short-lived sandbox session: mount only the files it needs, no persistent secrets in the sandbox image, network egress restricted to an allowlist (or fully disabled for pure compute), and the session is destroyed after the task completes or after a short idle timeout (minutes, not hours).
- Rendered artifacts (HTML/SVG/generated files) get written through ADK's Artifact Service into object storage and served back to the client through a signed URL — never execute or render untrusted HTML in the same origin as your main app; use a separate subdomain/sandboxed iframe origin so a malicious artifact can't read your app's cookies or call your API with the user's session.
### 5.8 Human-in-the-loop (HITL) for critical actions

Every "write" action a tool can take — send an email, delete a record, spend money, modify a user, execute code with real side effects — needs an explicit human approval gate before it runs. ADK gives you a real mechanism for this, but with a gap worth designing around rather than adopting blindly:

- **What ADK gives you**: `ToolContext.request_confirmation()` lets a tool pause mid-call and emit a synthetic `adk_request_confirmation` event; the tool only actually runs once a matching `function_response` with `{confirmed: true}` shows up. There's also an "advanced" form that can request structured input (not just yes/no) alongside the confirmation.
- **The gap that matters for you**: this feature is explicitly experimental, and as of the current release does **not support `DatabaseSessionService`** — the exact session backend this plan puts on your Postgres instance (Section 5.3). It also doesn't reliably trigger inside a tool wrapped as an `AgentTool`, and has no built-in approval UI, audit trail, or durable persistence of its own. Building on the raw mechanism today means building on something that doesn't yet support your production session store.
- **What to build instead**: a small, **session-agnostic HITL approval gateway** that owns its own persistence, independent of ADK's session service — the same shape the community has already converged on to patch this gap. Concretely:
  - A `pending_approvals` table in your existing Postgres (id, org_id, requested_by_tool, tool_args, requesting_user_id, status [pending/approved/denied/expired], decided_by, decided_at, expires_at).
  - A `before_tool` callback that checks whether the tool being called is on your "critical action" list (a config flag on the tool, not a hardcoded list scattered through code) and, if so, writes a `pending_approvals` row and halts instead of calling the tool.
  - A small approval UI (in the web app or a Slack/email notification) that surfaces the pending request to someone with the right role, and on approval/denial resumes the agent run via ADK's standard resume API.
  - Treat this the same way you'd treat any other durable async workflow (a webhook, a queued job) rather than trying to keep it alive in-memory across the wait — approvals can and will sit pending for hours.
- **Security detail worth building in deliberately**: there's a documented issue class where a confirmation event isn't checked as having actually been emitted by the model for *that* tool call, and where a confirmation relayed across an agent-to-agent boundary can be used to self-approve a dangerous call (a "confused deputy" pattern). Your gateway should independently verify that (a) the pending-approval record it's resolving was created by your own `before_tool` callback for this exact session and tool-call id, and (b) the approval decision arrives over an authenticated channel tied to a real user with the approver role — never accept a confirmation that arrived embedded in tool output, another agent's message, or an A2A payload. You don't need A2A at your scale (Section 2), which conveniently removes that specific attack surface entirely for now.
- Log every approval decision to the same `tool_invocations` audit trail as the rest of Section 5.5 — who requested it, who approved/denied it, and when, is exactly the kind of record a security review will ask for.

### 5.9 Which ADK workflow pattern to use, from chat to multi-tool tasks

ADK gives you several ways to structure execution, and matching the pattern to the task shape matters more than defaulting to the most powerful one everywhere:

| Task shape | Pattern | Why |
|---|---|---|
| **Ordinary chat, including turns with one or several tool calls** | A single **`LlmAgent`** with tools attached, using ADK's normal function-calling loop — no orchestration wrapper at all | This is the vast majority of your traffic. The model decides which tool(s) to call and in what order; you don't know the shape ahead of time, so a deterministic pipeline would only get in the way. This is the default — reach for anything below only when this stops being enough. |
| **Routing to a specialist skill/sub-agent** (once a skill has graduated per Section 5.6) | **Coordinator/dispatcher pattern**: a root `LlmAgent` with `sub_agents`, using either LLM-driven `transfer_to_agent` (the model decides to hand off) or wrapping the specialist as an `AgentTool` (treating it as a callable the root agent invokes like any other tool) | `transfer_to_agent` suits genuine hand-offs where the sub-agent takes over the rest of the turn; `AgentTool` suits hierarchical decomposition where the root agent stays in control and just delegates one sub-task. Pick per skill, not globally. |
| **A known, fixed-shape multi-step task** (e.g., a scheduled report, an onboarding checklist, invoice processing) where every run does the same steps in the same order | Deterministic **template workflow agents**: `SequentialAgent` (validate → process → report, passing data via `output_key`), `ParallelAgent` (fan out independent lookups, e.g. querying three systems at once, then a downstream agent gathers the results), `LoopAgent` (repeat until a quality/termination condition — a generator/critic pattern is the classic case) | These are deterministic, not model-driven — the LLM reasons *inside* a step, but the step order itself is fixed code, not a decision. That makes them testable, auditable, and cheap, which is exactly what admin/compliance-flavored background tasks need. Don't use these for open-ended chat — they only fit when you already know the steps before the request arrives. |
| **Anything needing conditional branching, a mix of code/agent/tool/human-input steps, or precise control beyond what nesting Sequential/Parallel/Loop can express** | ADK 2.0's **graph-based workflow engine** (`Workflow(edges=[...])`) — the explicit successor to nesting template agents for this case | This is also the natural place to put an explicit human-input node in a larger pipeline (e.g., "classify → [human approval] → execute"), since the graph makes that pause a first-class node in the routing logic rather than something bolted onto a single tool call. Reach for this once template-agent nesting starts feeling like you're fighting the abstraction, not before. |

For a <100-seat internal assistant, expect the traffic split to be heavily weighted toward the first row (plain chat + tool calling) with the coordinator pattern showing up once you have a handful of graduated skills, and the deterministic/graph patterns reserved for the specific admin-console-triggered or scheduled background tasks that genuinely have a fixed shape — resist reaching for graph-based workflows or a coordinator hierarchy for the core chat experience itself; it adds latency and debugging surface for no benefit when a single `LlmAgent` already handles it well.

---

## 6. Web frontend

- **Next.js (App Router) + TypeScript.** Server components for the shell (auth-gated layout, conversation list) and client components for the actual chat surface (streaming needs client-side state).
- **State/data**: TanStack Query for server state (conversations, tool connections), lightweight client state (Zustand or React context) for in-flight streaming UI. Avoid Redux — it's unnecessary overhead for this shape of app.
- **Streaming UI**: consume SSE/WebSocket in a hook that appends tokens to the active message; render tool-call and artifact events as distinct message-timeline items (like ChatGPT's tool-use cards), not just text.
- **Component library**: shadcn/ui (Radix primitives + Tailwind) gives you accessible, ownable components you can restyle instead of fighting a heavier design-system library — good fit for an internal tool where you'll want fast iteration.
- **Artifacts rendering**: render generated HTML/React artifacts in a sandboxed `<iframe>` on a separate subdomain with a strict CSP, using `postMessage` for the narrow set of things the artifact is allowed to ask the host app to do (e.g., "send this back to chat"). This mirrors how the major vendors isolate generative UI and is the single most important web-security decision in this whole system.
- **Admin console**: can be a second Next.js app in the monorepo (`apps/admin`) reusing `packages/ui`, or a route group inside the same app gated by role — a separate app is cleaner if admin and end-user release cadences differ.

---

## 7. Native mobile app

- **React Native via Expo**, not fully native (Swift/Kotlin) or a WebView wrapper. Reasoning for a <100-seat internal tool:
  - You get one codebase for iOS + Android, sharing `shared-types` and `api-client` directly with the web app (no re-implementing the API contract in Swift and Kotlin separately).
  - Expo's managed workflow + EAS Build/Submit gives you OTA updates for JS-level changes (fix a bug without an App Store review cycle) and handles push notifications, deep linking, and biometric-gated auth with well-maintained libraries rather than custom native modules.
  - A WebView wrapper is tempting for speed but gives a worse chat UX (keyboard handling, streaming text rendering, offline/poor-network behavior) and doesn't get you real push notifications or background behavior as cleanly — for an assistant app where "notify me when the long-running task finishes" matters, native chrome around a native chat surface is worth the extra effort over a WebView.
  - Reach for a fully native rewrite only if you later need something Expo/RN genuinely can't do well (heavy on-device ML inference, deep OS-level integration) — unlikely for a chat+tools assistant.
- **Auth on mobile**: OIDC via `expo-auth-session` doing the standard authorization-code-with-PKCE flow against your IdP, tokens stored in `expo-secure-store` (Keychain/Keystore-backed), with biometric unlock (Face ID/fingerprint) gating access to a cached session so users aren't re-authenticating against the IdP every launch.
- **Offline/poor connectivity**: cache the last N conversations locally (SQLite via `expo-sqlite` or a sync engine) so the app opens instantly and queues sent messages if the network drops mid-type — a common rough edge in ChatGPT-style mobile apps that's cheap to fix early.
- **Push notifications**: Expo's push service (backed by APNs/FCM) for "your requested report is ready" / "you were mentioned" style notifications from long-running tool or artifact jobs.
- **Artifacts on mobile**: render inside a sandboxed in-app WebView (same origin-isolation principle as the web iframe) rather than trying to run interactive generated UI as native views — you don't want to interpret arbitrary generated code as native components.

---

## 8. Data model (core tables)

A minimal but complete schema to start from. Tables marked **(ADK-managed)** are created and maintained by `DatabaseSessionService`/the Artifact Service, not hand-written — list them here so you know they exist in the same Postgres instance, not because you design their internals:

- `organizations` (id, name, idp_config, plan)
- `users` (id, org_id, email, role, idp_subject)
- *`sessions`, `events`, `app_states`, `user_states`* — **(ADK-managed)**, the source of truth for conversation/agent state
- `conversations` (id, org_id, user_id, title, last_message_at) — your own thin summary table over ADK's sessions, populated via an `after_agent` callback, used for admin/search/listing
- `memory_items` (id, org_id, user_id, kind [episodic|semantic|procedural], content, embedding, confidence, source_message_id, created_at) — backing store for your custom `BaseMemoryService`
- `tool_connections` (id, org_id, user_id, provider, oauth_token_encrypted, scopes, connected_at)
- `tool_invocations` (id, session_id, tool_connection_id, arguments, result, status, latency_ms, created_at) — your audit log, populated by a `before_tool`/`after_tool` callback
- `pending_approvals` (id, org_id, session_id, tool_call_id, requested_by_tool, tool_args, requesting_user_id, status [pending|approved|denied|expired], decided_by, decided_at, expires_at) — your HITL approval gateway (Section 5.8), decoupled from ADK's own session storage since its built-in tool-confirmation feature doesn't yet support `DatabaseSessionService` in production
- `skills` (id, org_id, name, trigger_config, content_ref, version, enabled)
- *artifact metadata* — **(ADK-managed)** via the Artifact Service; point its storage backend at your S3-compatible bucket rather than modeling this table yourself

Encrypt OAuth tokens at rest (KMS-backed column encryption or a secrets manager, not plaintext columns) — `tool_connections` is the single highest-value table for an attacker.

---

## 9. Deployment, sizing, and cost shape for <100 seats

You do **not** need Kubernetes, a service mesh, or multi-region active-active for this scale. A right-sized deployment:

- **App tier**: 2–3 small container instances (or a managed platform like Fly.io/Railway/Render) for the web API, the `agent-runtime` (ADK Runner) process, and the MCP gateway, auto-scaled 1–4 instances — 100 concurrent chat users is a light load. Run `agent-runtime` as a plain container you deploy yourself rather than Vertex AI Agent Engine — the managed option is convenient if you're all-in on GCP, but it's one more piece of vendor lock-in you don't need at this scale, and a container is simple enough to operate directly.
- **Database**: one managed Postgres instance (RDS/Cloud SQL/Supabase/Neon), vertically sized (2–4 vCPU to start), with `pgvector` enabled and daily backups. Add a read replica only if/when the admin dashboard's analytics queries start contending with the chat hot path.
- **Redis**: one small managed instance for sessions + pub/sub.
- **Object storage**: S3/R2/GCS bucket, lifecycle policy to expire old artifacts after N days to control storage cost.
- **Sandbox execution**: pay-per-use with the vendor (E2B's free tier is 100 hours/month, which is a lot of headroom for <100 seats before you pay anything).
- **Model costs** are almost certainly your largest line item at this scale, not infrastructure — budget accordingly and put per-user/per-team usage dashboards in the admin console early so a runaway agent loop or an over-eager skill doesn't surprise you on the bill.
- **Network placement**: put the whole thing behind your SSO (no public sign-up), and consider a private network / VPN-gated admin console specifically, since that surface can change tool permissions and view audit logs.

This whole stack comfortably runs for a <100-seat org on a small number of managed services with one or two engineers able to operate it — resist the urge to over-build for a scale you don't have yet; the monorepo/module boundaries above are what let you split things out later without a rewrite.

---

## 10. Suggested build order (phases)

1. **Phase 1 — Core chat on ADK**: stand up `agent-runtime` with a single ADK agent, `DatabaseSessionService` on Postgres, and `InMemoryMemoryService` as a placeholder; auth (SSO), streaming completions to the web client. No tools, no real memory backend yet — get the Runner/Session plumbing solid first since everything else hangs off it.
2. **Phase 2 — MCP + tools + HITL gateway**: wire up `McpToolset`, stand up the permissions/audit layer in front of it, connect 2–3 high-value internal tools (e.g., Google Drive, Slack, your ticketing system), and build the custom `pending_approvals`-backed HITL gateway (Section 5.8) for write actions — don't depend on ADK's built-in tool-confirmation alone, since it doesn't yet support the `DatabaseSessionService` this plan uses.
3. **Phase 3 — Memory**: replace the placeholder with your custom Postgres/`pgvector`-backed `BaseMemoryService`, wire the `after_agent` write callback and the `preload_memory`/`before_model` retrieval path, expose the "what does it remember about me" panel.
4. **Phase 4 — Artifacts**: wire up the sandbox vendor as an ADK `FunctionTool`, route its output through ADK's Artifact Service into object storage, build the sandboxed rendering surface (iframe/WebView).
5. **Phase 5 — Skills/plugins + admin console**: build the skill router (as a `before_model` callback) and the admin UI for managing users, tool connections, skills, and usage; add the org-wide ADK Plugin for audit/cost tracking. Evaluate whether any skill has earned promotion to a full sub-agent via the Multi-Agent Workflow Engine.
6. **Phase 6 — Mobile**: once the API/contract is stable from the phases above, the RN app is mostly "build the UI against an already-proven API," which is why it's last, not first.

---

*This report reflects engineering practice as understood as of September 2026; MCP tooling, sandbox vendors, and memory-framework maturity are moving quickly, so re-check vendor specifics (pricing, self-host options, feature parity) before committing to a specific provider. ADK 2.0 is a young major version with breaking changes from 1.x (e.g., the default model change, renamed SDK helpers) — pin your version explicitly, read the 1.x→2.0 migration notes before starting, and expect the API surface around the newer multi-agent workflow engine specifically to keep moving for a few more minor releases.*
