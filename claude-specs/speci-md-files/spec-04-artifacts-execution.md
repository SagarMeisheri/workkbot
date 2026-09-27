# Spec 04: Artifacts & Sandboxed Code Execution

## 1. Context & Motivation
With chat, tools, and memory in place, this spec adds generative Artifacts — charts, small interactive tools, and files produced by sandboxed code execution — the capability that most differentiates this assistant from a plain chat interface. The constitution requires execution to happen in an isolated sandbox and render only in an isolated origin, never the main app's origin.

## 2. Objective & Non-Goals
- **Objective**: The assistant can execute LLM-generated code in a vendor-managed sandbox, persist the result through ADK's Artifact Service, and render it back to the user in a sandboxed, isolated-origin surface.
- **Non-Goals**: No adoption of ADK 2.0's Vertex AI Agent Engine Sandbox (GCP-only — excluded per the constitution's provider-neutrality boundary). No general-purpose file storage feature beyond what Artifacts require.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/sandbox-worker/` — thin service wrapping the E2B SDK: create session, run code, tear down, enforce network-egress allowlist/deny.
* `apps/agent-runtime/tools/execute_code.py` — an ADK `FunctionTool` calling into `sandbox-worker`.
* `apps/agent-runtime/callbacks/execution_audit.py` — `before_tool`/`after_tool` callback around the execution tool logging who/what code/output/duration/cost.
* `apps/web/app/artifact/[id]/` — isolated-origin (separate subdomain) route that renders a published Artifact inside a sandboxed `<iframe>` with a strict CSP and a narrow `postMessage` contract back to the host app.
* Object-storage bucket/lifecycle policy configuration in `infra/` for Artifact expiry.

### Files to Modify:
* `apps/agent-runtime/runner.py` — configure ADK's Artifact Service against the object-storage bucket.
* `apps/agent-runtime/agent.py` — attach the `execute_code` tool.
* `apps/mobile/` — add an in-app WebView surface mirroring the same isolated-origin rendering approach.

### Files to Delete / Deprecate:
* None.

---

## 4. Requirements & Implementation Details

### R04.1: Sandboxed execution
- Each execution request gets its own short-lived sandbox session; no persistent secrets are baked into the sandbox image; network egress is denied by default and allowlisted only where a specific tool genuinely needs it.
- A sandbox session is torn down immediately on task completion or after a short idle timeout (minutes, not hours) — no long-lived sandboxes.
- The sandbox vendor is accessed only through `sandbox-worker`'s abstraction — `agent-runtime` never calls the vendor SDK directly, so swapping vendors later touches one service, not the agent code.

### R04.2: Artifact persistence
- Execution output (files, charts, generated HTML) is written through ADK's Artifact Service into the shared object-storage bucket, never returned inline as raw bytes through the chat transcript.
- A signed, time-limited URL is what the client actually receives — never a permanent public URL.

### R04.3: Isolated-origin rendering
- Artifacts render only inside `apps/web`'s dedicated Artifact route, served from a separate subdomain from the main app, with a CSP that blocks the artifact from reading the host app's cookies or calling the host app's API with the user's session.
- The only communication channel between the rendered Artifact and the host app is a narrow, explicitly-typed `postMessage` contract (e.g., "send this back to chat") — no broader access is exposed.
- The mobile equivalent uses an in-app WebView with the same isolation principle — arbitrary generated code is never interpreted as native RN components.

### R04.4: Execution audit
- Every execution request logs who ran it, a reference to the code, output metadata, duration, and estimated cost — feeding both the security audit log (Spec 02's `tool_invocations`) and a cost dashboard input for Spec 05's admin console.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass / Fail |
|:---:|---|---|:---:|
| **VAL-01** | A sandbox session cannot reach the network except an explicitly allowlisted destination | Attempt an unlisted outbound request from inside a test sandbox; assert failure | [ ] |
| **VAL-02** | A sandbox session is torn down within the configured idle timeout | Integration test measuring session lifetime | [ ] |
| **VAL-03** | A rendered Artifact cannot read the host app's cookies or call its API with the user's session | Security test: attempt cross-origin cookie/API access from inside the artifact iframe | [ ] |
| **VAL-04** | Artifact URLs served to the client are signed and expire | Inspect a returned URL; confirm expiry and signature | [ ] |
| **VAL-05** | Every execution request produces an audit row with cost/duration | Integration test asserting row presence and fields | [ ] |
| **VAL-06** | No direct import of the sandbox vendor SDK exists outside `sandbox-worker` | `grep`/lint rule across `apps/agent-runtime` | [ ] |
