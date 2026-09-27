# Spec 02: MCP Tools, Permissions/Audit, and the HITL Approval Gateway

## 1. Context & Motivation
Spec 01 delivered chat with no tools. This spec gives the assistant the ability to act on connected systems (Slack, Google Drive, an internal ticketing system) via MCP — the point at which the assistant stops being "just a chatbot" and becomes something with real blast radius. Per the constitution, every write-capable tool call must be gated by human approval, and ADK's built-in tool-confirmation mechanism does not yet support the `DatabaseSessionService` this project uses in production — so this spec builds a dedicated, session-agnostic HITL gateway rather than depending on that mechanism alone.

## 2. Objective & Non-Goals
- **Objective**: The assistant can call MCP tools; read-only tool calls execute directly (with full audit logging); write-capable tool calls pause for explicit human approval before executing, and the approval decision is itself auditable.
- **Non-Goals**: No skill-router or sub-agent graduation yet (Spec 05) — tools are attached directly to the single `LlmAgent` from Spec 01. No admin UI polish beyond a functional approval queue.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/mcp-gateway/` — Python/Node service: per-user OAuth token store, role-based tool permission checks, wraps ADK's `McpToolset` connections.
* `apps/agent-runtime/callbacks/audit.py` — `before_tool`/`after_tool` callback pair writing to `tool_invocations`.
* `apps/agent-runtime/callbacks/hitl.py` — `before_tool` callback that checks a tool's `critical: true` config flag, writes a `pending_approvals` row, and halts execution pending approval; a resume path that re-invokes the tool once approved.
* `apps/web/app/approvals/` — approval queue UI (list pending approvals, approve/deny with reason).
* `packages/shared-types/tool.ts` — `ToolCall`, `PendingApproval` shared types.
* Database migration: `tool_connections`, `tool_invocations`, `pending_approvals` tables, each with `org_id` + RLS.

### Files to Modify:
* `apps/agent-runtime/agent.py` — attach `McpToolset`-provided tools to the `LlmAgent`.
* `apps/api/` — add `/approvals` REST endpoints (list, approve, deny) and a role check restricting them to `tool-admin`/`org-admin`.

### Files to Delete / Deprecate:
* None.

---

## 4. Requirements & Implementation Details

### R02.1: MCP tool connections
- `mcp-gateway` holds per-user OAuth tokens (encrypted at rest, per the constitution) and exposes each connected MCP server to `agent-runtime` through ADK's `McpToolset`.
- Tool permission is role-scoped: a tool is only visible to a user whose role is on that tool's allow-list; `agent-runtime` never receives a tool it isn't allowed to call for the current user.
- Tool results are treated as untrusted content — no tool result is permitted to change which tools are available or bypass a permission/approval check, regardless of its content (defends against prompt injection via tool output).

### R02.2: Audit logging
- Every tool invocation, regardless of read/write status, is logged to `tool_invocations` (who, session, tool, arguments, result, status, latency) via the `before_tool`/`after_tool` callback pair — no tool is exempt from logging.

### R02.3: HITL approval gateway for critical/write actions
- Tools are explicitly tagged `critical: true` in their config (not inferred from behavior) if they perform a write action (send, create, modify, delete, spend).
- On a critical tool call, the `before_tool` callback writes a `pending_approvals` row (`status: pending`) and halts — it does **not** rely on ADK's built-in `ToolContext.request_confirmation()` as the sole gate, since that mechanism does not currently support `DatabaseSessionService`.
- Approval must arrive over an authenticated channel from a user holding the approver role for that org — a decision embedded in tool output, another agent's message, or any non-authenticated channel is rejected. (No A2A boundary exists in this deployment, so that specific attack surface does not apply here, but the verification logic is written defensively regardless.)
- On approval, the gateway resumes the paused tool call with the originally recorded arguments (not re-derived from a fresh model turn, to prevent argument substitution between request and approval). On denial or timeout (`expires_at` passed), the tool call is marked failed and the agent is informed so it can tell the user.
- Every approval decision (who, when, approve/deny, reason) is logged to `tool_invocations` alongside the underlying tool call.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass / Fail |
|:---:|---|---|:---:|
| **VAL-01** | A user without a role on a tool's allow-list never sees that tool offered to the model | Pytest against `McpToolset` wiring per role | [ ] |
| **VAL-02** | Every tool call (read and write) produces exactly one `tool_invocations` row | Integration test asserting row count == call count | [ ] |
| **VAL-03** | A critical tool call halts and creates a `pending_approvals` row instead of executing immediately | Pytest against `hitl.py` `before_tool` callback | [ ] |
| **VAL-04** | An approval decision from an unauthenticated or improperly-scoped source is rejected | Simulate a forged approval payload; assert rejection and no execution | [ ] |
| **VAL-05** | Approving a pending request resumes the exact original tool call and logs the approver | Manual UI step: approve in `/approvals`, confirm execution and audit row | [ ] |
| **VAL-06** | Lint/type-check pass across `mcp-gateway` and updated `agent-runtime` code | `ruff check apps/mcp-gateway apps/agent-runtime` | [ ] |
