# Block 4 Plan: Unified MCP Tools (Workspace & Zoho), Gating & Injection Shield

## 1. Objective
Enable on-demand enterprise productivity tool integrations—Google Workspace (Gmail, Drive, Docs, Sheets, Calendar) and Zoho Suite (CRM, Mail, Desk, Analytics via `mcp.zoho.com`)—using the open **Model Context Protocol (MCP)**:
1. Build an encrypted PostgreSQL token vault (`workspace_tokens`) using `pgcrypto` column-level encryption to store OAuth refresh tokens securely for both Google and Zoho.
2. Configure Google ADK 2.6+ `McpToolset` (`from google.adk.tools.mcp_tool import McpToolset`) to connect to:
   - **Google Workspace MCP Server**: Read and write capabilities for Drive, Gmail, and Calendar.
   - **Zoho MCP Server (`mcp.zoho.com`)**: Read and write capabilities for Zoho CRM, Zoho Mail, and Zoho Desk.
3. Build ADK 2.6+ tool guard callbacks (`tool_guards.py`):
   - `before_tool_callback`: Inspects `consent_logs` for `WORKSPACE_INTEGRATION` or `ZOHO_INTEGRATION` and verifies valid decrypted OAuth tokens; returns a typed tool challenge if unconsented.
   - `after_tool_callback`: Sanitizes and encapsulates all MCP outputs inside `<untrusted_content source="mcp:{provider}:{tool}">...</untrusted_content>` boundaries to prevent indirect prompt injection.
4. Integrate frontend incremental OAuth flow via `expo-auth-session` supporting both Google and Zoho sign-in prompts.

---

## 2. Architectural Blueprint

```
+-------------------------------------------------------------+
|                  Expo App (Incremental OAuth)                |
|  - Prompts OAuth for Google or Zoho upon tool demand        |
|  - Uses expo-auth-session with PKCE                          |
+------------------------------+------------------------------+
                               | OAuth Exchange
                               v
+-------------------------------------------------------------+
|            FastAPI Encrypted Vault & MCP Orchestration       |
|  - workspace_tokens (pgcrypto AES-256 in Mumbai)            |
+------------------------------+------------------------------+
                               | ADK 2.6+ McpToolset Client
                               v
+-------------------------------------------------------------+
|               ADK 2.6+ Tool Execution Pipeline               |
|                                                             |
|  1. before_tool_callback: [tool_guards.py]                  |
|     - Verifies WORKSPACE_INTEGRATION / ZOHO_INTEGRATION     |
|     - Resolves decrypted token from pgcrypto vault          |
|     - Returns {'error': 'AUTH_REQUIRED'} if missing        |
|                                                             |
|  2. McpToolset Invocation:                                  |
|     - Google Workspace MCP (Gmail, Drive, Calendar)         |
|     - Zoho MCP Platform (CRM, Mail, Desk via mcp.zoho.com)  |
|                                                             |
|  3. after_tool_callback: [tool_guards.py]                   |
|     - Sanitizes raw output string                           |
|     - Wraps in <untrusted_content source="mcp:...">...</>   |
|     - Returns safe dictionary to model context              |
+-------------------------------------------------------------+
```

---

## 3. Dependency Sequence
1. Token Vault Migration:
   - `infra/migrations/003_vault.sql` (Creates `workspace_tokens` table with `pgcrypto` supporting Google and Zoho)
2. MCP Toolset Setup:
   - `backend/src/tools/mcp/workspace_mcp.py`
   - `backend/src/tools/mcp/zoho_mcp.py`
3. Tool Guard Callbacks & Injection Shield:
   - `backend/src/callbacks/tool_guards.py`
   - `backend/tests/test_tool_guards.py`
   - `backend/tests/test_prompt_injection.py`
4. Frontend Incremental OAuth:
   - `frontend/lib/workspace_auth.ts`
   - `frontend/components/tools/OAuthChallengeModal.tsx`
