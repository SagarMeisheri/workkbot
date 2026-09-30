# Spec 04: Dynamic MCP Tools, Composio Platform, Supabase Vault & In-Chat HITL (The Two-Tier Gateway Architecture)

## 1. Context & Motivation
Connecting an enterprise AI assistant to external systems introduces severe operational and security risks, including token theft, indirect prompt injection (tool poisoning), tool shadowing, and parameter tampering (e.g. CVE-2026-29791). Hand-rolling individual OAuth integrations for dozens of SaaS tools is brittle, slow, and security-prone.

Workkbot resolves these challenges by adopting the **Two-Tier Gateway Model**, strictly governed under the **5 Core Frameworks**:
1. **Tier 1 (Infrastructure Data Plane - Agentgateway 1.5.x)**: High-speed in-pod Rust proxy on loopback (`127.0.0.1:8080`), sanitizing tool descriptions against prompt injection, preventing tool shadowing, validating parameters (CVE-2026-29791), enforcing CEL tenant policies, and proxying resilient LLM inference.
2. **Tier 2 (SaaS Connector & Managed Auth Plane - Composio Platform v3.1)**: Managed ecosystem providing 1,000+ certified toolkits (Google Workspace, Zoho Workplace, Microsoft 365, Notion, Slack, Jira, Linear, Tally, etc.), automated OAuth 2.0 lifecycle management, and user-scoped session MCP endpoints (`session.mcp.url`).
3. **Supabase (Mumbai `ap-south-1`)**: Hardware encryption of integration keys via Supabase Vault (`pgsodium`), user connection state mapping (`public.tool_connections`), and immutable audit trails with RLS.
4. **Google Cloud Platform (GCP `asia-south1`)**: Multi-container Cloud Run pod, Direct VPC Egress blocking metadata SSRF (`169.254.169.254`), and structured JSON audit logging to Cloud Logging with Composio `log_id` correlation.
5. **Google ADK 2.0 (`google-adk`)**: Python agentic runtime discovering tools via `McpToolset` / session tools, evaluating mutating action safety via `classifier.py`, and inline gating via `ToolContext.request_confirmation()`.
6. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: In-chat interactive `ApprovalCard` rendered via `useAdkToolConfirmations()`, and collapsible tool execution traces (`ToolGroup`, `ToolFallback`).

### **The North Star: Security & Mobile App Approval**
- **Security**: Zero plaintext tokens, zero container-level metadata SSRF (Cloud Run VPC egress firewall), indirect prompt injection filtering, and atomic parameter sanitization.
- **Mobile App Approval (Apple & Google Play)**: User actions execute transparently inside the chat stream; mutating actions prompt the active user directly with an interactive `ApprovalCard` without requiring external messaging apps or complex administrative approvals, guaranteeing responsive, touch-friendly mobile interaction.

---

## 2. The 5-Framework Architecture Mapping for Spec 04

| Framework / Layer | Core Responsibility in MCP & HITL | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | Supabase Vault (`pgsodium`) encrypted token storage; `public.tool_connections` (Composio session/account mappings) and `public.tool_invocations` with RLS. | Master `COMPOSIO_API_KEY` and session tokens sealed in Vault; all tool invocations logged with tenant isolation (`org_id`). |
| **2. Google Cloud Platform (GCP)** | Cloud Run multi-container networking over loopback (`127.0.0.1:8080`); Cloud Run Direct VPC Egress firewall rules. | High-priority VPC firewall drops all egress to `169.254.169.254` (metadata SSRF immunity); logs stream to Cloud Logging. |
| **3. Google ADK 2.0** | `McpToolset` / dynamic session provider; heuristic tool safety classifier; `ToolContext.request_confirmation()`. | Gating pause prevents unconfirmed write executions; resumes execution seamlessly upon user confirmation. |
| **4. assistant-ui** | Inline `ApprovalCard` powered by `useAdkToolConfirmations()`; `ToolGroup` and `ToolFallback` collapsible trace cards. | Cross-platform web & mobile (`@assistant-ui/react-native`); touch-friendly [Confirm] / [Decline] buttons. |
| **5. Agentgateway 1.5.x** | Rust proxy on loopback `:8080/mcp` fanning out tools; anti-poisoning and anti-shadowing defense; parameter sanitization. | Strips prompt injection delimiters (`<|im_start|>`, `[INST]`) from Composio/external tool definitions, blocks tool shadowing, mitigates CVE-2026-29791. |
| **Tier 2: Composio Platform** | User-scoped sessions (`composio.create(user_id=uid, mcp=True)`); 1,000+ business toolkits; managed OAuth 2.0. | Zero manual token refresh logic; upstream token revocation on user deletion (`revoke_on_delete=True`). |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/mcp/`
  * `composio_service.py`: Initializes `Composio` client, manages user-scoped sessions (`ToolRouterSessionWithMcp`), and provides Connect Links.
  * `client.py`: Configures ADK `McpToolset` pointing to Agentgateway federated endpoint (`http://127.0.0.1:8080/mcp`) and bridges user Composio session tools.
  * `classifier.py`: Automated semantic classifier inspecting MCP tool descriptions and schemas to assign `critical: true` or `critical: false`.
  * `sanitizer.py`: Deep parameter sanitizer blocking path traversal (`../`), CRLF, and shell delimiters (CVE-2026-29791).
  * `vault.py`: Wraps Supabase Vault (`vault.create_secret`, `vault.decrypted_secrets`) for Composio credentials and session state.
  * `hitl/`
    * `user_confirmation.py`: In-chat interactive confirmation handler via ADK's `ToolContext.request_confirmation()`.
  * `audit.py`: `before_tool`/`after_tool` callbacks logging to `tool_invocations` and writing structured audit logs to Google Cloud Logging with Composio `log_id`.
* `infra/agentgateway/policies/`
  * `tool_authz.cel`: Common Expression Language authorization rules filtering tools by user role and blocking unsafe parameter expressions.
* `infra/agentgateway/agentgateway.yaml`:
  * Dynamic MCP route configuration proxying Composio session endpoints on loopback.
* `supabase/migrations/20260927000004_mcp_tools_and_vault.sql`:
  * `public.tool_connections` table referencing Supabase Vault secret IDs and Composio connected account IDs.
  * `public.discovered_tools` cache table with RLS.
  * `public.tool_invocations` audit log table with RLS and Composio `log_id` column.
* `apps/web/src/components/chat/hitl-confirmation-card.tsx`: Interactive inline approval card powered by assistant-ui's `useAdkToolConfirmations()` and `useAdkConfirmTool()`.
* `apps/web/src/components/assistant-ui/elements/tool-group.aui.tsx`: Collapsible tool execution trace showing tool name, arguments, execution duration, sanitized output, and Composio `log_id`.
* `apps/mobile/src/components/chat/MobileApprovalCard.tsx`: Native mobile approval card for Expo SDK 52.

---

## 4. Requirements & Implementation Details

### R04.1: Two-Tier Credential & Session Management via Supabase Vault & Composio
- **Server API Key**: Master `COMPOSIO_API_KEY` is injected via GCP Secret Manager / Cloud Run environment variable and sealed in Supabase Vault:
  ```sql
  SELECT vault.create_secret(
    secret := '{"api_key": "ak_live_..."}',
    name := 'composio_master_key',
    description := 'Master Composio Platform project key'
  );
  ```
- **User Session Binding**: When an employee starts an agent session, Workkbot creates a user-scoped Composio session using their immutable Supabase `user_id`:
  ```python
  session = composio.create(user_id=current_user.id, mcp=True)
  ```
- Active session ID and connected account IDs are recorded in `public.tool_connections` with Supabase RLS (`user_id = auth.uid()`).
- On multi-turn conversations, the session is resumed via `composio.use(session_id, mcp=True)` to preserve authentication and execution context.

### R04.2: Federated Tool Ingestion, Anti-Poisoning & CEL Isolation via Agentgateway
- Composio session MCP URLs (`session.mcp.url`) and on-premises Indian ERP tools are federated into **Agentgateway 1.5.x** on loopback (`http://127.0.0.1:8080/mcp`):
  - **Anti-Poisoning Protection**: Agentgateway sanitizes prompt injection markers (e.g. `SYSTEM OVERRIDE`, `<|im_start|>`, `[INST]`) embedded within external tool descriptions before they reach the ADK prompt context.
  - **Anti-Shadowing Defense**: Blocks unauthorized external tools from registering duplicate names that shadow core system tools.
  - **Parameter Sanitization (CVE-2026-29791)**: `sanitizer.py` validates and strips path traversal (`../`), CRLF, and shell delimiters from all dynamic arguments.
  - **CEL Authorization**: Applies Common Expression Language rules ensuring only permitted tools are exposed to the user's role (`request.auth.claims.sub == resource.owner && request.auth.claims.org_id == resource.org_id`).

### R04.3: Automated Tool Safety Classification (Google ADK 2.0 Framework)
- `classifier.py` evaluates every dynamically discovered tool from Composio or local MCP:
  - **Mutating Action Heuristic**: Scans tool name, description, and parameters for write verbs (e.g. `send`, `create`, `delete`, `update`, `modify`, `post`, `write`, `execute`, `cancel`, `pay`, `upload`).
  - Tags matching tools (e.g. `GMAIL_SEND_MESSAGE`, `ZOHO_CREATE_INVOICE`, `SLACK_POST_MESSAGE`) as `critical: true`.
  - Pure retrieval tools (e.g. `get`, `list`, `search`, `fetch`, `read`, `query`) are tagged `critical: false`.

### R04.4: 100% User-Centric In-Chat HITL Confirmation (assistant-ui + ADK)
- When the LLM decides to invoke a tool tagged `critical: true`:
  1. The tool execution pauses via Google ADK's `ToolContext.request_confirmation(details={...})`.
  2. The Cloud Run backend emits the confirmation challenge over SSE down the active connection.
  3. The `@assistant-ui/react-google-adk` client surfaces the challenge via `useAdkToolConfirmations()`.
  4. The chat stream renders the assistant-ui `ApprovalCard`:
     - Clear title: "Authorization Required for Mutating Action".
     - Tool name, destination provider (e.g., Google Workspace, Zoho), and parameter breakdown.
     - Interactive **[Confirm & Execute]** and **[Decline]** buttons.
  5. The user clicks **[Confirm & Execute]**, triggering `confirmTool(toolCallId, true)`, resuming the ADK runner and executing the tool via `session.execute(tool_slug, arguments)` without manual refresh or admin bottlenecks.
  6. Read-only tools execute automatically and render via `ToolGroup` and `ToolFallback` with collapsible execution details.

### R04.5: Cloud Logging & Supabase Audit Trail with Composio Log Correlation
- Every tool execution emits:
  1. An immutable database record in `public.tool_invocations` storing execution time, parameters, status, and Composio `log_id`.
  2. A structured JSON audit entry to **Google Cloud Logging** with GCP trace ID linking back to the user request and Composio `log_id`.

---

## 5. Validation Scorecard & Execution Target

### **Execution Target**: `Localhost (Zero-Mock)`
- **Environment**: Next.js 15 (`localhost:3000`), FastAPI (`localhost:8000`), Agentgateway (`127.0.0.1:8080/mcp`), and live Composio Platform SDK test session.
- **Live Cloud Boundaries**:
  - Live Supabase Vault (`pgsodium`) in Mumbai (`ap-south-1`).
  - Live Google ADK in-process runner pausing turns via `ToolContext.request_confirmation()`.
  - Live Composio Platform session returning non-empty `log_id` for executed tools.
  - Live Supabase `public.tool_invocations` table and Google Cloud Logging sink for immutable audit trails.

---

### **Tier 1: Unit & Contract Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.1** | Heuristic classifier accurately flags mutating actions (`GMAIL_SEND_MESSAGE`, `ZOHO_CREATE_INVOICE`) as critical | `uv run pytest apps/backend/tests/test_classifier_heuristics.py` | [ ] |
| **VAL-04.2** | Parameter sanitization blocks path traversal, CRLF, and shell injections in tool args (CVE-2026-29791) | `uv run pytest apps/backend/tests/test_mcp_parameter_sanitization.py` | [ ] |
| **VAL-04.3** | Agentgateway anti-poisoning filter strips prompt injection markers from tool definitions | `uv run pytest apps/backend/tests/test_tool_poisoning_defense.py` | [ ] |

### **Tier 2: Zero-Mock Live Integration Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.4** | Agentgateway fans out `tools/list` across Composio session MCP and loopback endpoints | `uv run pytest apps/backend/tests/test_mcp_dynamic_registration.py` | [ ] |
| **VAL-04.5** | Live Supabase Vault stores Composio credentials and resumes user sessions with `user_id` isolation | `uv run pytest apps/backend/tests/test_vault_encryption.py` | [ ] |
| **VAL-04.6** | Mutating Composio tool pauses ADK runner stream via `request_confirmation()`; resuming on approval completes turn | `uv run pytest apps/backend/tests/test_hitl_approval_commit.py` | [ ] |
| **VAL-04.7** | Tool execution produces immutable audit record in `public.tool_invocations` with non-empty Composio `log_id` | `uv run pytest apps/backend/tests/test_tool_audit_emission.py` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.8** | In-stream `ApprovalCard` renders with tool name, formatted parameters, and [Confirm] / [Reject] buttons | `pnpm --filter @workkbot/web test:e2e tests/e2e/approval-card-render.spec.ts` | [ ] |
| **VAL-04.9** | Clicking [Confirm] transitions card badge to "Approved", executes tool, and streams final response | `pnpm --filter @workkbot/web test:e2e tests/e2e/approval-card-action.spec.ts` | [ ] |
| **VAL-04.10** | Clicking [Reject] cancels tool execution and prompts model to provide an alternate plan | `pnpm --filter @workkbot/web test:e2e tests/e2e/approval-card-reject.spec.ts` | [ ] |

### **Tier 4: Manual Verification Protocol**
1. **Trigger Mutating Tool**: In `http://localhost:3000/chat`, prompt: *"Create a calendar event for Team Standup tomorrow at 10 AM"*. Confirm the assistant pauses streaming and renders the interactive `ApprovalCard`.
2. **Inspect Approval Card**: Verify card displays:
   - Tool Name: `GOOGLECALENDAR_CREATE_EVENT` (or equivalent Composio action)
   - Parameters: `summary="Team Standup"`, `start_time="Tomorrow 10:00 AM"`
   - Security Notice: *"This action will create an external calendar event"*
3. **Approve Action**: Click **[Confirm]**. Observe card status update to *"Executing..."* and then *"Completed"*. Confirm model streams confirmation: *"I have scheduled Team Standup for tomorrow at 10 AM."*
4. **Reject Action**: In a new turn, prompt: *"Send an email to client@example.com"*. When the `ApprovalCard` appears, click **[Reject]**. Verify model responds: *"Action cancelled. Let me know if you would like to edit the message details."*
5. **Verify Audit Trail**: In Supabase table `public.tool_invocations`, verify tool records exist with accurate statuses, timestamps, and valid Composio `log_id`.
