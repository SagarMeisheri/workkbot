# Spec 04: Dynamic MCP Tools, Supabase Vault & In-Chat HITL (The 5-Framework Architecture)

## 1. Context & Motivation
Connecting an AI assistant to external systems introduces severe operational and security risks, including token theft, indirect prompt injection (tool poisoning), tool shadowing, and parameter tampering (e.g. CVE-2026-29791). 

Workkbot mitigates these risks by routing all tool connection, discovery, sanitization, and execution decisions through the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Hardware encryption of third-party OAuth credentials via Supabase Vault (`pgsodium`) and immutable audit trails in PostgreSQL with RLS.
2. **Google Cloud Platform (GCP `asia-south1`)**: Cloud Run multi-container execution, Direct VPC Egress blocking access to Google Cloud Metadata (`169.254.169.254`), and structured JSON audit logging to Cloud Logging.
3. **Google ADK 2.0 (`google-adk`)**: Stateful `McpToolset` connecting to loopback, heuristic semantic tool classification, and inline execution gating via `ToolContext.request_confirmation()`.
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: In-chat interactive `ApprovalCard` rendered via `useAdkToolConfirmations()`, and collapsible tool execution traces (`ToolGroup`, `ToolFallback`).
5. **Agentgateway 1.5.x**: High-performance Rust proxy federating open-ended MCP servers, sanitizing tool descriptions against prompt injection, preventing tool shadowing, sanitizing tool arguments, and enforcing CEL role policies.

### **The North Star: Security & Mobile App Approval**
- **Security**: Zero plaintext tokens (stored in Supabase Vault), zero container-level SSRF (Cloud Run VPC egress firewall), indirect prompt injection filtering, and atomic parameter sanitization.
- **Mobile App Approval (Apple & Google Play)**: User actions execute transparently inside the chat stream; mutating actions prompt the active user directly with an interactive `ApprovalCard` without requiring external messaging apps or complex administrative approvals, guaranteeing responsive, touch-friendly mobile interaction.

---

## 2. The 5-Framework Architecture Mapping for Spec 04

| Framework | Core Responsibility in MCP & HITL | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | Supabase Vault (`pgsodium`) encrypted token storage; `public.tool_connections` and `public.tool_invocations` with RLS. | Tokens are sealed with hardware encryption; all tool invocations are logged with tenant isolation (`org_id`). |
| **2. Google Cloud Platform (GCP)** | Cloud Run multi-container networking over loopback (`127.0.0.1:8080`); Cloud Run Direct VPC Egress firewall rules. | High-priority VPC firewall drops all egress to `169.254.169.254` (metadata SSRF immunity); logs stream to Cloud Logging. |
| **3. Google ADK 2.0** | `McpToolset` interfacing with Agentgateway; heuristic tool safety classifier; `ToolContext.request_confirmation()`. | Gating pause prevents unconfirmed write executions; resumes execution seamlessly upon user confirmation. |
| **4. assistant-ui** | Inline `ApprovalCard` powered by `useAdkToolConfirmations()`; `ToolGroup` and `ToolFallback` collapsible trace cards. | Cross-platform web & mobile (`@assistant-ui/react-native`); touch-friendly [Confirm] / [Decline] buttons. |
| **5. Agentgateway 1.5.x** | Rust proxy on loopback `:8080/mcp` fanning out `tools/list`; anti-poisoning and anti-shadowing defense; parameter sanitization. | Strips prompt injection from tool descriptions, blocks tool shadowing, mitigates CVE-2026-29791 parameter injection. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
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
* `apps/mobile/src/components/chat/MobileApprovalCard.tsx`: Native mobile approval card for Expo SDK 52.

---

## 4. Requirements & Implementation Details

### R04.1: Hardware Encryption via Supabase Vault (Supabase Framework)
- When an employee authorizes an MCP provider via OAuth in the Connectors Hub, the token pair is encrypted into **Supabase Vault**:
  ```sql
  SELECT vault.create_secret(
    secret := '{ "access_token": "...", "refresh_token": "..." }',
    name := 'mcp_token_' || user_id || '_' || provider_id,
    description := 'Encrypted MCP OAuth credentials'
  );
  ```
- The backend on Cloud Run retrieves decrypted tokens only at execution time via `vault.decrypted_secrets` under the user's authenticated session context, injecting them into Agentgateway upstream session headers.

### R04.2: Federated Tool Discovery & Anti-Poisoning via Agentgateway (Agentgateway Framework)
- Agentgateway dynamically federates an **open-ended catalog of MCP servers** (Google Workspace, Zoho Workplace, Microsoft 365, Notion, Slack, Canva, Figma, Atlassian Jira/Confluence, HubSpot, Asana, Linear, Tally, Zoho Books).
- Upon client connection, the ADK `McpToolset` calls `tools/list` on `http://127.0.0.1:8080/mcp`:
  - **Anti-Poisoning Protection**: Agentgateway sanitizes prompt injection markers (e.g. `SYSTEM OVERRIDE`, `<instructions>`) embedded within third-party tool descriptions.
  - **Anti-Shadowing Defense**: Blocks unauthorized external tools from registering duplicate names that shadow core system tools.
  - **Parameter Sanitization (CVE-2026-29791)**: Validates and sanitizes path traversal characters (`../`), CRLF, and shell delimiters from all dynamic arguments.
  - **CEL Authorization**: Applies Common Expression Language rules ensuring only permitted tools are exposed to the user's role.

### R04.3: Automated Tool Safety Classification (Google ADK 2.0 Framework)
- `classifier.py` evaluates every dynamically discovered tool:
  - **Mutating Action Heuristic**: Scans tool name, description, and parameters for write verbs (e.g. `send`, `create`, `delete`, `update`, `modify`, `post`, `write`, `execute`, `cancel`, `pay`).
  - Tags matching tools as `critical: true`.
  - Pure retrieval tools (e.g. `get`, `list`, `search`, `fetch`, `read`, `query`) are tagged `critical: false`.

### R04.4: 100% User-Centric In-Chat HITL Confirmation (assistant-ui + ADK)
- When the LLM decides to invoke a tool tagged `critical: true`:
  1. The tool pauses execution via ADK's `ToolContext.request_confirmation()`.
  2. The Cloud Run backend emits the confirmation challenge over SSE down the active connection.
  3. The `@assistant-ui/react-google-adk` client surfaces the challenge via `useAdkToolConfirmations()`.
  4. The chat stream renders the assistant-ui `ApprovalCard`:
     - Clear title: "Authorization Required for Mutating Action".
     - Tool name, destination, and parameter breakdown.
     - Interactive **[Confirm & Execute]** and **[Decline]** buttons.
  5. The user clicks **[Confirm & Execute]**, triggering `confirmTool(toolCallId, true)`, resuming the ADK runner and executing the tool without manual refresh or admin bottlenecks.
  6. Read-only tools render automatically via `ToolGroup` and `ToolFallback` with collapsible execution details.

### R04.5: Cloud Logging & Supabase Audit Trail (GCP + Supabase)
- Every tool execution emits:
  1. An immutable database record in `public.tool_invocations` with execution time and parameters.
  2. A structured JSON audit entry to **Google Cloud Logging** with trace ID linking back to the user request.

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
| **VAL-04.9** | ApprovalCard renders and confirms smoothly on React Native mobile app | `pnpm --filter mobile test:e2e tests/e2e/approval-card.spec.ts` | [ ] |
