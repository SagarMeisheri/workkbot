# Spec 09: Centralized Admin Console & Immutable Audit Engine via Supabase

## 1. Context & Motivation
For an internal enterprise tool, governance, cost control, and auditability are non-negotiable. 
IT leadership and business owners need a single pane of glass to configure allowed MCP providers, monitor AI token expenditures in INR, manage user roles, toggle skills, and review immutable compliance audit trails.
Because tool execution approvals are handled 100% user-centrically by employees in their own chat sessions, the Admin Console is freed from being an operational approval bottleneck, focusing purely on governance, cost tracking, and statutory compliance.

## 2. Objective & Non-Goals
- **Objective**: Authorized admins (`tool-admin`, `org-admin`) have a secure dashboard to manage users, allowlist MCP providers, toggle skills, monitor token budgets in INR, and export the immutable audit trail from Supabase PostgreSQL.
- **Non-Goals**: No admin approval queue for routine user tool calls. Admins set policies and provider allowlists, not micro-approve individual emails or tickets.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/admin/`
  * `router.py`: Endpoints for `/api/v1/admin/users`, `/providers`, `/skills`, `/metrics`, and `/audit-logs`.
  * `metrics_service.py`: Queries Supabase `agent_runs` to aggregate token consumption and calculate monthly costs in INR.
  * `audit_export.py`: Generates signed CSV/JSON audit exports for DPDP or CERT-In compliance reviews.
* `supabase/migrations/20260927000009_admin_views.sql`:
  * Database views and helper functions for monthly cost aggregations.
  * Strict RLS policies restricting read access to users with `app_metadata.role = 'org-admin'`.
* `apps/web/src/app/admin/`:
  * `page.tsx`: Executive dashboard with usage metrics, active users, and cost summaries.
  * `providers/`: Org-wide MCP provider allowlisting (enable/disable providers for employees).
  * `skills/`: Skill catalog with toggle switches and usage metrics.
  * `audit/`: Searchable log table with filters for date, user, tool, and execution status.

---

## 4. Requirements & Implementation Details

### R09.1: Role-Based Access Control via Supabase RLS
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

### R09.2: Org-Wide MCP Provider Allow-Listing
- Admins configure which external MCP providers employees are permitted to connect via OAuth:
  - Updates `public.org_provider_policies` table.
  - Employees only see allowlisted providers in their **Settings -> Connected Tools** hub.
  - Prevents data leakage to unapproved external services.

### R09.3: Cost & Rupee Budget Dashboard
- Queries Supabase `agent_runs` table:
  - Input tokens vs Output tokens.
  - Model family (Gemini Flash vs Claude Sonnet vs GPT-4o).
  - Total expenditure converted to Indian Rupees (INR).
- **Budget Threshold Alerts**: Supabase Realtime alerts when monthly spend reaches 80% and 100% of the configured budget cap.

### R09.4: Searchable Audit Log Viewer (`tool_invocations`)
- Features:
  - Filter by user email, tool name, date range, or execution status (`executed`, `rejected`, `failed`).
  - View full input arguments and execution latency.
  - One-click **Export to CSV / JSON** with SHA-256 integrity hash for statutory DPDP / CERT-In audits.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-09.1** | Standard `member` user attempting to access admin tables is blocked by Supabase RLS | Query admin tables with member Supabase token | [ ] |
| **VAL-09.2** | Disabling an MCP provider in the Admin Console removes it from employee connection options | Toggle provider; verify employee hub options | [ ] |
| **VAL-09.3** | Cost aggregation correctly calculates INR totals based on model pricing tiers | Unit test on `metrics_service.py` | [ ] |
| **VAL-09.4** | Audit log export contains all required fields and matches database record count | Verify exported CSV against `tool_invocations` table | [ ] |
