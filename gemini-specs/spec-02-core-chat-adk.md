# Spec 02: Core Chat on Google ADK 2.0 & Cloud Run Streaming (The 5-Framework Architecture)

## 1. Context & Motivation
With identity and statutory consent verified via Supabase Auth, this spec establishes the core conversational chat engine. 
The conversational core must deliver lightning-fast time-to-first-token (TTFT < 800ms), resilient multi-model failover, durable multi-turn state persistence, and full mobile cross-platform parity while maintaining uncompromising security and meeting Apple App Store Review Guideline 1.2 (mandatory AI moderation & user reporting).

All chat decisions route through the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Durable relational persistence for ADK sessions, event trees, and conversation metadata, secured by PostgreSQL Row-Level Security (RLS).
2. **Google Cloud Platform (GCP `asia-south1`)**: Cloud Run multi-container pod hosting FastAPI and Agentgateway, HTTP/2 SSE streaming, Cloud Load Balancing, and Vertex AI (`gemini-2.0-flash` / `gemini-2.0-pro`).
3. **Google ADK 2.0 (`google-adk`)**: In-process agentic runtime executing `LlmAgent`, orchestrating event cycles, and managing event-tree branching checkpoints.
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-google-adk`, `@assistant-ui/react-native`)**: Cross-platform declarative chat surface, `ThreadListSidebar`, floating composer with `+` action menu, `BranchPickerPrimitive`, `Reasoning`, `Sources`, and `ActionBarPrimitive`.
5. **Agentgateway 1.5.x**: High-speed Rust proxy on loopback `127.0.0.1:8080/v1`, shielding the LLM, managing upstream circuit breaking, token telemetry, and automatic model failover.

### **The North Star: Security & Mobile App Approval**
- **Security**: In-process ADK execution eliminates external unencrypted network hops; Supabase RLS guarantees zero cross-tenant session leaks; Cloud Run Direct VPC Egress blocks SSRF.
- **Mobile App Approval (Apple Guideline 1.2 & Google Play AI Safety)**: Every assistant chat bubble on web and mobile incorporates assistant-ui's `ActionBarPrimitive` embedding a mandatory **"Report / Flag AI Content"** button opening an immediate moderation dialog.

---

## 2. The 5-Framework Architecture Mapping for Spec 02

| Framework | Core Responsibility in Core Chat | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | Persists ADK sessions, event logs, app state, and user state via `DatabaseSessionService`; `public.conversations` with RLS. | Multi-tenant isolation: `org_id = (auth.jwt() ->> 'org_id')::uuid`. Purging user deletes all chat history (Apple 5.1.1). |
| **2. Google Cloud Platform (GCP)** | Multi-container Cloud Run pod streaming SSE over HTTP/2; Vertex AI Gemini 2.0 Flash/Pro; Cloud Load Balancing keep-alives. | Zero-cold-start compute in Mumbai (`asia-south1`); direct VPC egress drops metadata requests (`169.254.169.254`). |
| **3. Google ADK 2.0** | In-process Python `Runner` hosting `LlmAgent(name="workkbot_core")`; manages multi-turn event history and branching. | Event-based state checkpointing prevents state pollution; runs within isolated Python container. |
| **4. assistant-ui** | Unified chat surface powered by `@assistant-ui/react-google-adk` (`useAdkRuntime`); renders `ThreadListSidebar`, `BranchPickerPrimitive`, `Reasoning`, and `ActionBarPrimitive`. | Provides instant in-app AI report/flag modal on every message (Apple 1.2); native 60fps rendering on `@assistant-ui/react-native`. |
| **5. Agentgateway 1.5.x** | Loopback proxy (`127.0.0.1:8080/v1`) routing ADK requests to Vertex AI with automated circuit-breaker failover. | Strips malformed tokens, monitors rate limits, and provides seamless fallback from Flash to Pro during peak spikes without dropping streams. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/agent/`
  * `agent.py`: Instantiates the primary Google ADK 2.0 `LlmAgent(name="workkbot_core")` configured with OpenAI/Vertex-compatible client pointing to Agentgateway (`http://127.0.0.1:8080/v1`).
  * `runner.py`: Sets up ADK `Runner` configured with `DatabaseSessionService` pointed at Supabase PostgreSQL (via SQLAlchemy/asyncpg).
  * `model_tier.py`: Manages model selection headers passed to Agentgateway (defaulting to Vertex AI `gemini-2.0-flash` with circuit breaker fallback to `gemini-2.0-pro`).
* `apps/backend/src/chat/`
  * `router.py`: FastAPI endpoints `/api/v1/chat/stream`, `/api/v1/conversations`, `/api/v1/conversations/{id}/branch`.
  * `sse.py`: Async generator transforming ADK event streams into compliant SSE chunks over Cloud Run HTTP/2.
* `supabase/migrations/20260927000002_adk_sessions.sql`:
  * Core ADK session and event tables in Supabase Postgres (`sessions`, `events`, `app_states`, `user_states`).
  * `public.conversations` summary table for quick UI listing with RLS policies.
* `apps/web/src/components/assistant-ui/`: Styled elements catalog (`thread`, `thread-list`, `markdown-text`, `reasoning`, `sources`, `attachment`, `action-bar`).
* `apps/web/src/components/chat/adk-chat-container.tsx`: Root client chat interface mounting `AssistantRuntimeProvider` with `useAdkRuntime` (`@assistant-ui/react-google-adk`).
* `apps/web/src/app/chat/page.tsx`: Streaming chat page embedding the assistant-ui `Thread` and `ThreadListSidebar`.
* `apps/mobile/src/screens/ChatScreen.tsx`: Mobile equivalent utilizing `@assistant-ui/react-native`.

---

## 4. Requirements & Implementation Details

### R02.1: In-Process ADK 2.0 Runner & Agentgateway LLM Proxy (ADK + Agentgateway + GCP)
- The ADK Runner executes as an in-process singleton within FastAPI on Cloud Run, eliminating cross-service HTTP proxy latency and serialization overhead.
- Sessions and events persist into Supabase PostgreSQL using ADK's `DatabaseSessionService` via SQLAlchemy and asyncpg with connection pooling (`pool_size=20`, `max_overflow=10`).
- **Resilient LLM Routing via Agentgateway**:
  - ADK client connects to loopback `http://127.0.0.1:8080/v1`.
  - **Primary Route**: Google Vertex AI `gemini-2.0-flash` in `asia-south1`.
  - **Automated Fallback**: Agentgateway catches 429 (rate-limit) or 503 errors and transparently retries against `gemini-2.0-pro` without dropping the user's streaming connection.

### R02.2: Cloud Run Native HTTP/2 SSE Streaming with `@assistant-ui/react-google-adk` (GCP + assistant-ui + ADK)
- Endpoint: `POST /api/v1/chat/stream`
  - Consumed directly on the frontend by `@assistant-ui/react-google-adk` via `createAdkStream({ api: '/api/v1/chat/stream' })`.
  - The `@assistant-ui/react-google-adk` client automatically normalizes snake_case event fields from ADK Python (`function_call` to `functionCall`, `part` deltas) into framework-native message state.
  - Streams tokens over Cloud Run HTTP/2 with initial `: ping\n\n` keep-alive comments to prevent Google Cloud Load Balancing timeout drops.
  - Gemini 2.0 Flash reasoning and thinking blocks render seamlessly using the assistant-ui `Reasoning` element.
  - Code blocks render syntax-highlighted markdown via `@assistant-ui/react-markdown` with Shiki.

### R02.3: ChatGPT-Style Branching via `BranchPickerPrimitive` (assistant-ui + ADK + Supabase)
- Message editing and regeneration are powered natively by assistant-ui's `BranchPickerPrimitive` (`< 1/2 >`).
- Configured through `useAdkRuntime({ getCheckpointId: async (threadId, parentMessages) => lastParentId })`.
- When an earlier user message is edited or regenerated:
  - The client submits the edit referencing the parent event checkpoint.
  - The ADK Runner creates a new child Event branching from that parent in the Supabase PostgreSQL event tree.
  - The `BranchPickerPrimitive` allows users to toggle between branches without losing alternate conversation paths.

### R02.4: Multi-Thread Conversation Management via `createAdkSessionAdapter` (Supabase + assistant-ui)
- Conversation threads are persisted and managed through `createAdkSessionAdapter` wired to Supabase's `public.conversations` table.
- The `ThreadListSidebar` displays categorized conversations (Today, Previous 7 Days, Older) with rename, archive, and delete primitives.

### R02.5: Mandatory In-App AI Moderation & Flagging (Apple Guideline 1.2 Compliance)
- Integrated directly into the `ActionBarPrimitive` attached to every assistant response:
  - Action buttons: Copy (`CopyPrimitive`), Regenerate (`ReloadPrimitive`), and **Flag / Report** (`FlagPrimitive`).
  - Clicking Flag opens an instant modal:
    - Reason: Inaccurate, Offensive, Sensitive PII Leak, Copyright, Other.
    - User comments input.
    - Submit logs an immediate incident report to `public.ai_content_reports` in Supabase and triggers an alert via Google Cloud Logging.
  - Guarantees 100% compliance with Apple App Store Guideline 1.2 and Google Play AI Safety requirements.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-02.1** | Authenticated user streams a response token-by-token over SSE via Cloud Run | `pnpm --filter web test:e2e tests/e2e/chat-stream.spec.ts` | [ ] |
| **VAL-02.2** | First token delivered in <800ms TTFT under Cloud Run | `pytest apps/backend/tests/test_chat_sse_latency.py` | [ ] |
| **VAL-02.3** | Killing and restarting backend container preserves conversation history in Supabase | `pytest apps/backend/tests/test_session_durability.py` | [ ] |
| **VAL-02.4** | Editing a message creates a new branch without overwriting prior history in Postgres | `pytest apps/backend/tests/test_event_branching.py` | [ ] |
| **VAL-02.5** | User from Org A cannot read conversations belonging to Org B (Supabase RLS) | `pytest apps/backend/tests/test_conversation_tenant_isolation.py` | [ ] |
| **VAL-02.6** | Agentgateway successfully fails over from primary to secondary LLM on simulated 429 | `pytest apps/backend/tests/test_llm_gateway_failover.py` | [ ] |
| **VAL-02.7** | Clicking "Flag AI Content" opens modal and records incident in Supabase (Apple 1.2) | `pnpm --filter web test:e2e tests/e2e/ai-flagging.spec.ts` | [ ] |
