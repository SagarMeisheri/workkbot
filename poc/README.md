# Workkbot Local Proof of Concept (PoC)

A standalone local implementation of **Workkbot** engineered to demonstrate the official **Google ADK 2.0 Agent Architecture** (`google-adk` >= 2.6.2), **dynamic Model Context Protocol (MCP) toolsets** for **Google Workspace** and **Zoho Suite**, **in-app Dual OAuth 2.0 authentication with auto-refresh**, **in-process Presidio PII de-identification callbacks**, **SQLite database session persistence**, **long-term memory**, and **background webhook ingestion** without requiring cloud infrastructure.

---

## 🌟 Key Highlights

1. **Official Google ADK 2.0 Agent Engine**:
   - `google.adk.Agent` powered by Gemini 2.5 Flash (`google-genai`). Requires `GEMINI_API_KEY` for reasoning chains.
   - Dynamic tool discovery using ADK `BaseToolset` and `BaseTool` subclassing.
   - Multi-turn conversation persistence via `DatabaseSessionService` backed by SQLite (`poc_sessions.db`).
   - Cross-session memory recall via `InMemoryMemoryService`.
2. **In-App Dual OAuth 2.0 Engine (Google Workspace & Zoho Suite)**:
   - **Google Workspace OAuth 2.0**: Seamless authentication for Gmail, Google Drive, and Google Calendar.
   - **Zoho Suite OAuth 2.0**: Domain-specific authentication for Zoho CRM, Books, and Desk supporting Indian (`zoho.in`), US (`zoho.com`), EU (`zoho.eu`), and Australian (`zoho.com.au`) data centers.
   - **One-Click In-App Redirection**: Automatically intercepts authorization codes on `http://localhost:8501/?code=...` using Streamlit `st.query_params`, exchanges tokens, and maintains offline token auto-refresh.
3. **ADK 2.0 Native Guardrail Callbacks**:
   - `before_model_callback`: In-process Presidio de-identification masking PAN, Aadhaar, GSTIN, emails, and phone numbers in ephemeral RAM (`temp:pii_map`).
   - `after_model_callback`: Rehydrates surrogate tokens in the final model completion before user display.
   - `before_tool_callback`: Enforces granular consent (`WORKSPACE_INTEGRATION`, `ZOHO_INTEGRATION`) and pauses mutating actions for Human-In-The-Loop approval.
   - `after_tool_callback`: Wraps third-party tool responses inside `<untrusted_content>` injection shield tags with SHA-256 integrity hashes.
4. **Background FastAPI Webhook Listener**:
   - Runs a lightweight webhook server on `http://localhost:8000/webhooks/...` listening for incoming Google Pub/Sub push notifications and Zoho CRM/Books webhooks.
5. **10 Production-Grade Cross-Platform Automations**:
   - Bi-directional task execution between Google Workspace and Zoho Suite with interactive Human-In-The-Loop approval cards.

---

## 📁 Folder Structure

```
poc/
├── README.md                      # This quickstart guide
├── pyproject.toml                 # Package definition and dependencies (uv)
├── requirements.txt               # ADK 2.0, GenAI, FastAPI, SQLite dependencies (legacy/export)
├── .env.example                   # Local configuration template
├── specs/                         # PoC architectural and functional specifications
│   ├── 00-overview.md             # PoC executive summary & cloud comparison
│   ├── 01-architecture-local.md   # Local runtime & component architecture
│   ├── 02-mcp-tools-spec.md       # Dynamic MCP tool discovery & schema catalog
│   └── 03-automation-tasks.md     # 10 Google ⇄ Zoho automation specifications
└── src/
    ├── app.py                     # Streamlit web application & OAuth receiver
    ├── core/                      # Guardrails & privacy engine
    │   ├── config.py              # Environment configuration loader
    │   ├── presidio_guard.py      # Presidio PII de-identification proxy
    │   ├── injection_shield.py    # MCP untrusted content envelope
    │   └── hitl.py                # Human-In-The-Loop approval gatekeeper
    ├── mcp/                       # Dynamic Model Context Protocol providers
    │   ├── models.py              # Standard MCP tool schemas & call results
    │   ├── oauth_engine.py        # Dual OAuth 2.0 authorization & token exchange engine
    │   ├── client_vault.py        # Client-side OAuth token manager with auto-refresh
    │   ├── google_workspace.py    # Google Workspace live REST & sandbox provider
    │   ├── zoho_suite.py          # Zoho Suite live REST & sandbox provider
    │   └── registry.py            # Dynamic MCP Tool Registry
    ├── adk/                       # Google ADK 2.0 agent harness
    │   ├── callbacks.py           # Native ADK 2.0 lifecycle callbacks
    │   ├── tools.py               # ADK 2.0 BaseToolset & BaseTool adapters
    │   └── agent_harness.py       # Agent & Runner with SQLite DatabaseSessionService
    ├── api/                       # Inbound webhook ingestion
    │   └── webhook_server.py      # Background FastAPI webhook server (port 8000)
    └── tasks/                     # 10 Cross-Platform Automation Workflows
        └── registry.py            # Workflows, parameter validation, and HITL gates
```

---

## 🚀 Quickstart: Running Locally

### 1. Prerequisites
- Python 3.10+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)
- Google Gemini API Key

### 2. Configure Environment
From the `poc/` directory:
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```
Ensure you provide:
- `GEMINI_API_KEY`: Your Google Gemini API Key (required for ADK 2.0 reasoning).
- `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`: For Google Workspace OAuth.
- `ZOHO_CLIENT_ID` & `ZOHO_CLIENT_SECRET`: For Zoho Suite OAuth.

### 3. Install Dependencies & Synchronize Environment
From within the `poc/` directory:
```bash
uv sync
```

### 4. Launch the Streamlit Application
```bash
uv run streamlit run src/app.py
```
Open your browser at `http://localhost:8501`.

---

## 🖥️ Streamlit Application Interface

The local UI is structured into 4 interactive tabs:

1. **💬 Agent Chat (`@workkbot`)**:
   - Talk to `@workkbot` in natural language.
   - Watch the agent dynamically discover available tools from connected providers.
   - Inspect step-by-step ADK execution traces, PII masking in ephemeral RAM, and prompt injection shields.
2. **⚡ 10 Google ⇄ Zoho Automations**:
   - 1-click trigger cards for all 10 enterprise workflows.
   - Real-time step logs showing tool inputs and wrapped outputs.
   - Interactive HITL approval cards for mutating actions.
3. **🔌 Client OAuth & MCP Connectors**:
   - One-click OAuth 2.0 authorization links for Google Workspace and Zoho Suite.
   - Automatic code exchange via Streamlit redirect handling (`http://localhost:8501/?code=...`).
   - Token refresh status indicators and domain routing.
4. **🛡️ Privacy & Compliance Monitor**:
   - Interactive Presidio tester to see Indian PAN, Aadhaar, GSTIN, and emails converted into surrogate tokens.
   - RAM verification confirming `temp:pii_map` is never persisted to disk or database.
   - Human-In-The-Loop approval history audit log.

---

## 🔄 The 10 Automated Tasks

| ID | Task Title | Direction | Dynamic Tools Used | HITL Gate |
| :--- | :--- | :--- | :--- | :--- |
| **T01** | Lead Ingestion & CRM Creation | Google → Zoho | `gmail.search_threads`, `zoho_crm.create_lead`, `gmail.send_message` | Approve Lead |
| **T02** | Pre-Meeting Client Dossier Generator | Zoho → Google | `calendar.list_events`, `zoho_crm.search_records`, `zoho_books.get_customer_balance`, `drive.create_file` | Read-only |
| **T03** | Overdue Invoice Chaser & Dunning | Zoho → Google | `zoho_books.get_unpaid_invoices`, `gmail.send_message` | Approve Email |
| **T04** | Contract Execution & Deal Closure | Google → Zoho | `drive.search_files`, `drive.read_file_content`, `zoho_crm.update_deal`, `zoho_books.create_invoice` | Approve Deal Win |
| **T05** | High-Priority Support Escalation Bridge | Google → Zoho | `gmail.search_threads`, `zoho_desk.create_ticket`, `calendar.create_event` | Approve Ticket |
| **T06** | Customer Financial Health Sync | Zoho → Google | `zoho_books.get_unpaid_invoices`, `zoho_crm.search_records`, `drive.create_file` | Read-only |
| **T07** | Client Onboarding Workspace Provisioner | Zoho → Google | `zoho_crm.search_records`, `drive.create_file`, `calendar.create_event` | Approve Setup |
| **T08** | Post-Meeting Minutes & CRM Action Sync | Google → Zoho | `drive.read_file_content`, `zoho_crm.update_deal`, `calendar.create_event` | Approve Notes |
| **T09** | Receipt OCR & Expense Entry | Google → Zoho | `drive.search_files`, `drive.read_file_content`, `zoho_books.record_expense` | Approve Expense |
| **T10** | Weekly Executive Revenue Digest | Bi-directional | `zoho_crm.search_records`, `zoho_books.get_unpaid_invoices`, `drive.create_file`, `gmail.create_draft` | Draft Only |
