# Spec 08: Skills-as-Content, Progressive Workflows & INR Cost Governance (GCP Day 1)

## 1. Context & Motivation
Non-engineers (HR heads, accounting leads, operations managers) need to teach the assistant organization-specific workflows without writing code or redeploying backend services. 
At the same time, naive multi-agent architectures introduce latency, token waste, and debugging nightmares.
This spec introduces on **Google Cloud (`asia-south1`)**:
1. **Content-as-Data Skills**: Versioned Markdown files loaded on-demand.
2. **Progressive Workflow Graduation Ladder**: Starting with prompt injection before graduating to complex sub-agents.
3. **Org-Wide ADK Governance Plugin**: Calculating token usage and real-time expenditure in Indian Rupees (INR) logged to Supabase and exported to **Google Cloud Monitoring**.

## 2. Objective & Non-Goals
- **Objective**: Skills are authored as versioned markdown files; a lightweight router injects only top matching skills; high-value skills can graduate into ADK sub-agents or graph workflows when justified; a global plugin logs token consumption and cost metrics into Supabase PostgreSQL and Google Cloud Monitoring.
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
* `apps/backend/src/plugins/governance_plugin.py`: Global Google ADK Plugin writing token metrics to Supabase and Google Cloud Monitoring.
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

### R08.3: Org-Wide Governance Plugin Logging to Supabase & Cloud Monitoring
- The `GovernancePlugin` attaches globally to the ADK Runner:
  - Hooks: `before_agent`, `after_agent`, `before_tool`, `after_tool`.
  - Calculates cost in Indian Rupees (INR) based on Google Vertex AI pricing (e.g. ₹0.00625 per 1k input tokens for Gemini 2.0 Flash).
  - Inserts run telemetry into `public.agent_runs` in Supabase PostgreSQL.
  - Emits custom time-series metrics to **Google Cloud Monitoring** (`custom.googleapis.com/workkbot/token_cost_inr`).

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-08.1** | Adding a markdown file in `skills/` makes the skill discoverable with zero code change | `pytest apps/backend/tests/test_skill_discovery.py` | [ ] |
| **VAL-08.2** | Router injects only matching skills; unrelated skills are excluded from context | `pytest apps/backend/tests/test_skill_routing.py` | [ ] |
| **VAL-08.3** | Level 3 SequentialAgent executes steps deterministically passing state via `output_key` | `pytest apps/backend/tests/test_sequential_agent.py` | [ ] |
| **VAL-08.4** | Governance plugin writes token usage and INR cost rows to Supabase `agent_runs` | `pytest apps/backend/tests/test_governance_inr_logging.py` | [ ] |
| **VAL-08.5** | Google Cloud Monitoring receives custom metric `token_cost_inr` | `pytest apps/backend/tests/test_cloud_monitoring_emission.py` | [ ] |
