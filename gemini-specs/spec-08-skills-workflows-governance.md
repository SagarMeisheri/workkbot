# Spec 08: Skills-as-Content, Progressive Workflows & Governance Plugin

## 1. Context & Motivation
Non-engineers (HR heads, accounting leads, operations managers) need to teach the assistant organization-specific workflows without writing code or redeploying backend services. 
At the same time, naive multi-agent architectures introduce latency, token waste, and debugging nightmares.
This spec introduces **Content-as-Data Skills**, a **Progressive Workflow Graduation Ladder**, and an org-wide **ADK Governance Plugin** logging cost metrics in Indian Rupees (INR) to Supabase.

## 2. Objective & Non-Goals
- **Objective**: Skills are authored as versioned markdown files; a lightweight router injects only top matching skills; high-value skills can graduate into ADK sub-agents or graph workflows when justified; a global plugin logs token consumption and cost metrics into Supabase PostgreSQL.
- **Non-Goals**: No complex visual drag-and-drop workflow builders. Adding or graduating workflows is governed by code review.

---

## 3. Architecture & File Modifications

### Files to Create:
* `skills/<skill-name>/`
  * `SKILL.md`: Frontmatter with trigger conditions + structured instructions.
* `apps/backend/src/skills/`
  * `router.py`: `before_model` callback retrieving top-K matching skills per message.
  * `registry.py`: Scans and validates local skills.
* `apps/backend/src/workflows/`
  * `coordinator.py`: Root agent delegating to specialized sub-agents (`transfer_to_agent`).
  * `gst_reconciliation.py`: Sample deterministic `SequentialAgent` for monthly tax filing.
* `apps/backend/src/plugins/governance_plugin.py`: Global Google ADK Plugin writing token metrics to Supabase.
* `supabase/migrations/20260927000008_governance_metrics.sql`:
  * `public.agent_runs` table (`id`, `org_id`, `user_id`, `model`, `prompt_tokens`, `completion_tokens`, `cost_inr`, `created_at`).
  * RLS policies allowing org-admins to view metrics.

---

## 4. Requirements & Implementation Details

### R08.1: Content-as-Data Skills & Dynamic Routing
- A skill is a versioned markdown file located under `skills/`:
  ```markdown
  ---
  name: vendor-onboarding
  description: Handles standard KYC and vendor verification procedures
  triggers: ["new vendor", "kyc check", "vendor onboarding", "gstin verification"]
  ---
  When a user asks to onboard a vendor:
  1. Request vendor legal name and GSTIN.
  2. Verify GSTIN format using the compliance validator.
  ...
  ```
- The Skill Router runs in the `before_model` callback, matches incoming user queries against triggers, and injects **only the top 2 matching skills** into context, preventing prompt bloat.

### R08.2: The Progressive Workflow Graduation Ladder

```
[Level 1: Default (90%)] ──> Single LlmAgent with prompt-injected skill content
                                  │
                                  ▼ (Requires independent tools, model, or multi-turn reasoning)
[Level 2: Coordinator]    ──> Root LlmAgent delegates to specialized Sub-Agent (Deep Research)
                                  │
                                  ▼ (Requires deterministic, fixed-order execution pipeline)
[Level 3: Template Agents]──> SequentialAgent / ParallelAgent (e.g. Monthly GST Reconciliation)
                                  │
                                  ▼ (Requires dynamic DAG branching or explicit human-input node)
[Level 4: Graph Workflow] ──> ADK 2.0 Graph Workflow with conditional edges and approval gates
```

1. **Default Rule**: Every workflow starts at **Level 1** (plain prompt injection on the core agent).
2. **Graduation to Level 2 (Coordinator/Sub-agent)**: Justified only when the task requires independent model selection or multi-pass iterations.
3. **Graduation to Level 3 (Deterministic Pipeline)**: Used for recurring, audit-sensitive jobs (e.g. invoice extraction → ledger entry → validation).
4. **Graduation to Level 4 (Graph Workflow)**: Used when the pipeline contains branching logic and explicit human-input nodes.

### R08.3: Org-Wide Governance Plugin Logging to Supabase
- The `GovernancePlugin` attaches globally to the ADK Runner:
  - Hooks: `before_agent`, `after_agent`, `before_tool`, `after_tool`.
  - Calculates cost in Indian Rupees (INR) based on model pricing tiers.
  - Inserts run telemetry into `public.agent_runs` in Supabase PostgreSQL:
    ```sql
    INSERT INTO public.agent_runs (org_id, user_id, model, prompt_tokens, completion_tokens, cost_inr)
    VALUES (...);
    ```

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-08.1** | Adding a markdown file in `skills/` makes the skill discoverable with zero code change | Add test skill; submit prompt; assert presence in context | [ ] |
| **VAL-08.2** | Router injects only matching skills; unrelated skills are excluded from context | Submit query; inspect system prompt payload | [ ] |
| **VAL-08.3** | Level 3 SequentialAgent executes steps deterministically passing state via `output_key` | Pytest on `gst_reconciliation.py` pipeline | [ ] |
| **VAL-08.4** | Governance plugin writes token usage and INR cost rows to Supabase `agent_runs` | Query Supabase table after agent run; verify row exists | [ ] |
