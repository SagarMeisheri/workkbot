# Workkbot Local Proof of Concept (PoC) Specification: Dynamic MCP Tool Discovery & Schemas

## 1. Dynamic MCP Tool Discovery Architecture

In accordance with the **Model Context Protocol (MCP)** specification:
- **No static or hardcoded tools**: The agent does NOT possess pre-compiled or static tools.
- **Dynamic Runtime Discovery (`tools/list`)**: When an MCP server (Google Workspace or Zoho MCP) is connected, the agent queries the provider's `tools/list` endpoint to dynamically discover all exposed tools, descriptions, and JSON schemas (`inputSchema`).
- **State-Dependent Availability**:
  - If Google Workspace is connected, Google MCP tools become available to the agent.
  - If Zoho MCP is connected, Zoho MCP tools become available to the agent.
  - If a provider is disconnected or unconsented, all its tools are automatically purged from the agent's context.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Dynamic MCP Tool Registry                            │
├────────────────────────────────────┬────────────────────────────────────┤
│ Google Workspace MCP Client        │ Zoho MCP Server Client             │
│ [State: Connected/Disconnected]    │ [State: Connected/Disconnected]    │
│  ▼ tools/list (HTTP/SSE)           │  ▼ tools/list (HTTP/SSE)           │
│  - gmail.*                         │  - zoho_crm.*                      │
│  - drive.*                         │  - zoho_books.*                    │
│  - calendar.*                      │  - zoho_desk.*                     │
│  - docs.* / sheets.*               │  - zoho_mail.* / workdrive.*       │
└────────────────────────────────────┴────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Google ADK 2.0 Agent Harness                                            │
│ Dynamically binds currently discovered tools to LlmAgent session        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Dynamic Provider Toolsets

### 2.1 Google Workspace MCP Provider (`https://{service}mcp.googleapis.com/mcp/v1`)
Discovered dynamically via `tools/list` on each active product service:
- **Gmail Server**:
  - `gmail.search_threads`
  - `gmail.get_thread`
  - `gmail.create_draft`
  - `gmail.send_message` *(Mutating — requires HITL confirmation)*
  - `gmail.list_labels`
- **Google Drive Server**:
  - `drive.search_files`
  - `drive.read_file_content`
  - `drive.create_file` *(Mutating — requires HITL confirmation)*
  - `drive.copy_file`
- **Google Calendar Server**:
  - `calendar.list_events`
  - `calendar.create_event` *(Mutating — requires HITL confirmation)*
  - `calendar.update_event`
- **Google Docs & Sheets**:
  - `docs.read_doc`
  - `sheets.get_values`
  - `sheets.update_values` *(Mutating — requires HITL confirmation)*

### 2.2 Zoho MCP Provider (`https://mcp.zoho.com/...`)
Discovered dynamically via `tools/list` based on tools added to the Zoho MCP server:
- **Zoho CRM Tools**:
  - `zoho_crm.search_records`
  - `zoho_crm.get_contact`
  - `zoho_crm.create_lead` *(Mutating — requires HITL confirmation)*
  - `zoho_crm.update_deal` *(Mutating — requires HITL confirmation)*
- **Zoho Books Tools**:
  - `zoho_books.get_unpaid_invoices`
  - `zoho_books.get_customer_balance`
  - `zoho_books.create_invoice` *(Mutating — requires HITL confirmation)*
  - `zoho_books.record_expense` *(Mutating — requires HITL confirmation)*
- **Zoho Desk Tools**:
  - `zoho_desk.list_tickets`
  - `zoho_desk.create_ticket` *(Mutating — requires HITL confirmation)*

---

## 3. Dynamic Tool Schema Specification

Every discovered tool conforms to the standard MCP `Tool` structure:
```json
{
  "name": "gmail.search_threads",
  "description": "Searches email threads in user's Gmail mailbox matching query.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query matching standard Gmail syntax"},
      "max_results": {"type": "integer", "default": 5}
    },
    "required": ["query"]
  }
}
```

---

## 4. Security & Guardrails on Dynamic Tools
1. **Dynamic Consent Validation**: When an agent attempts to invoke a dynamically discovered tool, the guardrail checks the server source (Google vs Zoho) and enforces active consent (`WORKSPACE_INTEGRATION` vs `ZOHO_INTEGRATION`).
2. **Untrusted Content Envelope**: The output of any dynamic MCP tool call is encapsulated within `<untrusted_content source="mcp:{server}:{tool}">` before reaching the LLM reasoning loop.
3. **Dynamic HITL Detection**: Tools marked with mutation capabilities (`send_message`, `create_lead`, `update_deal`, `create_invoice`, etc.) dynamically register an approval request before mutation.
