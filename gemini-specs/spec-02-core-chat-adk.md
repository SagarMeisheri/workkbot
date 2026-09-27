# Spec 02: Core Chat on Google ADK 2.0 & Cloud Run Streaming (GCP Day 1)

## 1. Context & Motivation
With identity and statutory consent verified via Supabase Auth, this spec establishes the core conversational chat engine. 
The **Google ADK 2.0 Runner runs in-process inside the FastAPI backend deployed to Google Cloud Run in `asia-south1` (Mumbai)**, persisting conversation state into **Supabase PostgreSQL (Mumbai)** via ADK's `DatabaseSessionService`. The assistant starts with a single, unadorned `LlmAgent` routed through the local **Agentgateway 1.5.x LLM Proxy (`127.0.0.1:8080/v1`)** to **Google Vertex AI (`gemini-2.0-flash`)**. This provides sub-second time-to-first-token (TTFT), automatic upstream circuit breaking, token counting telemetry, and transparent secondary model failover during peak traffic.

## 2. Objective & Non-Goals
- **Objective**: Authenticated users stream responses token-by-token over Server-Sent Events (SSE) via Cloud Run over HTTP/2, edit previous messages to create conversation branches, and persist sessions durably in Supabase PostgreSQL via ADK’s `DatabaseSessionService` with Row-Level Security (RLS). LLM calls pass through the hardened Agentgateway proxy for resilience and telemetry.
- **Non-Goals**: No external MCP tools, memory injection, or code execution in this spec. Those attach to the ADK Runner in later specs.

---

## 3. Architecture & File Modifications

### Files to Create:
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
* `apps/web/src/components/assistant-ui/`: Styled elements catalog scaffolded via `npx assistant-ui@latest add thread thread-list markdown-text reasoning sources attachment`.
* `apps/web/src/components/chat/adk-chat-container.tsx`: Root client chat interface mounting `AssistantRuntimeProvider` with `useAdkRuntime` (`@assistant-ui/react-google-adk`).
* `apps/web/src/app/chat/page.tsx`: Streaming chat page embedding the assistant-ui `Thread` and `ThreadListSidebar`.

---

## 4. Requirements & Implementation Details

### R02.1: In-Process ADK 2.0 Runner & Agentgateway LLM Proxy
- The ADK Runner runs as an in-process singleton within FastAPI on Cloud Run, eliminating cross-service HTTP proxy latency and connection serialization overhead.
- Sessions and events persist into Supabase PostgreSQL using ADK's `DatabaseSessionService` via SQLAlchemy and asyncpg with connection pooling (`pool_size=20`, `max_overflow=10`).
- RLS Policies on `conversations`:
  ```sql
  CREATE POLICY "Users can only access conversations in their org" ON public.conversations
    FOR ALL USING (org_id = (auth.jwt() ->> 'org_id')::uuid AND user_id = auth.uid());
  ```
- **Resilient LLM Routing via Agentgateway**:
  - ADK client connects to loopback `http://127.0.0.1:8080/v1`.
  - **Primary Route**: Google Vertex AI `gemini-2.0-flash` in `asia-south1`.
  - **Automated Fallback**: Agentgateway catches 429 (rate-limit) or 503 errors and transparently retries against `gemini-2.0-pro` without dropping the user's streaming connection.

### R02.2: Cloud Run Native HTTP/2 SSE Streaming with `@assistant-ui/react-google-adk`
- Endpoint: `POST /api/v1/chat/stream`
  - Consumed directly on the frontend by `@assistant-ui/react-google-adk` via `createAdkStream({ api: '/api/v1/chat/stream' })`.
  - The `@assistant-ui/react-google-adk` client automatically normalizes snake_case event fields from ADK Python (`function_call` to `functionCall`, `part` deltas) into framework-native message state.
  - Streams tokens over Cloud Run HTTP/2 with initial `: ping\n\n` keep-alive comments to prevent Google Cloud Load Balancing timeout drops.
  - Gemini 2.0 Flash reasoning and thinking blocks render seamlessly using the assistant-ui `Reasoning` element.
  - Code blocks render syntax-highlighted markdown via `@assistant-ui/react-markdown` with Shiki.

### R02.3: ChatGPT-Style Branching via `BranchPickerPrimitive`
- Message editing and regeneration are powered natively by assistant-ui's `BranchPickerPrimitive` (`< 1/2 >`).
- Configured through `useAdkRuntime({ getCheckpointId: async (threadId, parentMessages) => lastParentId })`.
- When an earlier user message is edited or regenerated:
  - The client submits the edit referencing the parent event checkpoint.
  - The ADK Runner creates a new child Event branching from that parent in the Supabase PostgreSQL event tree.
  - The `BranchPickerPrimitive` allows users to toggle between branches without losing alternate conversation paths.

### R02.4: Multi-Thread Conversation Management via `createAdkSessionAdapter`
- Conversation threads are persisted and managed through `createAdkSessionAdapter` wired to Supabase's `public.conversations` table.
- The `ThreadListSidebar` displays categorized conversations (Today, Previous 7 Days, Older) with rename, archive, and delete primitives.

### R02.5: Canonical UI Layout Specification (Landing & Active States)
All frontend chat views converge strictly to the canonical assistant-ui visual design:
1. **Collapsible Left Sidebar (`ThreadListSidebar`)**:
   - Top: Workkbot brand logo, workspace name, and sidebar toggle icon `[|]`.
   - Prominent `+ New thread` rounded action button calling `aui.threads.switchToNew()`.
   - Chronological conversation threads with three-dot action menus (Rename, Archive, Delete).
   - Bottom Profile Footer: Displays `-> Sign in` when unauthenticated, or employee avatar, name, organization badge, and DPDP privacy portal link when authenticated.
2. **Top Navigation Header (`ThreadHeader`)**:
   - Left: Active thread title (e.g. `New chat`, or auto-titled from initial prompt).
   - Right: More options menu `...` and Canvas / Split-Screen toggle `↗` (for Spec 07 Artifacts).
3. **Empty Landing Experience**:
   - Prominent greeting: **"How can I help you today?"** (or personalized **"Back at it, [name]"**).
   - Centered floating composer input container:
     - `ComposerPrimitive.Input` with placeholder `"Type / for skills"` supporting slash commands (`/skill`, `/learn`, `/goal`).
     - Bottom-left: **`+` Action Button** opening the hierarchical dropdown menu:
       - `📎 Add files or photos` (`⌘U`) via `AttachmentPrimitive`
       - `📷 Take a screenshot`
       - `📁 Add to project >`
       - `────────`
       - `📑 Skills >` (Spec 08)
       - `🔲 Connectors >` (Google Workspace, Zoho Workplace MCP tools via Spec 01/04)
       - `🎨 Design system >` / `🧩 Add plugins` (Spec 05)
       - `────────`
       - `🌐 Web search` (`✓` toggle for Vertex AI Search Grounding)
     - Bottom-left (adjacent): **Mode Toggle Pill** `[ Chat | Canvas ]` (or `[ Chat | Cowork ]` for live collaborative artifact editing).
     - Bottom-right: **`ModelSelector` Pill** (e.g., `Gemini 2.0 Flash Medium ▾`), speech-to-text dictation microphone (`🎙️`), and voice waveform/orb (`|||| ▾`).
   - Suggestion Chips Cloud (`SuggestionPrimitive`): Centered staggered prompt pills for SMB productivity:
     - *"Calculate GST for March"*
     - *"Summarize Zoho unpaid invoices"*
     - *"Check stock ledger in Tally"*
     - *"What does AI remember about me?"*
4. **Active Thread Stream**:
   - Clean, centered message flow.
   - Gemini reasoning and thinking blocks render in an expandable `Reasoning` element.
   - Message edits and regeneration render the `< 1/2 >` branch navigator (`BranchPickerPrimitive`).
   - Bottom of each assistant bubble includes `ActionBarPrimitive` (Copy, Regenerate, and Apple App Store Guideline 1.2 "Report AI Content" Flag).

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-02.1** | Authenticated user streams a response token-by-token over SSE via Cloud Run | `pnpm --filter web test:e2e tests/e2e/chat-stream.spec.ts` | [ ] |
| **VAL-02.2** | First token delivered in <800ms TTFT under Cloud Run | `pytest apps/backend/tests/test_chat_sse_latency.py` | [ ] |
| **VAL-02.3** | Killing and restarting backend container preserves conversation history in Supabase | `pytest apps/backend/tests/test_session_durability.py` | [ ] |
| **VAL-02.4** | Editing a message creates a new branch without overwriting prior history in Postgres | `pytest apps/backend/tests/test_event_branching.py` | [ ] |
| **VAL-02.5** | User from Org A cannot read conversations belonging to Org B | `pytest apps/backend/tests/test_conversation_tenant_isolation.py` | [ ] |
| **VAL-02.6** | Agentgateway successfully fails over from primary to secondary LLM on simulated 429 | `pytest apps/backend/tests/test_llm_gateway_failover.py` | [ ] |
