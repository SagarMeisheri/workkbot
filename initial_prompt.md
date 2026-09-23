```markdown
You are an enterprise AI software architect and principal security engineer. Build a production-grade, client-facing Enterprise AI Assistant application end-to-end within a polyglot monorepo. 

The frontend is an Expo (React Native) cross-platform app leveraging `@assistant-ui/react-native` (following `assistant-ui/examples/with-expo`). The backend is a high-performance Python 3.12 FastAPI server powered by Google Agent Development Kit (ADK) 2.0 (`google-genai` / `google-adk`), deployed on Google Cloud Run in Mumbai (`asia-south1`). The database layer is Supabase PostgreSQL pinned to India, and integrations connect dynamically to Google Workspace APIs (Drive, Gmail, Calendar) strictly upon explicit client demand.

You must follow **Spec-Driven Development (SDD)** and guarantee **India Digital Personal Data Protection (DPDP) Act compliance from Day 1 / Block 1**.

```

---

### 1. REPOSITORY TOPOLOGY & MONOREPO STRUCTURE

Scaffold a polyglot monorepo (`pnpm` workspace for frontend/infra tools, Python packaging for backend):

```
enterprise-ai-assistant/
├── specs/                          # [SDD Persistent Memory & Blueprints]
│   ├── constitution/               # Immutable laws, techstack invariants & phased roadmap
│   │   ├── mission.md              # Vision, target audience, non-goals, DPDP anchors
│   │   ├── techstack.md            # Pinned libraries, regional locks (asia-south1), ZDR rules
│   │   └── roadmap.md              # Living tracker of Blocks 1–5 with scorecard gates
│   ├── features/                   # Phased feature specs (Plan -> Spec -> Scorecard)
│   │   ├── 01-sovereign-session/   # FastAPI shell, Supabase RLS, ADK SupabaseSessionService
│   │   ├── 02-zdr-guardrails-ui/   # ADK callbacks, PII scrubber, @assistant-ui/react-native
│   │   ├── 03-dsr-memory-lifecycle/# Retention cron, /user/forget-me, /user/export-data
│   │   ├── 04-workspace-shield/    # On-demand OAuth, tool gating, prompt injection boundaries
│   │   └── 05-hitl-cert-in-launch/ # Async HITL action cards, audit logging, Cloud Run launch
│   └── workflows/                  # SDD lifecycle rules, /clear hygiene protocol
│       └── agent-rules.md
├── frontend/                       # [Expo Mobile/Web App]
│   ├── app/                        # Expo Router routes (/(tabs), /chat, /consent, /settings)
│   ├── components/                 # Custom @assistant-ui/react-native primitives & HITL cards
│   ├── lib/                        # Supabase client with hardware-backed expo-secure-store
│   └── package.json
├── backend/                        # [FastAPI Application + Google ADK 2.0]
│   ├── src/
│   │   ├── session/                # SupabaseSessionService (ADK Python session persistence)
│   │   ├── agent/                  # ADK Runner & Vertex AI client (asia-south1, ZDR)
│   │   ├── callbacks/              # Consent gates, PII scrubber, injection shields, audit hooks
│   │   ├── tools/                  # Google Workspace handlers (Drive, Gmail, Calendar)
│   │   ├── routes/                 # SSE chat streams, DSR endpoints, OAuth handlers
│   │   └── main.py                 # FastAPI ASGI application factory & lifespan
│   ├── tests/                      # pytest test suites
│   └── pyproject.toml              # Python packaging (Python 3.12+, uv/pip compatible)
├── infra/                          # [Infrastructure as Code & Migrations]
│   ├── docker/Dockerfile           # Multi-stage Python 3.12-slim (non-root user, port 8080)
│   ├── cloudbuild.yaml             # Cloud Run build/deploy pipeline targeting asia-south1
│   └── migrations/                 # Supabase SQL: RLS, pgcrypto vault, retention cron
├── shared/                         # Cross-cutting JSON schemas and type definitions
├── pnpm-workspace.yaml
└── package.json

```

---

### 2. CORE COMPLIANCE & ARCHITECTURAL INVARIANTS

1. **Sovereignty & Region Pinning**:
* All compute, database, vector embeddings, and LLM inference must be strictly pinned to India: Google Cloud Run (`asia-south1` Mumbai), Supabase (`ap-south-1` / `asia-south1`), and Vertex AI (`asia-south1-aiplatform.googleapis.com`). No global or US multi-region endpoints are permitted.


2. **Zero Data Retention (ZDR)**:
* Configure Vertex AI Gemini Flash to disallow context caching (`SessionResumptionConfig` omitted).
* Document the mandatory Abuse Monitoring Opt-Out form and Data Processing Addendum (DPA) to disable 24-hour transient abuse logging.


3. **India DPDP Act (2023) Compliance**:
* **Notice & Itemised Consent (Sec. 5 & 6)**: Standalone, multilingual-ready consent UI. No chat processing can proceed without a valid, timestamped database consent record. Workspace tools require separate, just-in-time consent.
* **Consent Withdrawal (Sec. 6(4))**: One-tap revocation stopping active pipelines and disconnecting OAuth tokens.
* **Storage Limitation (Sec. 8(7))**: Chat logs and session context carry an automated 90-day time-to-live (TTL) via Supabase automated procedures.
* **Security Safeguards (Sec. 8(5))**: On-device auth tokens must use `expo-secure-store` (hardware Keychain/KeyStore, never unencrypted storage). Run in-flight regex masking in FastAPI memory for Indian identifiers (PAN, Aadhaar, phone numbers, emails) before prompts leave the sovereign boundary.
* **Data Principal Rights (Sec. 11–14)**: Native self-service endpoints for Right to Erasure ("Forget Me"), Right to Access (JSON export), and Grievance Redressal officer drawer.


4. **Agent Orchestration (Google ADK 2.0)**:
* Let ADK 2.0 manage session state machines, short/long-term memory, execution callbacks (`before_agent`, `before_model`, `after_model`, `before_tool`, `after_tool`, `after_agent`), and async HITL webhooks. Avoid writing ad-hoc orchestration loops.


5. **Google Workspace On-Demand Access**:
* Workspace tools remain unexposed until requested by the user.
* Enforce incremental OAuth using `expo-auth-session`/`expo-web-browser`.
* Protect against Indirect Prompt Injection: Sanitize tool output and encapsulate raw content within `` XML wrappers.
* Write actions (`send_email`, `create_calendar_event`) require explicit user confirmation via an interactive UI card before execution.



---

### 3. SPEC-DRIVEN DEVELOPMENT (SDD) LIFECYCLE

You must decouple the **"What & Why"** (markdown specifications in `specs/`) from the **"How"** (code implementation):

* **Persistent Memory**: The `specs/` folder serves as the single source of truth across agent sessions to eliminate context decay.
* **The Execution Loop**:
1. **Plan**: Define specifications (`spec.md`) and exit criteria (`scorecard.md`).
2. **Implement**: Write modular, typed code in small increments.
3. **Validate**: Run automated test suites against `scorecard.md`.
4. **Replan & Reset**: Update `roadmap.md`, prompt for git commit, and instruct the user to issue `/clear` before starting the next block.



---

### 4. PHASED BLOCK-BY-BLOCK ROADMAP

#### PHASE 0: PROJECT CONSTITUTION

* Generate `specs/constitution/mission.md`, `specs/constitution/techstack.md`, and `specs/constitution/roadmap.md`.
* Generate `specs/workflows/agent-rules.md` detailing SDD rules, `/clear` protocols, and non-negotiables.

#### BLOCK 1: SOVEREIGN FASTAPI BACKEND, SUPABASE RLS & EXPO SHELL

* **Specs**: `specs/features/01-sovereign-session/{plan.md, spec.md, scorecard.md}`
* **Deliverables**:
* Root monorepo configuration (`pnpm-workspace.yaml`, `package.json`).
* `infra/migrations/001_adk_foundation.sql`: Tables `consent_logs`, `adk_sessions` (with 90-day TTL), and `adk_events` with strict Row-Level Security (`auth.uid() = user_id`).
* `backend/`: FastAPI app, `infra/docker/Dockerfile` (Python 3.12-slim, non-root user), `infra/cloudbuild.yaml` (`asia-south1`), and `SupabaseSessionService` implementing ADK 2.0 session persistence over Supabase.
* `frontend/`: Expo app shell with Expo Router, `expo-secure-store` wrapper for Supabase Auth, and basic layout.


* **Scorecard Gates (Block 1)**:
* [ ] User B cannot read or write User A's sessions or consent logs via Supabase RLS (assert zero rows returned).
* [ ] `SupabaseSessionService` successfully creates sessions, updates state JSONB, and enforces expiration.
* [ ] FastAPI `/health` endpoint responds confirming region `asia-south1`.
* [ ] Docker container builds and runs as non-root user on port 8080.



#### BLOCK 2: ADK 2.0 LIFECYCLE CALLBACKS, ZDR GEMINI & EXPO CHAT UI

* **Specs**: `specs/features/02-zdr-guardrails-ui/{plan.md, spec.md, scorecard.md}`
* **Deliverables**:
* `backend/src/callbacks/consent_gate.py`: ADK `before_agent` callback verifying active `CORE_CHAT` consent; halts with a consent challenge if absent.
* `backend/src/callbacks/pii_scrubber.py`: ADK `before_model` and `after_model` callbacks masking Indian PAN (`[A-Z]{5}[0-9]{4}[A-Z]{1}`), Aadhaar (`[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}`), mobile numbers (`(?:\+91|91)?[6-9]\d{9}`), and emails into `{{PSEUDO_X}}` tokens, rehydrating them before client delivery.
* `backend/src/agent/vertex_client.py`: Google GenAI SDK 2.0 configured for `asia-south1` with ZDR (no context caching).
* `backend/src/routes/chat.py`: Server-Sent Events (SSE) streaming endpoint outputting ADK runner events.
* `frontend/`: Integration of `@assistant-ui/react-native` (following `assistant-ui/examples/with-expo`) connected to `/chat` SSE stream.
* `frontend/components/consent/ConsentSheet.tsx`: Native BottomSheet modal requiring itemised consent before starting chats.


* **Scorecard Gates (Block 2)**:
* [ ] Raw Aadhaar/PAN never appears in outbound Vertex AI payloads (verified via network mocks).
* [ ] Outbound LLM responses rehydrate pseudo-tokens back to original values seamlessly in the mobile UI.
* [ ] Calls without active consent are blocked at `before_agent` with HTTP 403 / Consent Challenge.



#### BLOCK 3: DATA PRINCIPAL RIGHTS (DSR) & STORAGE GOVERNANCE

* **Specs**: `specs/features/03-dsr-memory-lifecycle/{plan.md, spec.md, scorecard.md}`
* **Deliverables**:
* `backend/src/session/memory_service.py`: ADK long-term memory adapter on Supabase `pgvector` with strict PII exclusions.
* `infra/migrations/002_retention.sql`: Scheduled SQL procedure purging unpinned sessions older than 90 days (DPDP Sec. 8(7)).
* `backend/src/routes/user.py`:
* `POST /user/forget-me`: Cascading deletion of user sessions, events, memory vectors, and tokens.
* `GET /user/export-data`: Signed JSON export containing all stored user interactions and consents.


* `frontend/app/(tabs)/settings.tsx`: Privacy settings screen with "Erase All Data" button, "Export Data" button (via `expo-sharing`), and Grievance Redressal officer drawer.


* **Scorecard Gates (Block 3)**:
* [ ] Invoking `forget-me` leaves 0 residual records for that user ID across all database tables.
* [ ] Data export generates valid, structured JSON containing exclusively the authenticated user's data.



#### BLOCK 4: WORKSPACE TOOLS, `before_tool` GATING & INJECTION SHIELD

* **Specs**: `specs/features/04-workspace-shield/{plan.md, spec.md, scorecard.md}`
* **Deliverables**:
* `infra/migrations/003_vault.sql`: `workspace_tokens` table with `pgcrypto` column-level encryption. Direct client access blocked by RLS.
* `backend/src/tools/workspace/`: Google Calendar, Drive, and Gmail tool handlers.
* `backend/src/callbacks/tool_guards.py`:
* `before_tool`: Verifies `WORKSPACE_INTEGRATION` consent before execution; returns OAuth challenge if missing.
* `after_tool`: Wraps tool responses in `` XML boundaries to mitigate indirect prompt injection.


* `frontend/lib/workspace_auth.ts`: Incremental OAuth trigger using `expo-auth-session` / `expo-web-browser`.


* **Scorecard Gates (Block 4)**:
* [ ] Workspace tools reject execution and prompt for OAuth if consent is unrecorded.
* [ ] Simulated malicious emails containing prompt injections are neutralized and treated as passive data.



#### BLOCK 5: ASYNC HITL WEBHOOKS, CERT-In AUDIT & CLOUD RUN LAUNCH

* **Specs**: `specs/features/05-hitl-cert-in-launch/{plan.md, spec.md, scorecard.md}`
* **Deliverables**:
* Backend emits ADK `interaction.requires_action` event for write operations (`send_email`, `create_calendar_event`).
* `frontend/components/tools/NativeActionCard.tsx`: Interactive confirmation card ("Send Email to X with Subject Y? [Confirm / Reject]").
* `backend/src/routes/webhooks.py`: ADK webhook endpoint resuming suspended agent execution upon user sign-off.
* `backend/src/callbacks/audit.py`: ADK `after_agent` hook logging immutable audit records (NTP-synchronized timestamp, user ID, tool name, execution status) to `audit_logs` (CERT-In & DPDP compliance).
* Production verification: Deployment validation script targeting Cloud Run in `asia-south1`.


* **Scorecard Gates (Block 5)**:
* [ ] Write operations pause and execute strictly upon clicking the mobile confirmation card.
* [ ] Every agent interaction logs an append-only, tamper-resistant record in `audit_logs`.
* [ ] Container deployment passes Cloud Run readiness probes in `asia-south1`.



---

### INSTRUCTION TO BEGIN:

Start by creating **PHASE 0** and **BLOCK 1**:

1. Scaffold the monorepo root structure (`pnpm-workspace.yaml`, root `package.json`).
2. Generate all Phase 0 constitution documents under `specs/constitution/` and `specs/workflows/`.
3. Generate Block 1 specifications under `specs/features/01-sovereign-session/` (`plan.md`, `spec.md`, `scorecard.md`).
4. Implement Block 1 code (`infra/migrations/001_adk_foundation.sql`, `backend/src/session/supabase_session_service.py`, `backend/src/main.py`, `infra/docker/Dockerfile`, and Expo initial setup).
5. Run the Block 1 test suite, verify that all scorecard checks pass, and pause for confirmation before proceeding to Block 2.

```

```