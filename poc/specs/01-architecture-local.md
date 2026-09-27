# Workkbot Local Proof of Concept (PoC) Specification: Architecture & Runtime

## 1. System Architecture

The Local PoC implements Workkbot's production agent harness adhering strictly to Google ADK 2.0 (`google-adk` >= 2.6.2), dual OAuth 2.0 authentication, dynamic MCP toolsets, and DPDP Act 2023 compliance guardrails:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Local Streamlit Frontend                        │
│ ┌───────────────┐ ┌────────────────────┐ ┌───────────────┐ ┌─────────┐ │
│ │  @workkbot    │ │ 10 Google ⇄ Zoho   │ │ OAuth & MCP   │ │ Privacy │ │
│ │  ADK 2.0 Chat │ │ Automation Tasks   │ │ Connectors    │ │ Monitor │ │
│ └───────┬───────┘ └─────────┬──────────┘ └───────┬───────┘ └────┬────┘ │
└─────────┼───────────────────┼────────────────────┼──────────────┼──────┘
          │                   │                    │              │
          ▼                   ▼                    ▼              │
┌───────────────────────────────────────────────────────────┐     │
│       Google ADK 2.0 Agent Orchestration Harness          │     │
│                                                           │     │
│  ┌─────────────────────────────────────────────────────┐  │     │
│  │ google.adk.Agent & Runner (Gemini 2.5 Flash)        │  │     │
│  │ • Step-by-step reasoning & tool calling             │  │     │
│  │ • SQLite DatabaseSessionService (poc_sessions.db)   │  │     │
│  │ • Long-term InMemoryMemoryService                   │  │     │
│  └──────────────────────────┬──────────────────────────┘  │     │
│                             │                             │     │
│  ┌──────────────────────────▼──────────────────────────┐  │     │
│  │ ADK 2.0 Model Callbacks (`src/adk/callbacks.py`)    │◄─┼─────┘
│  │ • before_model: In-process Presidio PII Redaction   │  │
│  │ • Ephemeral RAM translation (`temp:pii_map`)        │  │
│  │ • after_model: Rehydrate tokens in response         │  │
│  └──────────────────────────┬──────────────────────────┘  │
│                             │                             │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │ ADK 2.0 Tool Callbacks (`src/adk/callbacks.py`)     │  │
│  │ • before_tool: Consent check & HITL write gate      │  │
│  │ • after_tool: <untrusted_content> Injection Shield  │  │
│  └──────────────────────────┬──────────────────────────┘  │
│                             │                             │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │ Client-Side Connected Toolsets (`WorkkbotDynamic`)  │  │
│  │                                                     │  │
│  │  ┌───────────────────────┐ ┌──────────────────────┐ │  │
│  │  │ Google Workspace REST │ │ Zoho Suite REST/MCP  │ │  │
│  │  │ • Gmail Toolset       │ │ • Zoho CRM Toolset   │ │  │
│  │  │ • Google Drive Toolset│ │ • Zoho Books Toolset │ │  │
│  │  │ • Google Calendar     │ │ • Zoho Desk Toolset  │ │  │
│  │  └───────────────────────┘ └──────────────────────┘ │  │
│  │                                                     │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │ Dual OAuth 2.0 Engine (`oauth_engine.py`)      │ │  │
│  │  │ • In-app Streamlit capture (localhost:8501)    │ │  │
│  │  │ • Multi-DC Zoho routing (.in, .com, .eu)       │ │  │
│  │  │ • Refresh token auto-renewal                   │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
          ▲
          │ Asynchronous Inbound Triggers
┌─────────┴─────────────────────────────────────────────────┐
│ Background FastAPI Webhook Server (Port 8000)             │
│ • /webhooks/google/gmail (Cloud Pub/Sub push)             │
│ • /webhooks/zoho/{module} (CRM/Books/Desk webhooks)       │
└───────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Streamlit Frontend Surface ([`src/app.py`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/src/app.py))
Provides an intuitive, tabbed interactive console:
- **Tab 1: Chat with @workkbot**:
  - Live natural language dialogue executing via Google ADK 2.0 `Agent` and `Runner`.
  - Step trace drawer displaying real-time agent thoughts, PII redactions, and dynamic tool call traces.
- **Tab 2: 10 Cross-Platform Automation Workflows**:
  - Grid of executable automation cards between Google Workspace and Zoho Suite.
  - Interactive HITL approval modal with "Approve" / "Reject" controls before mutations.
- **Tab 3: Client-Side Connected OAuth & MCP**:
  - **One-Click In-App OAuth**: Generates Google and Zoho authorization URLs redirecting to `http://localhost:8501/?code=...`.
  - Streamlit query param processor automatically captures codes, performs token exchange, and stores tokens with refresh capability.
  - Domain selector for Zoho data centers (`zoho.in`, `zoho.com`, `zoho.eu`, `zoho.com.au`).
- **Tab 4: Privacy & Compliance Monitor**:
  - Real-time Presidio PII analysis inspector showing raw prompt vs. sanitized prompt.
  - Ephemeral memory audit verifying `temp:pii_map` is held strictly in RAM.
  - Audit trail of approved and rejected HITL operations.

### 2.2 Dual OAuth 2.0 Engine ([`src/mcp/oauth_engine.py`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/src/mcp/oauth_engine.py))
- Implements RFC 6749 Authorization Code Flow with offline access for both providers:
  - **Google Workspace**: `https://accounts.google.com/o/oauth2/v2/auth` and `https://oauth2.googleapis.com/token`.
  - **Zoho Suite**: Dynamic resolution based on data center (`https://accounts.{zoho_domain}/oauth/v2/auth` and `/token`).
- Auto-refresh mechanism: Automatically refreshes access tokens using `grant_type=refresh_token` before executing live API calls.

### 2.3 Official Google ADK 2.0 Harness ([`src/adk/agent_harness.py`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/src/adk/agent_harness.py))
- **Agent**: Instantiates `google.adk.Agent` with `gemini-2.5-flash` model. Enforces `GEMINI_API_KEY` configuration.
- **Dynamic Toolset**: Subclasses `google.adk.tools.base_toolset.BaseToolset` and `BaseTool` ([`src/adk/tools.py`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/src/adk/tools.py)) to dynamically expose tools discovered on connected providers.
- **Sessions & Database**: Configures `DatabaseSessionService(db_url="sqlite+aiosqlite:///poc_sessions.db")` to persist multi-turn conversation events across application restarts.
- **Memory**: Attaches `InMemoryMemoryService` for long-term recall across sessions.

### 2.4 ADK 2.0 Guardrail Callbacks ([`src/adk/callbacks.py`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/src/adk/callbacks.py))
- `before_model`: In-process Presidio PII de-identification (DPDP Act 2023 Sec. 8(5)). Masks PAN, Aadhaar, GSTIN, emails, phone numbers into `temp:pii_map`.
- `after_model`: Rehydrates surrogate tokens back into original values in model completion.
- `before_tool`: Verifies user consent flags (`WORKSPACE_INTEGRATION`, `ZOHO_INTEGRATION`) and pauses mutating operations (`gmail.send_message`, `zoho_crm.create_lead`, etc.) for Human-In-The-Loop approval.
- `after_tool`: Encloses third-party tool responses inside `<untrusted_content>` XML envelope with SHA-256 integrity hash to neutralize indirect prompt injection.

### 2.5 Inbound Webhook Listener ([`src/api/webhook_server.py`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/src/api/webhook_server.py))
- Lightweight background FastAPI server running on `http://localhost:8000`.
- Endpoints:
  - `POST /webhooks/google/gmail`: Accepts Google Cloud Pub/Sub push notifications.
  - `POST /webhooks/zoho/{module}`: Accepts inbound Zoho CRM/Books/Desk webhooks.
  - `GET /health` & `GET /webhooks/events`: Real-time health and event stream audit.
