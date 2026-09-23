# Block 4 Specification: Unified MCP Tools (Workspace & Zoho), Gating & Injection Shield

## 1. Functional Specification

### 1.1 Multi-Provider Encrypted Token Vault Schema (`infra/migrations/003_vault.sql`)

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE public.workspace_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL, -- 'google', 'zoho'
    encrypted_access_token BYTEA NOT NULL,
    encrypted_refresh_token BYTEA NOT NULL,
    scopes TEXT[] NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    UNIQUE(user_id, provider)
);

ALTER TABLE public.workspace_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspace_tokens FORCE ROW LEVEL SECURITY;

-- Block direct client access; only accessible via secured backend service role
CREATE POLICY "block_direct_client_access" ON public.workspace_tokens
    FOR ALL USING (false);
```

---

### 1.2 ADK 2.6+ MCP Toolset Integrations (`backend/src/tools/mcp/`)

#### 1. Google Workspace MCP Toolset (`workspace_mcp.py`)
- Configured using ADK's `McpToolset`:
  ```python
  from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
  from mcp import StdioServerParameters

  def get_workspace_mcp_toolset(user_token: str) -> McpToolset:
      return McpToolset(
          connection_params=StdioConnectionParams(
              server_params=StdioServerParameters(
                  command="npx",
                  args=["-y", "@google/workspace-mcp", "--auth-token", user_token],
              ),
              timeout=15,
          ),
          tool_filter=[
              "gmail_search",
              "gmail_read_thread",
              "drive_search",
              "drive_read_file",
              "calendar_list_events",
          ],
      )
  ```

#### 2. Zoho MCP Toolset (`zoho_mcp.py`)
- Configured using ADK's `McpToolset` connecting to `mcp.zoho.com` or local server:
  ```python
  from google.adk.tools.mcp_tool import McpToolset, SseConnectionParams

  def get_zoho_mcp_toolset(user_token: str) -> McpToolset:
      return McpToolset(
          connection_params=SseConnectionParams(
              url="https://mcp.zoho.com/sse",
              headers={"Authorization": f"Bearer {user_token}"},
              timeout=15,
          ),
          tool_filter=[
              "zoho_crm_get_lead",
              "zoho_crm_search_records",
              "zoho_desk_get_ticket",
              "zoho_mail_search",
          ],
      )
  ```

---

### 1.3 ADK 2.6+ Tool Guard Callbacks & Injection Shield (`backend/src/callbacks/tool_guards.py`)

#### `before_tool_callback`
- **Signature**:
  ```python
  from google.adk.tools import BaseTool, ToolContext

  async def before_tool_guard(
      tool: BaseTool, args: dict, tool_context: ToolContext
  ) -> dict | None:
      ...
  ```
- **Execution Logic**:
  1. Identifies provider from tool name (`google_*` / `gmail_*` -> Google, `zoho_*` -> Zoho).
  2. Checks `consent_logs` for `WORKSPACE_INTEGRATION` or `ZOHO_INTEGRATION` status `'GRANTED'`.
  3. Checks `workspace_tokens` for valid decrypted credentials.
  4. If either is missing, returns an override dictionary:
     ```python
     return {
         "error": "AUTH_REQUIRED",
         "provider": provider,
         "message": f"User consent and OAuth connection required for {provider}."
     }
     ```

#### `after_tool_callback` & Prompt Injection Defense
- **Signature**:
  ```python
  async def after_tool_guard(
      tool: BaseTool, args: dict, tool_context: ToolContext, tool_response: dict
  ) -> dict | None:
      ...
  ```
- **Sanitization & Boundary Wrapping**:
  - Converts tool output into safe text, stripping control characters.
  - Wraps the content in XML isolation boundaries:
    ```xml
    <untrusted_content source="mcp:{tool.name}">
    {sanitized_content}
    </untrusted_content>
    ```
  - Replaces `tool_response` content to ensure the LLM treats all external text purely as passive data.

---

### 1.4 Frontend Incremental OAuth Integration (`frontend/lib/workspace_auth.ts`)
- Leverages `expo-auth-session` with PKCE flow.
- Supports both Google OAuth 2.0 and Zoho OAuth 2.0 endpoints.
- Sends authorization code to `/oauth/callback` for backend `pgcrypto` encryption and storage.
