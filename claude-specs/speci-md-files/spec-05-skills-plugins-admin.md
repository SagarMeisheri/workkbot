# Spec 05: Skills, Plugins, Workflow Graduation & Admin Console

## 1. Context & Motivation
This is the most architecturally complex spec in the roadmap: it introduces content-as-data skills, the point at which a skill may graduate from prompt injection into a full ADK sub-agent or a deterministic/graph-based workflow, an org-wide ADK Plugin for cross-cutting concerns, and the admin console that ties governance across every prior spec (tool connections, HITL approvals, skill catalog, usage/cost) into one surface.

## 2. Objective & Non-Goals
- **Objective**: Non-engineers can author and enable skills without a deploy; the highest-value skills can be promoted to real sub-agents or explicit workflows with human-input nodes where the task shape warrants it; admins have one console for governance across the whole system.
- **Non-Goals**: Not every skill graduates — most stay as prompt-injected content, per the constitution's default-to-`LlmAgent` rule. No general-purpose no-code workflow builder — workflow authoring for graduated skills is still an engineering task, gated by this spec's requirements, not a self-service admin feature.

---

## 3. Architecture & File Modifications

### Files to Create:
* `skills/<skill-name>/SKILL.md` + optional scripts — versioned skill content, one directory per skill.
* `apps/agent-runtime/skills/router.py` — a `before_model` callback: keyword-match (upgradeable to embedding-based) retrieval of candidate skills, injects only the top matches, logs which skills fired.
* `apps/agent-runtime/plugins/governance_plugin.py` — an ADK Plugin (global hook, distinct from the product-level "skill/plugin" concept) covering audit logging, cost/usage tracking, and PII/secret redaction on tool output across every agent.
* `apps/agent-runtime/agents/` — home for any graduated sub-agent (e.g., a "deep research" sub-agent) and its coordinator wiring (`transfer_to_agent` or `AgentTool`), added incrementally per graduated skill, not scaffolded speculatively.
* `apps/agent-runtime/workflows/` — home for any graph-based `Workflow` definitions for skills needing conditional branching or an explicit human-input node.
* `apps/admin/` (or `apps/web/app/admin/` route group) — user/role management, tool-connection management, skill catalog CRUD + enable/disable, HITL approval queue (surfacing Spec 02's `pending_approvals`), usage/cost dashboards.
* Database migration: `skills` table (`org_id`, `name`, `trigger_config`, `content_ref`, `version`, `enabled`).

### Files to Modify:
* `apps/agent-runtime/agent.py` — attach the skill router callback; wire in the coordinator agent if/when a skill graduates.

### Files to Delete / Deprecate:
* None — this spec is additive to the existing single-`LlmAgent` core.

---

## 4. Requirements & Implementation Details

### R05.1: Skill authoring and routing
- A skill is a folder of instructions (+ optional scripts) with a manifest describing its trigger conditions — content, not code, so a non-engineer can add one via a reviewed PR without touching `agent-runtime`.
- The skill router runs as a `before_model` callback, retrieves the top few candidates per incoming message, and injects only those — never the full catalog — to keep prompt size bounded regardless of how many skills exist.
- Which skills fired on a given turn is logged, giving a feedback loop for tuning trigger configs over time.

### R05.2: Workflow-pattern graduation (apply the constitution's task-shape rule explicitly)
- Default: every skill starts as prompt-injected content on the single root `LlmAgent` — no exceptions without a documented reason in the skill's own spec note.
- A skill graduates to a **coordinator/sub-agent** only when it needs its own tool access, its own model choice, or materially independent multi-step reasoning (e.g., a multi-pass research skill) — implemented via `transfer_to_agent` (genuine hand-off) or `AgentTool` (root agent stays in control, delegates one sub-task).
- A skill graduates to a **deterministic template workflow** (`SequentialAgent`/`ParallelAgent`/`LoopAgent`) only if it has a known, fixed step order regardless of the request (e.g., a scheduled report pipeline) — never for anything where the step order depends on reasoning about the specific request.
- A skill graduates to a **graph-based `Workflow`** only if it needs conditional branching, a mix of code/agent/tool/human-input steps, or an explicit human-approval node embedded in a larger pipeline (reusing Spec 02's HITL gateway as that node's approval mechanism) — this is the ceiling of complexity in this system; nothing beyond it is in scope for v1.
- Every graduation decision is documented (which tier, and why) alongside the skill's own content, so a reviewer can audit whether the complexity was earned.

### R05.3: Org-wide governance plugin
- The `governance_plugin.py` ADK Plugin applies uniformly across every agent (root and any graduated sub-agents/workflows) — audit logging, cost/usage tracking, and output redaction are not re-implemented per agent.
- Redaction specifically screens tool *output* before it re-enters the model's context, as a defense-in-depth layer alongside Spec 02's permission/confirmation controls (not a replacement for them).

### R05.4: Admin console
- Single console surfacing: user/role management (mapped to IdP groups, not a bespoke permission UI), tool-connection management, the skill catalog (enable/disable/version history), the HITL approval queue from Spec 02, and usage/cost dashboards fed by the audit and execution logs from Specs 02 and 04.
- Placed on a private network path / VPN-gated route given it can change tool permissions and view the audit log, per the constitution's security boundary.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass / Fail |
|:---:|---|---|:---:|
| **VAL-01** | Adding a new skill (a PR to `skills/`) requires no `agent-runtime` code change or redeploy of agent logic | Manual step: add a skill folder, confirm it's retrievable without a code deploy | [ ] |
| **VAL-02** | The skill router injects only top-K matching skills, never the full catalog, regardless of catalog size | Pytest with a large seeded skill catalog, assert bounded prompt size | [ ] |
| **VAL-03** | A graduated sub-agent's graduation rationale is documented and reviewable | Manual review of the skill's accompanying graduation note | [ ] |
| **VAL-04** | The governance plugin's audit/cost/redaction logic applies to a graduated sub-agent identically to the root agent | Integration test comparing plugin behavior across both | [ ] |
| **VAL-05** | A graph-based workflow with a human-input node correctly pauses at that node and resumes via Spec 02's HITL gateway | Integration test driving a graph workflow through an approval pause | [ ] |
| **VAL-06** | Admin console access (approvals, tool connections, audit log) is restricted to `tool-admin`/`org-admin` roles | Role-based access test | [ ] |
| **VAL-07** | Lint/type-check pass across all new/modified files | `pnpm turbo run lint typecheck` + `ruff check apps/agent-runtime` | [ ] |
