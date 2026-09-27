# Spec 02: Core Chat on Google ADK 2.0 & Cloud Run Streaming (GCP Day 1)

## 1. Context & Motivation
With identity and statutory consent verified via Supabase Auth, this spec establishes the core conversational chat engine. 
The **Google ADK 2.0 Runner runs in-process inside the FastAPI backend deployed to Google Cloud Run in `asia-south1` (Mumbai)**, persisting conversation state into **Supabase PostgreSQL (Mumbai)** via ADK's `DatabaseSessionService`. The assistant starts with a single, unadorned `LlmAgent` powered directly by **Google Vertex AI (`gemini-2.0-flash`)**, saving tokens and latency by avoiding premature multi-agent complexity.

## 2. Objective & Non-Goals
- **Objective**: Authenticated users can stream responses token-by-token over Server-Sent Events (SSE) via Cloud Run over HTTP/2, edit previous messages to create conversation branches, and persist sessions durably in Supabase PostgreSQL via ADK’s `DatabaseSessionService` with Row-Level Security (RLS).
- **Non-Goals**: No external MCP tools, memory injection, or code execution in this spec. Those attach to the ADK Runner in later specs.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/agent/`
  * `agent.py`: Instantiates the primary Google ADK 2.0 `LlmAgent(name="workkbot_core")` configured with Vertex AI Gemini 2.0 Flash.
  * `runner.py`: Sets up ADK `Runner` configured with `DatabaseSessionService` pointed at Supabase PostgreSQL (via SQLAlchemy/asyncpg).
  * `model_tier.py`: Multi-provider model router defaulting to cost-effective models (Vertex AI `gemini-2.0-flash` or `gemini-2.0-pro`).
* `apps/backend/src/chat/`
  * `router.py`: FastAPI endpoints `/api/v1/chat/stream`, `/api/v1/conversations`, `/api/v1/conversations/{id}/branch`.
  * `sse.py`: Async generator transforming ADK event streams into compliant SSE chunks over Cloud Run HTTP/2.
* `supabase/migrations/20260927000002_adk_sessions.sql`:
  * Core ADK session and event tables in Supabase Postgres (`sessions`, `events`, `app_states`, `user_states`).
  * `public.conversations` summary table for quick UI listing with RLS policies.
* `apps/web/src/app/chat/`: Real-time streaming chat UI with message branching controls (edit/retry).

---

## 4. Requirements & Implementation Details

### R02.1: In-Process ADK 2.0 Runner on Google Cloud Run
- The ADK Runner runs as an in-process singleton within FastAPI on Cloud Run, eliminating cross-service HTTP proxy latency and connection serialization overhead.
- Sessions and events persist into Supabase PostgreSQL using ADK's `DatabaseSessionService` via SQLAlchemy and asyncpg with connection pooling (`pool_size=20`, `max_overflow=10`).
- RLS Policies on `conversations`:
  ```sql
  CREATE POLICY "Users can only access conversations in their org" ON public.conversations
    FOR ALL USING (org_id = (auth.jwt() ->> 'org_id')::uuid AND user_id = auth.uid());
  ```
- Model Provider: Pinned to **Google Vertex AI `gemini-2.0-flash`** by default for sub-second time-to-first-token (TTFT) and low token pricing.

### R02.2: Cloud Run Native HTTP/2 SSE Streaming
- Endpoint: `POST /api/v1/chat/stream`
  - Accepts `{ conversation_id: string, message: string, parent_event_id?: string }`.
  - Streams tokens as `data: {"type": "token", "content": "..."}\n\n`.
  - Emits completion events: `data: {"type": "done", "event_id": "...", "usage": {...}}\n\n`.
  - Emits keep-alive comments `: ping\n\n` every 15s to keep Google Cloud Load Balancing connections open.
  - Handles client disconnects cleanly by canceling in-flight LLM calls immediately to prevent token waste.

### R02.3: ChatGPT-Style Branching (Edit & Regenerate)
- If a user edits an earlier message, the client submits the edit referencing the `parent_event_id`.
- The ADK Runner creates a new child Event branching from that parent in the Supabase event tree.
- The web and mobile UIs render a branch navigator (`< 2/2 >`), allowing users to switch between alternative completion branches.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-02.1** | Authenticated user streams a response token-by-token over SSE via Cloud Run | `pnpm --filter web test:e2e tests/e2e/chat-stream.spec.ts` | [ ] |
| **VAL-02.2** | First token delivered in <800ms TTFT under Cloud Run | `pytest apps/backend/tests/test_chat_sse_latency.py` | [ ] |
| **VAL-02.3** | Killing and restarting backend container preserves conversation history in Supabase | `pytest apps/backend/tests/test_session_durability.py` | [ ] |
| **VAL-02.4** | Editing a message creates a new branch without overwriting prior history in Postgres | `pytest apps/backend/tests/test_event_branching.py` | [ ] |
| **VAL-02.5** | User from Org A cannot read conversations belonging to Org B | `pytest apps/backend/tests/test_conversation_tenant_isolation.py` | [ ] |
