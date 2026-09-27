# Spec 01: Core Foundation — Auth, Monorepo Scaffold, and Chat on ADK

## 1. Context & Motivation
This is the first feature loop. Before any tool, memory, or Artifact capability exists, the org needs a working, SSO-gated chat surface backed by a real agentic harness (Google ADK 2.0), not a placeholder. Everything in later specs (Spec 02–06) attaches to the `agent-runtime` app and the session model established here. Per the constitution, the core chat path must stay simple: a single `LlmAgent`, no orchestration wrapper, no tools yet.

## 2. Objective & Non-Goals
- **Objective**: A logged-in employee can open the web app, start a conversation, and stream a response from a model provider through an ADK Runner, with the session durably persisted in Postgres.
- **Non-Goals**: No MCP tools, no memory backend beyond an in-memory placeholder, no Artifacts, no mobile app, no admin console. This spec is deliberately thin — resist the urge to pull in later-phase capability here.

---

## 3. Architecture & File Modifications

### Files to Create:
* `pnpm-workspace.yaml`, `turbo.json` — monorepo root config.
* `apps/web/` — Next.js (App Router) app: login-gated layout, conversation view, streaming message component.
* `apps/api/` — NestJS/Fastify app: OIDC callback handling, session-cookie issuance/refresh, a `/chat` endpoint that proxies to `agent-runtime` and relays its SSE stream to the client.
* `apps/agent-runtime/` — Python ADK app:
  * `agent.py` — a single `LlmAgent` (`name="assistant"`, model provider set via config, no tools yet).
  * `runner.py` — instantiates the ADK `Runner` with `DatabaseSessionService` (pointed at Postgres) and `InMemoryMemoryService` as an explicit, temporary placeholder.
  * `server.py` — thin HTTP/SSE surface `api` calls into.
* `packages/shared-types/` — `Message`, `Session` types shared by `web` and `api`.
* `infra/` — Postgres, Redis provisioning (IaC), Dockerfiles for `web`, `api`, `agent-runtime`.

### Files to Modify:
* None — greenfield spec.

### Files to Delete / Deprecate:
* None.

---

## 4. Requirements & Implementation Details

### R01.1: SSO/OIDC authentication
- `api` implements the OIDC authorization-code flow against the org's IdP (Entra ID / Okta / Google Workspace) — no username/password form exists anywhere in the product.
- On successful login, `api` issues a short-lived (10–15 min) JWT access token and an `httpOnly`/`secure` refresh token; the refresh-token family is stored in Redis so a whole session tree can be revoked instantly.
- Every hand-written table created in this spec (`organizations`, `users`) carries `org_id` and a Postgres RLS policy per the constitution, even with a single org configured.

### R01.2: ADK Runner with a single `LlmAgent` and Postgres-backed sessions
- `agent-runtime` runs one `LlmAgent` with no tools attached — pure conversational chat.
- Session state is persisted via ADK's `DatabaseSessionService` against the shared Postgres instance; the exact ADK minor version is pinned in `techstack.md` and recorded in `agent-runtime`'s lockfile.
- `InMemoryMemoryService` is wired in explicitly as a labeled placeholder (a code comment and a `TODO(spec-03)` reference), not silently omitted, so Spec 03 has an unambiguous attachment point.

### R01.3: Streaming chat end to end
- `web` sends a message to `api`; `api` forwards it to `agent-runtime` and streams tokens back to the client over SSE.
- UI states: composing, streaming (token-by-token render), error (model/provider failure), and a visible "reconnecting" state if the SSE connection drops mid-stream.
- Message edit/regenerate creates a new ADK Event referencing its parent, establishing the branching structure later specs rely on — this is a required behavior of this spec, not deferred.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass / Fail |
|:---:|---|---|:---:|
| **VAL-01** | Unauthenticated request to `/chat` is rejected; only a valid IdP-issued session can start a conversation | Integration test hitting `api` with no/expired token | [ ] |
| **VAL-02** | A logged-in user's message reaches `agent-runtime` and a streamed response renders token-by-token in `web` | Playwright end-to-end test | [ ] |
| **VAL-03** | Session state survives an `agent-runtime` restart (read back from `DatabaseSessionService`, not memory) | Kill and restart the container mid-session, resume the conversation | [ ] |
| **VAL-04** | Editing an earlier message creates a new branch rather than overwriting history | Pytest against the ADK Event log | [ ] |
| **VAL-05** | Lint/format/type-check pass on all four new apps | `pnpm turbo run lint typecheck` + `ruff check apps/agent-runtime` | [ ] |
