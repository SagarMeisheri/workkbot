# Spec 04: Dynamic MCP Tools, Supabase Vault & In-Chat HITL Gateway (GCP Day 1)

## 1. Context & Motivation
Connecting an AI assistant to external systems introduces real operational and security risk. 
To prevent token theft and routing bottlenecks:
1. **Supabase Vault (Mumbai)**: User OAuth tokens are encrypted at rest using **Supabase Vault (`pgsodium`)**, eliminating the need for complex custom KMS orchestration.
2. **Dynamic MCP Tooling on Cloud Run**: Workkbot manages standard MCP server endpoints. Users simply connect their accounts via standard OAuth; tools are discovered dynamically via `tools/list`.
3. **Backend Semantic Tool Classification**: Workkbot automatically classifies discovered tools as read-only vs. mutating/critical based on tool names, descriptions, and input schemas.
4. **100% User-Centric In-App Confirmation**: Write-capable actions require the **individual user** to confirm execution directly in their chat stream via an interactive card. An In-App Notification Center (synced via Supabase Realtime) and mobile push alerts (Firebase Cloud Messaging) notify the user if they are away from the thread.

## 2. Objective & Non-Goals
- **Objective**: Authenticated users connect external services via OAuth; tokens are stored in Supabase Vault; Workkbot dynamically discovers available tools from the MCP server; mutating actions pause and render an inline interactive card in that user's chat for self-approval; invocations are recorded in Supabase PostgreSQL and streamed to Google Cloud Logging.
- **Non-Goals**: No external third-party alert channels (e.g. no WhatsApp). No admin approval bottlenecks for an employee's personal tool execution.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/mcp/`
  * `client.py`: Manages dynamic ADK `McpToolset` connections over SSE/stdio transports from Cloud Run.
  * `classifier.py`: Automated semantic classifier inspecting MCP tool descriptions and schemas to assign `critical: true` or `critical: false`.
  * `vault.py`: Wraps Supabase Vault (`vault.create_secret`, `vault.decrypted_secrets`) for token storage and decryption.
  * `hitl/`
    * `user_confirmation.py`: In-chat interactive confirmation handler via ADK's `ToolContext.request_confirmation()`.
  * `audit.py`: `before_tool`/`after_tool` callbacks logging to `tool_invocations` and writing structured audit logs to Google Cloud Logging.
* `supabase/migrations/20260927000004_mcp_tools_and_vault.sql`:
  * `public.tool_connections` table referencing Supabase Vault secret IDs.
  * `public.discovered_tools` cache table with RLS.
  * `public.tool_invocations` audit log table with RLS.
* `apps/web/src/components/chat/hitl-confirmation-card.tsx`: Interactive inline approval card.

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
- The backend on Cloud Run retrieves decrypted tokens only at execution time via `vault.decrypted_secrets` under the user's authenticated session context.

### R04.2: Dynamic Tool Discovery via Standard MCP
- Workkbot configures the target MCP server endpoints for providers (e.g. Google Workspace, Zoho Workplace, GitHub, Notion).
- Users click **"Connect Account"**, complete standard OAuth 2.0 authorization, and Workkbot registers the connection.
- Upon successful authentication, Workkbot connects to the MCP server and invokes `tools/list`:
  - Dynamically extracts tool names, descriptions, and input JSON schemas.
  - Registers these tools into the active user's ADK `LlmAgent` session.

### R04.3: Automated Tool Safety Classification
- `classifier.py` evaluates every dynamically discovered tool upon connection:
  - **Mutating Action Heuristic**: Scans tool name, description, and input parameters for action verbs (e.g. `send`, `create`, `delete`, `update`, `modify`, `post`, `write`, `execute`, `cancel`, `remove`, `pay`).
  - Tags matching tools as `critical: true`.
  - Tools with purely retrieval verbs (e.g. `get`, `list`, `search`, `fetch`, `read`, `query`) are tagged `critical: false`.

### R04.4: 100% User-Centric In-Chat HITL Confirmation
- When the LLM decides to call a tool tagged `critical: true`:
  1. The tool pauses execution via ADK's `ToolContext.request_confirmation()`.
  2. The Cloud Run backend emits an SSE event down the user's active chat stream:
     ```json
     {
       "type": "tool_confirmation_required",
       "tool_call_id": "call_abc123",
       "tool_name": "send_email",
       "hint": "Send email to rahul@company.in with subject 'Proposal'",
       "arguments": {"to": "rahul@company.in", "subject": "Proposal", "body": "..."}
     }
     ```
  3. The chat UI renders an inline card with **[Approve & Run]** and **[Cancel]** buttons.
  4. The user clicks **[Approve & Run]**, triggering the tool to execute immediately.

### R04.5: Cloud Logging & Supabase Audit Trail
- Every tool execution emits:
  1. A database record in `public.tool_invocations` with execution time and parameters.
  2. A structured JSON audit entry to **Google Cloud Logging** with trace ID linking back to the user request.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.1** | User OAuth tokens are encrypted in Supabase Vault and decrypted only at runtime | `pytest apps/backend/tests/test_vault_encryption.py` | [ ] |
| **VAL-04.2** | Connecting an MCP server dynamically registers all discovered tools in user session | `pytest apps/backend/tests/test_mcp_dynamic_registration.py` | [ ] |
| **VAL-04.3** | Automated classifier correctly tags `create_issue` as critical and `search_issues` as read-only | `pytest apps/backend/tests/test_classifier_heuristics.py` | [ ] |
| **VAL-04.4** | Calling a mutating tool displays the inline confirmation card directly to the active user | `pytest apps/backend/tests/test_hitl_inline_prompt.py` | [ ] |
| **VAL-04.5** | Approving a tool action on Cloud Run commits execution and streams final reply | `pytest apps/backend/tests/test_hitl_approval_commit.py` | [ ] |
| **VAL-04.6** | Every tool execution produces an immutable record in `tool_invocations` & Cloud Logging | `pytest apps/backend/tests/test_tool_audit_emission.py` | [ ] |
