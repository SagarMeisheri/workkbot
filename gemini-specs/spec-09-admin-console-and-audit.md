# Spec 09: Centralized Admin Console & Immutable BigQuery Audit (The 5-Framework Model)

## 1. Context & Motivation
For an internal enterprise tool, governance, cost control, security oversight, and auditability are non-negotiable. 
IT leadership and business owners need a single pane of glass to configure allowed MCP providers, monitor AI token expenditures in INR, manage user roles, toggle skills, monitor Agentgateway security events (tool poisoning detections, SSRF probe drops), and review immutable compliance audit trails.

Workkbot routes all administrative governance, observability, and compliance auditing through the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: User roles in JWT claims, granular PostgreSQL RLS policies, and `public.org_provider_policies`.
2. **Google Cloud Platform (GCP `asia-south1`)**: Cloud Logging sinks streaming audit trails to **Google BigQuery** with a 7-year immutable retention lock, and Cloud Monitoring alert policies.
3. **Google ADK 2.0 (`google-adk`)**: Emits structured agent run events, token consumption metrics, and tool execution lifecycles via `GovernancePlugin`.
4. **assistant-ui (`@assistant-ui/react-o11y`, `@assistant-ui/react-ink`)**: Visual trace waterfalls in the web admin console via `@assistant-ui/react-o11y` (`SpanResource`, `SpanPrimitive`) and headless terminal CLI management via `@assistant-ui/react-ink`.
5. **Agentgateway 1.5.x**: OpenTelemetry (OTel) security telemetry engine streaming blocked injection probes, parameter tampering, and SSRF attacks to Cloud Logging, and dynamically synchronizing CEL policies.

### **The North Star: Security & Mobile App Approval**
- **Security**: Tamper-evident, 7-year immutable audit retention in BigQuery satisfying India's DPDP Act 2023 and CERT-In; zero admin bottleneck on end-user chat.
- **Mobile App Approval (Apple Guideline 3.1.3c & 4.0)**: Clean separation of concerns where mobile clients operate in a lightweight, focused employee chat view while heavy administrative dashboards and o11y waterfall trees reside securely on the web admin console.

---

## 2. The 5-Framework Architecture Mapping for Spec 09

| Framework | Core Responsibility in Admin & Audit | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | `public.org_provider_policies` table; database views for monthly aggregations; RLS restricting access to `org-admin`. | Enforces strict role checks: `(auth.jwt() -> 'app_metadata' ->> 'role') = 'org-admin'`. |
| **2. Google Cloud Platform (GCP)** | Cloud Logging sink routing audit events to Google BigQuery in `asia-south1`; 7-year immutable retention policy. | Satisfies statutory DPDP & CERT-In requirements; data cannot be tampered with or deleted early. |
| **3. Google ADK 2.0** | `GovernancePlugin` emitting execution traces, token usage, and latency metrics per session turn. | Provides verifiable execution provenance without capturing unmasked PII. |
| **4. assistant-ui** | `@assistant-ui/react-o11y` rendering interactive trace timeline waterfalls; `@assistant-ui/react-ink` for DevOps CLI. | Rich observability UI without custom charting libraries; lightweight mobile UI remains fast. |
| **5. Agentgateway 1.5.x** | OTel metrics and security violation logging (`agentgateway.security.violation`); CEL policy synchronization. | Immediately alerts admins to attempted tool poisoning, SSRF probes, or brute-force parameter tampering. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/admin/`
  * `router.py`: Endpoints for `/api/v1/admin/users`, `/providers`, `/skills`, `/metrics`, `/security-events`, and `/audit-logs`.
  * `metrics_service.py`: Queries Supabase `agent_runs` to aggregate token consumption and calculate monthly costs in INR.
  * `audit_export.py`: Generates signed CSV/JSON audit exports and queries Google BigQuery audit archives.
* `infra/gcp/terraform/logging_sinks.tf`:
  * Google Cloud Logging export sink streaming `workkbot-audit` and `agentgateway-security` logs into a dedicated BigQuery dataset in Mumbai (`asia-south1`).
* `supabase/migrations/20260927000009_admin_views.sql`:
  * Database views and helper functions for monthly cost aggregations.
  * Strict RLS policies restricting read access to users with `app_metadata.role = 'org-admin'`.
* `apps/web/src/app/admin/`:
  * `page.tsx`: Executive dashboard with usage metrics, active users, and cost summaries.
  * `traces/page.tsx`: Trace waterfall timelines rendered via `@assistant-ui/react-o11y`.
  * `providers/`: Org-wide MCP provider allowlisting.
  * `security/`: Live Agentgateway security log viewer.
  * `audit/`: Searchable log table with filters for date, user, tool, and execution status.
* `apps/backend/src/cli/admin_ink.tsx`: Terminal administration utility powered by `@assistant-ui/react-ink`.

---

## 4. Requirements & Implementation Details

### R09.1: Role-Based Access Control via Supabase RLS (Supabase Framework)
- **Roles in Supabase Auth**:
  1. `member`: Normal chat, view own memories, authorize own connected tools and in-chat approval cards.
  2. `tool-admin`: Configure org-allowed MCP providers, view tool audit logs.
  3. `org-admin`: Full access including user provisioning, cost dashboards, provider allowlisting, and DPDP DSR erasure triggers.
- Protected by Supabase RLS policies:
  ```sql
  CREATE POLICY "Admins can view all audit logs" ON public.tool_invocations
    FOR SELECT USING (
      (auth.jwt() -> 'app_metadata' ->> 'role') IN ('tool-admin', 'org-admin')
      AND org_id = (auth.jwt() ->> 'org_id')::uuid
    );
  ```

### R09.2: Org-Wide MCP Provider Allow-Listing & CEL Policy Sync (Supabase + Agentgateway)
- Admins configure which external MCP providers employees are permitted to connect via OAuth:
  - Updates `public.org_provider_policies` table in Supabase.
  - Updates dynamic CEL rules in Agentgateway to deny requests to unapproved upstream tools.
  - Employees only see allowlisted providers in their Connectors Hub Modal.

### R09.3: Cost & Rupee Budget Dashboard (Supabase + GCP)
- Queries Supabase `agent_runs` table:
  - Input tokens vs Output tokens.
  - Model family (Gemini 2.0 Flash vs Pro).
  - Total expenditure converted to Indian Rupees (INR).
- **Budget Threshold Alerts**: Realtime alerts via Cloud Monitoring when monthly spend reaches 80% and 100% of the configured budget cap.

### R09.4: Immutable Google BigQuery Audit Sink (GCP Framework)
- All tool execution and HITL decision logs are streamed to **Google Cloud Logging**.
- A Cloud Logging export sink routes logs into **Google BigQuery** (`$PROJECT:audit_dataset.tool_invocations`) in `asia-south1`:
  - Enforces 7-year immutable retention lock.
  - Provides tamper-evident compliance logs satisfying DPDP Act 2023 and CERT-In directions.

### R09.5: Trace Waterfalls & Terminal CLI via Assistant-UI (assistant-ui Framework)
- `@assistant-ui/react-o11y` mounts inside the web admin console to render interactive span execution waterfalls:
  - Visualizes time spent in prompt routing, Cloud DLP inspection, Vertex AI inference, and MCP execution.
- `@assistant-ui/react-ink` provides a terminal-based CLI for DevOps engineers to inspect active agent status, view logs, and trigger maintenance tasks.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-09.1** | Standard `member` user attempting to access admin tables is blocked by Supabase RLS | `pytest apps/backend/tests/test_admin_rbac.py` | [ ] |
| **VAL-09.2** | Disabling an MCP provider in Admin Console removes it from employee connection options | `pytest apps/backend/tests/test_provider_allowlist.py` | [ ] |
| **VAL-09.3** | Cost aggregation correctly calculates INR totals based on model pricing tiers | `pytest apps/backend/tests/test_inr_metrics_aggregation.py` | [ ] |
| **VAL-09.4** | Cloud Logging sink delivers immutable audit records to BigQuery in `asia-south1` | `bq query --use_legacy_sql=false "SELECT count(*) FROM \`$PROJECT.audit_dataset.tool_invocations\`"` | [ ] |
| **VAL-09.5** | Agentgateway security events stream into BigQuery & Admin UI | `pytest apps/backend/tests/test_security_audit_ingestion.py` | [ ] |
| **VAL-09.6** | Trace waterfall renders smoothly using `@assistant-ui/react-o11y` | `pnpm --filter web test:e2e tests/e2e/trace-waterfall.spec.ts` | [ ] |
