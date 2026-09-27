# Spec 04: Dynamic MCP Tools, Supabase Vault & In-Chat HITL Gateway (GCP Day 1)

## 1. Context & Motivation
Connecting an AI assistant to external systems introduces real operational and security risk. 
To prevent token theft, routing bottlenecks, and emerging AI attack vectors (tool poisoning, tool shadowing, and parameter injection):
1. **Supabase Vault (Mumbai)**: User OAuth tokens are encrypted at rest using **Supabase Vault (`pgsodium`)**, eliminating the need for complex custom KMS orchestration.
2. **Agentgateway Federated MCP Hub (Loopback `127.0.0.1:8080/mcp`)**: Rather than managing fragile stateful SSE/stdio sessions in Python, **Agentgateway 1.5.x (Rust)** aggregates and virtualizes multiple MCP servers (Google Workspace, Zoho, GitHub, Notion). It handles session fan-out, bidirectional events, and protocol upgrades with sub-millisecond overhead.
3. **Anti-Poisoning & Shadowing Defense**: Agentgateway sanitizes tool definitions to neutralize indirect prompt injection, prevents untrusted tools from shadowing built-in actions, and enforces parameter sanitization (mitigating CVE-2026-29791).
4. **Backend Semantic Tool Classification & CEL RBAC**: Agentgateway evaluates role-based CEL policies on tool discovery. The backend classifies remaining tools as read-only vs. mutating/critical.
5. **100% User-Centric In-App Confirmation**: Write-capable actions require the **individual user** to confirm execution directly in their chat stream via an interactive card. An In-App Notification Center (synced via Supabase Realtime) and mobile push alerts (Firebase Cloud Messaging) notify the user if they are away from the thread.

## 2. Objective & Non-Goals
- **Objective**: Authenticated users connect external services via OAuth; tokens are stored in Supabase Vault; Agentgateway discovers, federates, and sanitizes available tools; mutating actions pause and render an inline interactive card in that user's chat for self-approval; invocations are recorded in Supabase PostgreSQL and streamed to Google Cloud Logging via OpenTelemetry.
- **Non-Goals**: No external third-party alert channels (e.g. no WhatsApp). No admin approval bottlenecks for an employee's personal tool execution.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/mcp/`
  * `client.py`: Configures ADK `McpToolset` pointing to Agentgateway federated endpoint (`http://127.0.0.1:8080/mcp`).
  * `classifier.py`: Automated semantic classifier inspecting MCP tool descriptions and schemas to assign `critical: true` or `critical: false`.
  * `vault.py`: Wraps Supabase Vault (`vault.create_secret`, `vault.decrypted_secrets`) for token storage and runtime injection.
  * `hitl/`
    * `user_confirmation.py`: In-chat interactive confirmation handler via ADK's `ToolContext.request_confirmation()`.
  * `audit.py`: `before_tool`/`after_tool` callbacks logging to `tool_invocations` and writing structured audit logs to Google Cloud Logging.
* `infra/agentgateway/policies/`
  * `tool_authz.cel`: Common Expression Language authorization rules filtering tools by user role and blocking unsafe parameter expressions.
* `supabase/migrations/20260927000004_mcp_tools_and_vault.sql`:
  * `public.tool_connections` table referencing Supabase Vault secret IDs.
  * `public.discovered_tools` cache table with RLS.
  * `public.tool_invocations` audit log table with RLS.
* `apps/web/src/components/chat/hitl-confirmation-card.tsx`: Interactive inline approval card powered by assistant-ui's `useAdkToolConfirmations()` and `useAdkConfirmTool()`.
* `apps/web/src/components/assistant-ui/elements/tool-group.aui.tsx`: Collapsible tool execution trace showing tool name, arguments, execution duration, and sanitized output.

---

## 4. Requirements & Implementation Details

### R04.1: Hardware Encryption via Supabase Vault
- When an employee authorizes an MCP provider via OAuth, the access/refresh token pair is encrypted into **Supabase Vault**:
  ```sql
  SELECT vault.create_secret(
    secret := '{ "access_token": "...", "refresh_token": "..." }',
    name := 'mcp_token_' || user_id || '_' || provider_id,
    description := 'Encrypted MCP OAuth credentials'
  );
  ```
- The backend on Cloud Run retrieves decrypted tokens only at execution time via `vault.decrypted_secrets` under the user's authenticated session context, injecting them into Agentgateway upstream session headers.

### R04.2: Federated Tool Discovery via Agentgateway 1.5.x
- While Google Workspace and Zoho Workplace serve as initial Day-1 starter connectors, Agentgateway dynamically federates an **open-ended catalog of MCP server endpoints** configured in `agentgateway.yaml` or added dynamically via the Connectors Hub (Microsoft 365, Notion, Slack, Canva, Figma, Atlassian Jira/Confluence, HubSpot, Asana, Linear, Tally, Zoho Books).
- Users browse **Connectors -> Discover** in the assistant-ui composer, click **[Connect]** on their desired service, complete OAuth 2.0 authorization, and register the connection.
- Upon successful authentication, the ADK `McpToolset` invokes `tools/list` on `http://127.0.0.1:8080/mcp`:
  - Agentgateway fans out `tools/list` across all connected MCP backends concurrently.
  - Applies CEL authorization filtering based on the caller's JWT role claims and tenant scope.
  - Returns a unified, deduplicated tool schema catalog to the ADK `LlmAgent`.

### R04.3: Automated Tool Safety Classification
- `classifier.py` evaluates every dynamically discovered tool upon connection:
  - **Mutating Action Heuristic**: Scans tool name, description, and input parameters for action verbs (e.g. `send`, `create`, `delete`, `update`, `modify`, `post`, `write`, `execute`, `cancel`, `remove`, `pay`).
  - Tags matching tools as `critical: true`.
  - Tools with purely retrieval verbs (e.g. `get`, `list`, `search`, `fetch`, `read`, `query`) are tagged `critical: false`.

### R04.4: 100% User-Centric In-Chat HITL Confirmation via Assistant-UI
- When the LLM decides to call a tool tagged `critical: true`:
  1. The tool pauses execution via ADK's `ToolContext.request_confirmation()`.
  2. The Cloud Run backend emits the confirmation challenge over SSE down the active connection.
  3. The `@assistant-ui/react-google-adk` client intercepts the challenge and surfaces it through the `useAdkToolConfirmations()` hook.
  4. The chat UI renders the assistant-ui `ApprovalCard` containing:
     - Clear title: "Authorization Required for Mutating Action".
     - Tool name and parameter breakdown.
     - Confirmation hint.
     - **[Confirm & Execute]** and **[Decline]** interactive buttons.
  5. The user clicks **[Confirm & Execute]**, which triggers `confirmTool(toolCallId, true)`, resuming the ADK runner and executing the tool without manual refresh or admin bottlenecks.
  6. Read-only tools render automatically via `ToolGroup` and `ToolFallback` with collapsible execution details.

### R04.5: Cloud Logging & Supabase Audit Trail
- Every tool execution emits:
  1. A database record in `public.tool_invocations` with execution time and parameters.
  2. A structured JSON audit entry to **Google Cloud Logging** with trace ID linking back to the user request.

### R04.6: Anti-Poisoning, Anti-Shadowing & Parameter Sanitization
- In `agentgateway.yaml`:
  - `enableToolPoisoningProtection: true`: Gateway strips indirect prompt injection triggers (e.g. `SYSTEM OVERRIDE`, `<instructions>`) embedded within tool descriptions.
  - `preventShadowing: true`: Blocks third-party tools from overriding built-in system tools.
  - `sanitizeParameters: true`: Mitigates **CVE-2026-29791** by validating and stripping path traversal, CRLF, and unescaped delimiters from dynamic tool parameters.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.1** | User OAuth tokens are encrypted in Supabase Vault and decrypted only at runtime | `pytest apps/backend/tests/test_vault_encryption.py` | [ ] |
| **VAL-04.2** | Agentgateway fans out `tools/list` across multiple MCP servers into a single unified catalog | `pytest apps/backend/tests/test_mcp_dynamic_registration.py` | [ ] |
| **VAL-04.3** | Automated classifier correctly tags `create_issue` as critical and `search_issues` as read-only | `pytest apps/backend/tests/test_classifier_heuristics.py` | [ ] |
| **VAL-04.4** | Calling a mutating tool displays the inline confirmation card directly to the active user | `pytest apps/backend/tests/test_hitl_inline_prompt.py` | [ ] |
| **VAL-04.5** | Approving a tool action on Cloud Run commits execution and streams final reply | `pytest apps/backend/tests/test_hitl_approval_commit.py` | [ ] |
| **VAL-04.6** | Every tool execution produces an immutable record in `tool_invocations` & Cloud Logging | `pytest apps/backend/tests/test_tool_audit_emission.py` | [ ] |
| **VAL-04.7** | Agentgateway blocks tool definition containing indirect prompt injection payload | `pytest apps/backend/tests/test_tool_poisoning_defense.py` | [ ] |
| **VAL-04.8** | Parameter sanitization rejects path traversal and CRLF injections in tool args (CVE-2026-29791) | `pytest apps/backend/tests/test_mcp_parameter_sanitization.py` | [ ] |
