# Spec 03: Memory Backend (Episodic, Semantic, Procedural)

## 1. Context & Motivation
Spec 01 wired in `InMemoryMemoryService` as an explicit placeholder. This spec replaces it with a durable, custom `BaseMemoryService` implementation backed by the same Postgres instance (via `pgvector`), avoiding both a new infrastructure dependency and GCP lock-in (ADK's managed `VertexAiMemoryBankService` is explicitly rejected per the constitution's provider-neutrality boundary).

## 2. Objective & Non-Goals
- **Objective**: The assistant remembers durable facts/preferences about a user across sessions, with the write path gated for review-worthiness and the retrieval path bounded and visible to the user.
- **Non-Goals**: No automated procedural-memory mining from transcripts — procedural memory stays authored content in `skills/` (see Spec 05). No cross-org memory sharing.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/agent-runtime/memory/postgres_memory_service.py` — implements ADK's `BaseMemoryService`: `add_session_to_memory` (write path) and retrieval methods backing `preload_memory`/`load_memory`.
* `apps/agent-runtime/callbacks/memory_write.py` — `after_agent` callback invoking `callback_context.add_session_to_memory()` asynchronously.
* `apps/agent-runtime/callbacks/memory_inject.py` — `before_model` callback performing a deterministic top-K vector search and injecting results, as an alternative/complement to model-initiated `preload_memory` tool use.
* `apps/web/app/memory/` — "what does it remember about me" panel: lists semantic facts with source and confidence, allows manual deletion.
* Database migration: `memory_items` table (`org_id`, `user_id`, `kind`, `content`, `embedding`, `confidence`, `source_message_id`, `created_at`), `pgvector` index.

### Files to Modify:
* `apps/agent-runtime/runner.py` — replace `InMemoryMemoryService` with `PostgresMemoryService`.
* `apps/agent-runtime/agent.py` — attach `preload_memory`/`load_memory` tool if using model-initiated retrieval.

### Files to Delete / Deprecate:
* Remove the `TODO(spec-03)` placeholder comment introduced in Spec 01.

---

## 4. Requirements & Implementation Details

### R03.1: `PostgresMemoryService` write path
- `add_session_to_memory` extracts candidate semantic facts from the session's events and writes them as `(subject, predicate, object, confidence, source_message_id)` rows plus an embedding.
- The write is triggered from an `after_agent` callback — asynchronous, outside the hot path, so a slow extraction step never adds latency to the user-visible response.
- Facts below a configurable confidence threshold are written as `pending_review` rather than immediately active, giving a human review gate before something sensitive said in passing becomes durable memory.

### R03.2: Retrieval and injection
- Retrieval is a `pgvector` similarity search scoped to `org_id` + `user_id` — never cross-user, never cross-org.
- The injected memory budget is capped (a few hundred tokens) and deterministic, not open-ended — bounded by a `TOP_K` and a token-budget constant, not "as much as fits."
- The set of facts actually injected on a given turn is recorded (which fact IDs, not just a token count) so the "what does it remember" panel and any later debugging can show exactly what was used.

### R03.3: Memory transparency and control panel
- `web` exposes a panel listing the user's own semantic facts, each with its source message and confidence, and an explicit delete action per fact.
- Deleting a fact removes both the row and its embedding — a deleted fact must not be retrievable, not merely hidden in the UI.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass / Fail |
|:---:|---|---|:---:|
| **VAL-01** | A fact learned in one session is retrievable and influences a response in a later session | Multi-session integration test | [ ] |
| **VAL-02** | Memory write happens asynchronously and does not add measurable latency to the streamed response | Latency benchmark with write callback enabled/disabled | [ ] |
| **VAL-03** | Retrieval never returns another user's or another org's facts | Pytest with two seeded users/orgs, cross-query assertion | [ ] |
| **VAL-04** | Deleting a fact via the panel removes it from future retrieval results | Integration test: delete then re-query | [ ] |
| **VAL-05** | Low-confidence extracted facts land in `pending_review`, not immediately active | Pytest against the extraction/write path | [ ] |
