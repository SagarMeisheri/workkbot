# Spec 08: Skills-as-Content, Progressive Workflows & INR Governance (The 5-Framework Model)

## 1. Context & Motivation
Non-engineers (HR heads, accounting leads, operations managers) need to teach the assistant organization-specific workflows without writing code or redeploying backend services. 
At the same time, naive multi-agent architectures introduce latency, token waste, and debugging nightmares.

Workkbot resolves this by structuring skills, progressive multi-agent workflows, and INR cost governance around the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Stores run telemetry, token usage, and calculated cost metrics in `public.agent_runs` with strict RLS.
2. **Google Cloud Platform (GCP `asia-south1`)**: Emits custom metrics to **Google Cloud Monitoring** (`custom.googleapis.com/workkbot/token_cost_inr`) and enforces monthly INR budget thresholds on Cloud Run.
3. **Google ADK 2.0 (`google-adk`)**: Ingests markdown skills via dynamic `before_model` router, provides the 4-tier Progressive Workflow Ladder, and hosts the global `GovernancePlugin`.
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: In-composer Skills picker (`+ -> Skills >`), slash command triggers (`/`), and dynamic agent transfer badges (`useAdkAgentInfo()`).
5. **Agentgateway 1.5.x**: Native Agent-to-Agent (A2A) protocol gateway (`127.0.0.1:8080/a2a`), CEL policy enforcement for inter-agent delegation, and token throttling.

### **The North Star: Security & Mobile App Approval**
- **Security**: Content-as-data skills are sandboxed; cross-agent delegation requires explicit CEL authorization; token consumption is capped in INR to prevent resource exhaustion attacks.
- **Mobile App Approval (Apple Guideline 4.0 & 2.1)**: Predictable, responsive UI; multi-agent step transfers render as fluid status badges rather than disjointed raw responses, maintaining seamless 60fps mobile execution.

---

## 2. The 5-Framework Architecture Mapping for Spec 08

| Framework | Core Responsibility in Skills & Workflows | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | `public.agent_runs` table tracking token usage, latency, and INR cost with RLS for org admins. | Isolates governance data by `org_id`; ensures auditability of automated workflow runs. |
| **2. Google Cloud Platform (GCP)** | Google Cloud Monitoring custom metrics (`token_cost_inr`); budget alert notifications. | Provides real-time visibility into infrastructure costs; alerts admins before budget exhaustion. |
| **3. Google ADK 2.0** | Skill registry; `before_model` router; Progressive Workflow Graduation Ladder; global `GovernancePlugin`. | Prevents context window bloat by injecting only top-2 relevant skills; executes deterministic pipelines. |
| **4. assistant-ui** | Skills submenu under `+`; slash command triggers (`/`); agent transfer progress indicator badges. | Native cross-platform UI rendering; clear user feedback during multi-agent handoffs. |
| **5. Agentgateway 1.5.x** | A2A Protocol proxy on loopback `:8080/a2a`; inter-agent CEL authorization; token rate limiter. | Prevents unauthorized agent-to-agent lateral movement; enforces per-session tool scoping. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `skills/<skill-name>/`
  * `SKILL.md`: Frontmatter with trigger conditions + structured instructions.
* `apps/backend/src/skills/`
  * `router.py`: `before_model` callback retrieving top-K matching skills per message.
  * `registry.py`: Scans and validates local skills.
* `apps/backend/src/workflows/`
  * `coordinator.py`: Root agent delegating to specialized sub-agents (`transfer_to_agent`).
  * `a2a_client.py`: Interacts with Agentgateway's A2A proxy to discover and invoke remote departmental agent services.
  * `gst_reconciliation.py`: Sample deterministic `SequentialAgent` for monthly tax filing.
* `apps/backend/src/plugins/governance_plugin.py`: Global Google ADK Plugin writing token metrics to Supabase and Google Cloud Monitoring.
* `supabase/migrations/20260927000008_governance_metrics.sql`:
  * `public.agent_runs` table (`id`, `org_id`, `user_id`, `model`, `prompt_tokens`, `completion_tokens`, `cost_inr`, `created_at`).
  * RLS policies allowing org-admins to view metrics.
* `apps/web/src/components/chat/agent-badge.tsx`: Dynamic assistant-ui badge showing active sub-agent name and status.

---

## 4. Requirements & Implementation Details

### R08.1: Content-as-Data Skills & Dynamic Routing (Google ADK 2.0 Framework)
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
- The Skill Router runs in ADK's `before_model` callback, matches incoming user queries against triggers, and injects **only the top 2 matching skills** into context, preventing prompt bloat.

### R08.2: The Progressive Workflow Graduation Ladder (Google ADK 2.0 Framework)
```text
[Level 1: Default (90%)] ──> Single LlmAgent with prompt-injected skill content
                                  │
                                  ▼ (Requires independent tools, model, or multi-turn reasoning)
[Level 2: Coordinator]    ──> Root LlmAgent delegates to specialized Sub-Agent (Deep Research)
                                  │
                                  ▼ (Requires deterministic, fixed-order execution pipeline)
[Level 3: Template Agents]──> SequentialAgent / ParallelAgent (e.g. Monthly GST Reconciliation)
                                  │
                                  ▼ (Requires cross-departmental agent collaboration)
[Level 4: A2A Federated]  ──> Agent-to-Agent (A2A) protocol routed via Agentgateway 1.5.x
```

### R08.3: Agent-to-Agent (A2A) Protocol Delegation via Agentgateway (Agentgateway Framework)
- When a task spans organizational boundaries (e.g. Core Assistant delegating an audited tax computation to an isolated Finance Agent container):
  - The Root Agent delegates over Agentgateway's native A2A proxy (`http://127.0.0.1:8080/a2a`).
  - Agentgateway negotiates schema, checks caller permissions via CEL, and invokes the remote agent.
  - The remote agent executes without exposing its internal system instructions or private tools.

### R08.4: Org-Wide Governance Plugin (Supabase + GCP Frameworks)
- The `GovernancePlugin` attaches globally to the ADK Runner:
  - Hooks: `before_agent`, `after_agent`, `before_tool`, `after_tool`.
  - Calculates cost in Indian Rupees (INR) based on Google Vertex AI pricing (e.g. ₹0.00625 per 1k input tokens for Gemini 2.0 Flash).
  - Inserts run telemetry into `public.agent_runs` in Supabase PostgreSQL with tenant RLS.
  - Emits custom time-series metrics to **Google Cloud Monitoring** (`custom.googleapis.com/workkbot/token_cost_inr`).

---

## 5. Validation Scorecard & Execution Target

### **Execution Target**: `Localhost (Zero-Mock)`
- **Environment**: Next.js 15 (`localhost:3000`) and FastAPI (`localhost:8000`) on developer machine.
- **Live Cloud Boundaries**:
  - Live local filesystem discovery from `skills/<name>/SKILL.md`.
  - In-process Google ADK 2.0 `SequentialAgent` executing with live Gemini 2.0 Flash.
  - Live Supabase `public.token_ledger` and Google Cloud Monitoring API emitting metric `workkbot/token_cost_inr` via Google Application Default Credentials.

---

### **Tier 1: Unit & Contract Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-08.1** | Skill parser extracts YAML frontmatter, description, and execution prompts from `SKILL.md` | `uv run pytest apps/backend/tests/test_skill_discovery.py` | [ ] |
| **VAL-08.2** | Router injects only matching skills into `before_model` context; unrelated skills are excluded | `uv run pytest apps/backend/tests/test_skill_routing.py` | [ ] |
| **VAL-08.3** | SequentialAgent executes steps deterministically passing state via `output_key` | `uv run pytest apps/backend/tests/test_sequential_agent.py` | [ ] |

### **Tier 2: Zero-Mock Live Integration Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-08.4** | Coordinator agent delegates task to external agent using Agentgateway A2A protocol | `uv run pytest apps/backend/tests/test_a2a_delegation.py` | [ ] |
| **VAL-08.5** | Real token usage and INR cost calculation writes immutable rows to `public.token_ledger` | `uv run pytest apps/backend/tests/test_governance_inr_logging.py` | [ ] |
| **VAL-08.6** | Live Google Cloud Monitoring receives custom metric `workkbot/token_cost_inr` via Google SDK | `uv run pytest -m live_gcp apps/backend/tests/test_cloud_monitoring_emission.py` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-08.7** | Composer `+ -> Skills >` submenu lists all discovered skills with icons and descriptions | `pnpm --filter @workkbot/web test:e2e tests/e2e/skills-popover.spec.ts` | [ ] |
| **VAL-08.8** | Sub-agent workflow execution displays fluid status badges ("Analyzing -> Drafting -> Validating") | `pnpm --filter @workkbot/web test:e2e tests/e2e/workflow-badges.spec.ts` | [ ] |
| **VAL-08.9** | Turn footer displays estimated INR token cost pill (`₹0.04`) for the completed prompt | `pnpm --filter @workkbot/web test:e2e tests/e2e/token-cost-pill.spec.ts` | [ ] |

### **Tier 4: Manual Verification Protocol**
1. **Discover Skill via UI**: In `http://localhost:3000/chat`, click `+` on the floating composer. Hover over `Skills >`. Confirm newly created skills in `skills/` appear in the submenu without app restart.
2. **Execute Sequential Workflow**: Select **"GST Audit Workflow"**. Prompt: *"Audit our September sales ledger for GST compliance."* Confirm the chat bubble renders real-time progressive status pills:
   - `Step 1/3: Extracting GSTINs...`
   - `Step 2/3: Validating against state tax rules...`
   - `Step 3/3: Generating compliance summary...`
3. **Verify Cloud Monitoring Metric**: Open Google Cloud Console -> Cloud Monitoring -> Metrics Explorer. Query `custom.googleapis.com/workkbot/token_cost_inr`. Confirm metric values corresponding to your recent chat turn were received within the last 3 minutes.

