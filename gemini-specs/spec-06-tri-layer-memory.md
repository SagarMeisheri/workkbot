# Spec 06: Tri-Layer Memory System via Supabase Vector & Transparency Panel

## 1. Context & Motivation
An enterprise assistant that forgets everything between sessions creates a severe productivity drag. However, auto-injecting open-ended memory leads to hallucination, prompt bloat, and privacy violations.
This spec implements a **custom `BaseMemoryService` on Supabase Vector (`pgvector`)**. It balances persistent recall with strict user transparency and self-deletion controls mandated by India's DPDP Act.

## 2. Objective & Non-Goals
- **Objective**: The assistant remembers durable user preferences and facts across sessions using Supabase Vector; memory writes execute asynchronously outside the hot path; users have an in-app panel to view, edit, or purge what the AI has remembered.
- **Non-Goals**: No cross-user or cross-org memory sharing. Facts are strictly partitioned by `org_id` and `user_id` using Supabase RLS.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/memory/`
  * `supabase_memory.py`: Implements Google ADK's `BaseMemoryService` interface backed by Supabase Vector.
  * `extractor.py`: Asynchronously extracts semantic `(subject, predicate, object, confidence)` tuples from conversation turns.
  * `callbacks/`
    * `memory_write.py`: `after_agent` callback dispatching async background extraction jobs.
    * `memory_inject.py`: `before_model` callback performing similarity search and bounded context injection.
* `supabase/migrations/20260927000006_supabase_vector.sql`:
  * `public.memory_items` table with vector column (`embedding vector(768)` or `vector(1536)`).
  * HNSW cosine distance index (`CREATE INDEX ON memory_items USING hnsw (embedding vector_cosine_ops)`).
  * Stored procedure `match_user_memories(query_embedding vector, match_threshold float, match_count int)`.
  * RLS policies enforcing tenant and user isolation.
* `apps/web/src/app/settings/memory/`: "What Does Workkbot Remember About Me?" management UI.

---

## 4. Requirements & Implementation Details

### R06.1: The Tri-Layer Memory Architecture on Supabase

| Memory Layer | Storage Mechanism | Retrieval Path | Purpose |
|---|---|---|---|
| **Episodic** | ADK Session & Event Log in Supabase Postgres | Replayed by ADK Runner per session | Conversation context, previous questions, message edits |
| **Semantic** | **Supabase Vector (`memory_items`)** with HNSW index | Cosine similarity match in `before_model` | Durable facts: user department, preferred formats, client names |
| **Procedural** | Versioned markdown files under `skills/` | Keyword & task routing in `before_model` | Company workflows: PR review steps, invoice drafting rules |

### R06.2: Asynchronous Extraction & Bounded Vector Injection
1. **Extraction (Write Path)**:
   - When an assistant turn completes, `after_agent` invokes `extractor.py` in the background.
   - Extracts structured facts: e.g. `("User", "prefers", "summaries in bullet points", confidence=0.92)`.
   - Embeds the content and writes to `public.memory_items` in Supabase Postgres.
   - Does **not** block or delay streaming the token response to the user.
2. **Injection (Read Path)**:
   - When a user submits a prompt, `memory_inject.py` calls the Supabase RPC function `match_user_memories`:
     ```sql
     CREATE OR REPLACE FUNCTION match_user_memories(
       query_embedding vector(768),
       match_threshold float,
       match_count int
     )
     RETURNS TABLE (id uuid, content text, confidence float, similarity float)
     LANGUAGE plpgsql AS $$
     BEGIN
       RETURN QUERY
       SELECT
         m.id, m.content, m.confidence,
         1 - (m.embedding <=> query_embedding) AS similarity
       FROM public.memory_items m
       WHERE m.org_id = (auth.jwt() ->> 'org_id')::uuid
         AND m.user_id = auth.uid()
         AND 1 - (m.embedding <=> query_embedding) > match_threshold
       ORDER BY m.embedding <=> query_embedding
       LIMIT match_count;
     END;
     $$;
     ```
   - Injects the top-K relevant facts into the system prompt, strictly bounded by a token budget (maximum 400 tokens).

### R06.3: User Transparency & Self-Service Deletion Panel
- The web and mobile apps expose a dedicated **Memory Management** panel:
  - Fetches the user's active memories from `public.memory_items` via Supabase client.
  - Lists all remembered items with date learned and confidence score.
  - Users can click **[Delete]** on any item to execute an instant Supabase delete query.
  - Satisfies DPDP Section 12 (Right to Correction and Erasure).

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-06.1** | Fact learned in Session 1 is retrieved via Supabase Vector search in Session 2 | Multi-session integration test | [ ] |
| **VAL-06.2** | Memory write executes in background without adding latency to chat stream | Latency benchmark comparison | [ ] |
| **VAL-06.3** | Supabase RLS guarantees User from Org A cannot retrieve memory items of Org B | Cross-tenant RLS query test | [ ] |
| **VAL-06.4** | Deleting a fact from the UI permanently drops row and HNSW vector index entry | Delete item via API; verify zero search hits | [ ] |
