# Enterprise AI Assistant: Living Phased Roadmap & Scorecard Tracker

## 1. Overview & Verification Status
This document tracks the phased implementation of the Sovereign Enterprise AI Assistant. Progress through each block requires satisfying all scorecard gates and passing automated test suites before proceeding.

| Phase / Block | Focus Area | Status | Target Date | Gate Pass |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Project Constitution, MCP Standards & SDD Workflows | **COMPLETED** | Block 0 | [x] |
| **Block 1** | Sovereign FastAPI Backend, Cloud SQL RLS & Expo Shell | **IN PROGRESS** | Block 1 | [ ] |
| **Block 2** | ADK 2.6 Callbacks, ZDR Gemini, SDP Guardrails & Chat UI | PLANNED | Block 2 | [ ] |
| **Block 3** | Data Principal Rights (DSR) & Storage Governance | PLANNED | Block 3 | [ ] |
| **Block 4** | Unified MCP Tools (Workspace & Zoho), Gating & Injection Shield | PLANNED | Block 4 | [ ] |
| **Block 5** | Async HITL (LongRunningFunctionTool), CERT-In Audit & Cloud Armor Launch | PLANNED | Block 5 | [ ] |

---

## 2. Block-by-Block Gate Definitions & Deliverables

### Phase 0: Project Constitution & Workflows
- [x] `specs/constitution/mission.md` (DPDP anchors, mission, non-goals, Zoho & SDP infoTypes)
- [x] `specs/constitution/techstack.md` (ADK 2.6+, MCP standard, Cloud Armor, regional locks)
- [x] `specs/constitution/roadmap.md` (living tracker & verification rubric)
- [x] `specs/workflows/agent-rules.md` (SDD lifecycle, `/clear` hygiene protocol)

### Block 1: Sovereign FastAPI Backend, Cloud SQL RLS & Expo Shell
- **Deliverables**:
  - Polyglot monorepo root setup (`pnpm-workspace.yaml`, root `package.json`)
  - `infra/migrations/001_adk_foundation.sql` (`public.users`, `consent_logs`, `adk_sessions`, `adk_events` with RLS)
  - `backend/src/session/cloud_sql_session_service.py` (ADK 2.6 session persistence over Cloud SQL)
  - `backend/src/main.py` (FastAPI shell with `/health` returning region `asia-south1`)
  - `infra/docker/Dockerfile` (multi-stage Python 3.12-slim, non-root user `appuser`, port 8080)
  - `frontend/` (Expo app shell, Expo Router, `expo-secure-store` wrapper)
- **Scorecard Gates**:
  - [ ] User B cannot read or write User A's sessions or consent logs via Cloud SQL RLS (assert zero rows returned).
  - [ ] `CloudSqlSessionService` successfully creates sessions, updates state JSONB, and enforces 90-day expiration.
  - [ ] FastAPI `/health` endpoint responds confirming region `asia-south1`.
  - [ ] Docker container builds and runs as non-root user on port 8080.

### Block 2: ADK 2.6 Lifecycle Callbacks, ZDR Gemini, SDP Guardrails & Expo Chat UI
- **Deliverables**:
  - `backend/src/callbacks/consent_gate.py` (`before_agent_callback` checking `CORE_CHAT` consent)
  - `backend/src/callbacks/pii_scrubber.py` (`before_model_callback` / `after_model_callback` using `temp:pii_map` for zero-trace in-memory redaction)
  - `backend/src/agent/vertex_client.py` (Google GenAI SDK 2.0 in `asia-south1` with ZDR)
  - `backend/src/routes/chat.py` (SSE streaming ADK runner events)
  - `frontend/` (`@assistant-ui/react-native` integration connected to SSE stream)
  - `frontend/components/consent/ConsentSheet.tsx` (Itemised consent modal)
- **Scorecard Gates**:
  - [ ] Raw Aadhaar/PAN never appears in outbound Vertex AI payloads (verified via network mocks).
  - [ ] Outbound LLM responses rehydrate pseudo-tokens back to original values seamlessly in the mobile UI.
  - [ ] `temp:pii_map` is verified to never be written to database or persistent session state.
  - [ ] Calls without active consent are blocked at `before_agent_callback` with HTTP 403 / Consent Challenge.

### Block 3: Data Principal Rights (DSR) & Storage Governance
- **Deliverables**:
  - `backend/src/session/memory_service.py` (Cloud SQL `pgvector` memory service with PII gating)
  - `infra/migrations/002_retention.sql` (Scheduled procedure purging records older than 90 days)
  - `backend/src/routes/user.py` (`POST /user/forget-me`, `GET /user/export-data`)
  - `frontend/app/(tabs)/settings.tsx` (DSR UI: Erase Data, Export Data, DPO contact drawer)
- **Scorecard Gates**:
  - [ ] Invoking `forget-me` leaves 0 residual records for that user ID across all database tables.
  - [ ] Data export generates valid, structured JSON containing exclusively the authenticated user's data.

### Block 4: Unified MCP Tools (Workspace & Zoho), Gating & Injection Shield
- **Deliverables**:
  - `infra/migrations/003_vault.sql` (`workspace_tokens` table with `pgcrypto` encryption)
  - `backend/src/tools/mcp/`: Configuration for Google Workspace MCP Server and Zoho MCP Server (`mcp.zoho.com`) via ADK's `McpToolset`.
  - `backend/src/callbacks/tool_guards.py`:
    - `before_tool_callback`: Verifies itemised consent (`WORKSPACE_INTEGRATION`, `ZOHO_INTEGRATION`) and valid tokens.
    - `after_tool_callback`: Wraps all MCP responses in `<untrusted_content source="mcp:{server}:{tool}">` XML tags.
  - `frontend/lib/workspace_auth.ts`: Incremental OAuth triggers for Google and Zoho.
- **Scorecard Gates**:
  - [ ] MCP tools reject execution and prompt for OAuth if itemised consent is unrecorded.
  - [ ] Simulated malicious emails and CRM notes containing prompt injections are neutralized within `<untrusted_content>`.
  - [ ] Google Workspace MCP and Zoho MCP tools are discovered and converted to ADK tools via `McpToolset`.

### Block 5: Async HITL (LongRunningFunctionTool), CERT-In Audit & Cloud Armor Launch
- **Deliverables**:
  - ADK `LongRunningFunctionTool` configuration for state-changing write operations (`send_email`, `create_calendar_event`, `create_crm_deal`).
  - `frontend/components/tools/NativeActionCard.tsx` (Interactive confirmation card).
  - `backend/src/routes/webhooks.py` (ADK HITL resumption endpoint matching `function_call_id`).
  - `backend/src/callbacks/audit.py` (CERT-In compliant append-only `audit_logs`).
  - `infra/cloudbuild.yaml` & Cloud Armor security policy attaching to Serverless NEG in `asia-south1`.
- **Scorecard Gates**:
  - [ ] Write operations pause and execute strictly upon user confirmation on the mobile card.
  - [ ] Every agent interaction logs an append-only, tamper-resistant record in `audit_logs`.
  - [ ] Container deployment passes Cloud Run readiness probes behind Cloud Armor in `asia-south1`.
