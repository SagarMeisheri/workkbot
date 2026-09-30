# Spec 04: Sovereign Remote MCP Tools, Google Workspace MCP, Supabase Vault & In-Chat HITL

## 1. Context & Motivation
Connecting an enterprise AI assistant to external systems introduces severe operational and security risks, including token theft, indirect prompt injection (tool poisoning), tool shadowing, and parameter tampering (e.g. CVE-2026-29791). While third-party broker platforms (e.g., Composio) offer pre-packaged SaaS connections, they introduce third-party vendor lock-in, data sovereignty violations under the India DPDP Act 2023, high latency from extra cloud hops, and external token storage vulnerabilities.

Workkbot resolves these challenges by executing the **Sovereign DIY MCP Architecture**, strictly governed under the **5 Core Frameworks**:
1. **Agentgateway 1.5.x (Rust Infrastructure Data Plane)**: High-speed in-pod Rust proxy on loopback (`127.0.0.1:8080`), sanitizing tool descriptions against prompt injection, preventing tool shadowing, validating parameters (CVE-2026-29791), enforcing CEL tenant policies, and proxying Streamable HTTP calls to remote MCP endpoints.
2. **Google Workspace Remote MCP Servers (Developer Preview)**: Direct connection to Google's official, dedicated remote MCP servers running on Streamable HTTP transport (`gmailmcp.googleapis.com`, `drivemcp.googleapis.com`, `docsmcp.googleapis.com`, `sheetsmcp.googleapis.com`, `slidesmcp.googleapis.com`, `calendarmcp.googleapis.com`, `chatmcp.googleapis.com`, and `people.googleapis.com`).
3. **Supabase (Mumbai `ap-south-1`)**: Hardware encryption of user OAuth access and refresh tokens via Supabase Vault (`pgsodium`), connection state mapping in `public.mcp_connections`, and immutable audit trails in `public.tool_invocations` with RLS.
4. **Google Cloud Platform (GCP `asia-south1`)**: Multi-container Cloud Run pod hosting FastAPI and Agentgateway sidecar, Cloud DLP Indian PII masking on tool arguments, and Direct VPC Egress blocking metadata SSRF (`169.254.169.254`).
5. **Google ADK 2.0 (`google-adk`)**: Python agentic runtime discovering user tools dynamically via `McpToolset`, evaluating mutating action safety via `classifier.py`, and inline gating via `ToolContext.request_confirmation()`.
6. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: In-chat interactive `ApprovalCard` rendered via `useAdkToolConfirmations()`, and collapsible tool execution traces (`ToolGroup`, `ToolFallback`).

### **The North Star: Sovereign Security & Effortless End-User Experience**
- **Zero-Config End Users**: Everyday business employees never edit JSON configs or create GCP projects. They connect Google Workspace with a single click using standard OAuth 2.0 in the Connectors Hub.
- **Sovereign Security**: Zero plaintext tokens (sealed in Supabase Vault), zero container-level metadata SSRF (Cloud Run VPC egress firewall), indirect prompt injection filtering, and atomic parameter sanitization.
- **Mobile App Approval (Apple & Google Play)**: User actions execute transparently inside the chat stream; mutating actions prompt the active user directly with an interactive `ApprovalCard` without requiring external messaging apps or complex administrative approvals, guaranteeing responsive, touch-friendly mobile interaction.
- **Immediate Disconnection & DPDP Compliance**: Disconnecting Google Workspace instantly revokes upstream OAuth tokens via Google's revocation endpoint (`https://oauth2.googleapis.com/revoke`) and purges Vault keys.

---

## 2. The 5-Framework Architecture Mapping for Spec 04

| Framework / Layer | Core Responsibility in MCP & HITL | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | Supabase Vault (`pgsodium`) encrypted token storage; `public.mcp_connections` and `public.tool_invocations` with strict RLS. | All OAuth tokens sealed in Vault as `mcp_token_${user_id}_google_workspace`; all tool invocations logged with tenant isolation (`org_id`). |
| **2. Google Cloud Platform (GCP)** | Cloud Run multi-container networking over loopback (`127.0.0.1:8080`); Cloud Run Direct VPC Egress firewall rules; Cloud DLP tool masking. | High-priority VPC firewall drops all egress to `169.254.169.254` (metadata SSRF immunity); logs stream to Cloud Logging. |
| **3. Google ADK 2.0** | `McpToolset` pointing to Agentgateway endpoints; heuristic tool safety classifier; `ToolContext.request_confirmation()`. | Gating pause prevents unconfirmed write executions; resumes execution seamlessly upon user confirmation. |
| **4. assistant-ui** | Inline `ApprovalCard` powered by `useAdkToolConfirmations()`; `ToolGroup` and `ToolFallback` collapsible trace cards; Connectors Hub modal. | Cross-platform web & mobile (`@assistant-ui/react-native`); touch-friendly [Confirm] / [Decline] buttons. |
| **5. Agentgateway 1.5.x** | Rust proxy on loopback `:8080/mcp` federating the 8 Google Workspace MCP servers; anti-poisoning and anti-shadowing defense; parameter sanitization. | Strips prompt injection delimiters (`<|im_start|>`, `[INST]`) from external tool definitions, blocks tool shadowing, mitigates CVE-2026-29791. |
| **Remote MCP Servers** | Official Google Workspace remote endpoints over Streamable HTTP (`/mcp/v1`). | Native Google Workspace capabilities (Gmail, Drive, Docs, Sheets, Slides, Calendar, Chat, People) running directly on official Google infrastructure. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/mcp/`
  * `oauth_service.py`: [NEW] Manages Google OAuth 2.0 authorization code exchange, automatic token refresh, token revocation, and Vault binding.
  * `client.py`: [NEW] Configures ADK `McpToolset` pointing to Agentgateway federated endpoints (`http://127.0.0.1:8080/mcp/google/...`) with delegated user credentials.
  * `classifier.py`: [NEW] Automated semantic classifier inspecting MCP tool names and schemas to assign `critical: true` (mutating/write) or `critical: false` (read-only).
  * `sanitizer.py`: [NEW] Deep parameter sanitizer blocking path traversal (`../`), CRLF, and shell delimiters (CVE-2026-29791).
  * `hitl/`
    * `user_confirmation.py`: [NEW] In-chat interactive confirmation handler via ADK's `ToolContext.request_confirmation()`.
  * `audit.py`: [NEW] Callbacks logging to `public.tool_invocations` and writing structured audit logs to Google Cloud Logging.
* `apps/backend/src/auth/`
  * `delegation.py`: [MODIFY] Retrieves user's OAuth tokens from Supabase Vault and injects authenticated session headers for Agentgateway.
* `apps/backend/src/routers/auth.py`:
  * [MODIFY] Update Google OAuth endpoints (`/connectors/oauth/authorize`, `/connectors/oauth/callback`) to request full Google Workspace MCP scopes.
* `infra/agentgateway/agentgateway.yaml`:
  * [MODIFY] Configure Streamable HTTP routes for the 8 official Google Workspace MCP endpoints (`gmail`, `drive`, `docs`, `sheets`, `slides`, `calendar`, `chat`, `people`).
* `supabase/migrations/20260927000004_mcp_tools_and_vault.sql`:
  * [NEW] Migration creating `public.mcp_connections` and `public.tool_invocations` tables with RLS and Vault secret functions.
* `apps/web/src/components/chat/hitl-confirmation-card.tsx`:
  * [NEW] Interactive inline approval card powered by assistant-ui's `useAdkToolConfirmations()` and `useAdkConfirmTool()`.
* `apps/web/src/components/assistant-ui/elements/tool-group.aui.tsx`:
  * [NEW] Collapsible tool execution trace showing tool name, arguments, execution duration, and sanitized output.
* `apps/mobile/src/components/chat/MobileApprovalCard.tsx`:
  * [NEW] Native mobile approval card for Expo SDK 52.

---

## 4. Requirements & Implementation Details

### R04.1: Sovereign Credential & Session Management via Supabase Vault
- **App-Level OAuth Credentials**: Workkbot's verified Google Cloud OAuth `CLIENT_ID` and `CLIENT_SECRET` are configured once in environment settings (`apps/backend/src/config.py`).
- **End-User 1-Click Connection**:
  1. The user clicks **[Connect]** on Google Workspace in the Connectors Hub.
  2. Frontend opens `/api/v1/auth/connectors/oauth/authorize?provider=google_workspace`.
  3. User completes standard Google OAuth consent screen.
  4. Google redirects to `/api/v1/auth/connectors/oauth/callback` with authorization `code`.
  5. Backend exchanges `code` for `access_token`, `refresh_token`, and `expires_in`.
  6. Backend seals tokens into **Supabase Vault (`pgsodium`)** as `mcp_token_${user_id}_google_workspace`.
  7. Active connection status is recorded in `public.mcp_connections` with Supabase RLS (`user_id = auth.uid()`).
- **Automatic Token Refresh**:
  - `oauth_service.py` checks token expiration before turn execution. If expired, it calls Google's token endpoint (`https://oauth2.googleapis.com/token`) with `grant_type=refresh_token`, re-seals the fresh token into Supabase Vault, and continues seamlessly.
- **Immediate Disconnection & Token Revocation**:
  - When the user disconnects Google Workspace or triggers account deletion (`DELETE /api/v1/account/delete`), Workkbot calls Google's revocation API:
    `POST https://oauth2.googleapis.com/revoke?token={access_token}`
  - The Vault secret is purged, and `public.mcp_connections` is updated/deleted.

### R04.2: Official Google Workspace Remote MCP Endpoints via Agentgateway
- Workkbot routes all agent tool requests through **Agentgateway 1.5.x** on loopback (`http://127.0.0.1:8080/mcp/google/...`):
  - **Transport**: Streamable HTTP (`/mcp/v1`).
  - **Target Endpoints**:
    - Gmail: `https://gmailmcp.googleapis.com/mcp/v1`
    - Drive: `https://drivemcp.googleapis.com/mcp/v1`
    - Docs: `https://docsmcp.googleapis.com/mcp/v1`
    - Sheets: `https://sheetsmcp.googleapis.com/mcp/v1`
    - Slides: `https://slidesmcp.googleapis.com/mcp/v1`
    - Calendar: `https://calendarmcp.googleapis.com/mcp/v1`
    - Chat: `https://chatmcp.googleapis.com/mcp/v1`
    - People: `https://people.googleapis.com/mcp/v1`
  - **Token Injection & Delegation**:
    - Backend passes `X-Upstream-Authorization: Bearer <decrypted_google_token>`.
    - Agentgateway validates CEL policy:
      `request.auth.claims.sub == resource.owner && request.auth.claims.org_id == resource.org_id`
    - Agentgateway maps header to `Authorization: Bearer <token>` when calling Google's remote MCP servers.
  - **Anti-Poisoning & Anti-Shadowing Defense**:
    - Agentgateway sanitizes prompt injection markers (e.g. `SYSTEM OVERRIDE:`, `<|im_start|>`, `[INST]`) from external tool descriptions and outputs before they reach the model.
    - Blocks unauthorized tools from shadowing system tools.
  - **Parameter Sanitization (CVE-2026-29791)**:
    - `sanitizer.py` validates and strips path traversal (`../`), CRLF, and shell delimiters from all dynamic arguments.

### R04.3: Automated Tool Safety Classification (Google ADK 2.0 Framework)
- `classifier.py` evaluates every discovered Google Workspace tool:
  - **Mutating Action Heuristic**: Flags write/destructive operations as `critical: true`:
    - Gmail: `create_draft`, `label_message`, `label_thread`, `unlabel_message`, `unlabel_thread`
    - Drive: `create_file`, `copy_file`
    - Docs: `update_doc`
    - Sheets: `update_spreadsheet`, `update_values`, `update_formulas`, `insert_dimension`
    - Slides: `update_presentation`
    - Calendar: `create_event`, `delete_event`, `update_event`, `respond_to_event`
    - Chat: `send_message`, `mark_as_read`, `mark_as_unread`
  - **Read-Only Action Heuristic**: Flags safe queries as `critical: false`:
    - Gmail: `get_message`, `get_thread`, `list_drafts`, `list_labels`, `search_threads`
    - Drive: `search_files`, `read_file_content`, `get_file_metadata`, `get_file_permissions`, `list_recent_files`, `download_file_content`
    - Docs: `read_doc`
    - Sheets: `get_values`, `get_spreadsheet`
    - Slides: `read_presentation`
    - Calendar: `list_calendars`, `list_events`, `get_event`, `search_events`, `suggest_time`
    - Chat: `search_conversations`, `list_messages`, `search_messages`, `list_memberships`
    - People: `get_user_profile`, `search_contacts`, `search_directory_people`

### R04.4: 100% User-Centric In-Chat HITL Confirmation (assistant-ui + ADK)
- When the LLM decides to invoke a tool tagged `critical: true`:
  1. The tool execution pauses via Google ADK's `ToolContext.request_confirmation(details={...})`.
  2. The Cloud Run backend emits the confirmation challenge over SSE down the active connection.
  3. The `@assistant-ui/react` client surfaces the challenge via `useAdkToolConfirmations()`.
  4. The chat stream renders the assistant-ui `ApprovalCard`:
     - Clear title: "Action Requires Confirmation".
     - Action details: Target service (e.g., Google Calendar, Gmail), tool name, and formatted parameters.
     - Interactive **[Confirm & Execute]** and **[Decline]** buttons.
  5. The user clicks **[Confirm & Execute]**, triggering `confirmTool(toolCallId, true)`, resuming the ADK runner and executing the tool via Agentgateway without manual refresh or admin bottlenecks.
  6. Read-only tools execute automatically and render via `ToolGroup` and `ToolFallback` with collapsible execution details.

### R04.5: Cloud Logging & Supabase Audit Trail
- Every tool execution emits:
  1. An immutable database record in `public.tool_invocations` storing execution time, parameters, status, and duration.
  2. A structured JSON audit entry to **Google Cloud Logging** with GCP trace ID linking back to the user request.

---

## 5. Validation Scorecard & Execution Target

### **Execution Target**: `Localhost (Zero-Mock)`
- **Environment**: Next.js 15 (`localhost:3000`), FastAPI (`localhost:8000`), Agentgateway (`127.0.0.1:8080/mcp`), and Supabase Vault (`pgsodium`).
- **Live Cloud Boundaries**:
  - Live Supabase Vault (`pgsodium`) in Mumbai (`ap-south-1`).
  - Live Google ADK in-process runner pausing turns via `ToolContext.request_confirmation()`.
  - Live Agentgateway proxying Streamable HTTP requests to Google Workspace MCP servers.
  - Live Supabase `public.tool_invocations` table and Google Cloud Logging sink for immutable audit trails.

---

### **Tier 1: Unit & Contract Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.1** | Heuristic classifier accurately flags mutating actions (`gmail.create_draft`, `calendar.create_event`, `sheets.update_values`) as critical | `uv run pytest apps/backend/tests/mcp/test_classifier_heuristics.py` | [ ] |
| **VAL-04.2** | Parameter sanitization blocks path traversal, CRLF, and shell injections in tool args (CVE-2026-29791) | `uv run pytest apps/backend/tests/mcp/test_mcp_parameter_sanitization.py` | [ ] |
| **VAL-04.3** | Agentgateway anti-poisoning filter strips prompt injection markers from tool definitions | `uv run pytest apps/backend/tests/mcp/test_tool_poisoning_defense.py` | [ ] |

### **Tier 2: Zero-Mock Live Integration Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.4** | Agentgateway routes Streamable HTTP requests to Google Workspace MCP endpoints with CEL tenant isolation | `uv run pytest apps/backend/tests/mcp/test_google_mcp_routing.py` | [ ] |
| **VAL-04.5** | Supabase Vault stores Google OAuth credentials and retrieves tokens with `user_id` isolation | `uv run pytest apps/backend/tests/mcp/test_vault_encryption.py` | [ ] |
| **VAL-04.6** | Mutating Google tool pauses ADK runner stream via `request_confirmation()`; resuming on approval completes turn | `uv run pytest apps/backend/tests/mcp/test_hitl_approval_commit.py` | [ ] |
| **VAL-04.7** | Tool execution produces immutable audit record in `public.tool_invocations` and Cloud Logging | `uv run pytest apps/backend/tests/mcp/test_tool_audit_emission.py` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-04.8** | In-stream `ApprovalCard` renders with tool name, formatted parameters, and [Confirm] / [Decline] buttons | `pnpm --filter @workkbot/web typecheck` | [ ] |
| **VAL-04.9** | Clicking [Confirm] transitions card badge to "Approved", executes tool, and streams final response | `pnpm --filter @workkbot/web build` | [ ] |

### **Tier 4: Manual Verification Protocol**
1. **Trigger Mutating Tool**: In `http://localhost:3000/chat`, prompt: *"Create a calendar event for Team Standup tomorrow at 10 AM"*. Confirm the assistant pauses streaming and renders the interactive `ApprovalCard`.
2. **Inspect Approval Card**: Verify card displays:
   - Tool Name: `calendar.create_event`
   - Parameters: `summary="Team Standup"`, `start_time="Tomorrow 10:00 AM"`
   - Security Notice: *"Action Requires Confirmation"*
3. **Approve Action**: Click **[Confirm & Execute]**. Observe card status update to *"Executing..."* and then *"Completed"*. Confirm model streams confirmation: *"I have scheduled Team Standup for tomorrow at 10 AM."*
4. **Decline Action**: In a new turn, prompt: *"Create an email draft to client@example.com"*. When the `ApprovalCard` appears, click **[Decline]**. Verify model responds: *"Action cancelled. Let me know if you would like to edit the draft details."*
5. **Verify Audit Trail**: In Supabase table `public.tool_invocations`, verify tool records exist with accurate statuses, timestamps, and parameters.
