# Spec 06: Tri-Layer Memory via Vertex AI Embeddings & pgvector (The 5-Framework Architecture)

## 1. Context & Motivation
An enterprise assistant that forgets everything between sessions creates a severe productivity drag. However, auto-injecting open-ended memory leads to hallucination, prompt bloat, and privacy violations. Furthermore, India's **DPDP Act 2023** and **Apple App Store Guideline 5.1.1** mandate complete user transparency, editable memory, and instant in-app memory purging.

Workkbot implements a **custom `BaseMemoryService` combining Google Vertex AI Embeddings (`text-embedding-004`) with Supabase Vector (`pgvector` in Mumbai)**, routing all memory decisions through the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Relational episodic session storage, Supabase Vector (`pgvector` `^0.8.0` with HNSW cosine distance indexing), and strict user/tenant RLS.
2. **Google Cloud Platform (GCP `asia-south1`)**: Google Vertex AI `text-embedding-004` generating 768-dimensional embeddings in Mumbai, and Cloud Run background workers.
3. **Google ADK 2.0 (`google-adk`)**: Custom `BaseMemoryService` implementation, `after_agent` asynchronous fact extraction, and `before_model` bounded similarity injection (<400 tokens).
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: In-chat prompt suggestions ("What does AI remember about me?"), and an interactive memory transparency and deletion drawer (`unstable_useInteractable`).
5. **Agentgateway 1.5.x**: Proxies background fact extraction prompts to Vertex AI Gemini Flash, filtering any extracted memories against prompt injection and cross-session poisoning.

### **The North Star: Security & Mobile App Approval**
- **Security**: Complete tenant and user isolation via Supabase RLS (`auth.uid()` and `auth.jwt() ->> 'org_id'`); extracted facts filtered by Agentgateway to prevent persistent prompt injection poisoning.
- **Mobile App Approval (Apple Guideline 5.1.1 & DPDP Sec 12)**: The user can view every fact the AI has recorded and purge individual items or all memory instantly in-app on web and mobile.

---

## 2. The 5-Framework Architecture Mapping for Spec 06

| Framework | Core Responsibility in Tri-Layer Memory | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | `public.memory_items` with `embedding vector(768)`; HNSW index; `match_user_memories()` RPC with RLS. | Strict user isolation: memory cannot be queried across users or orgs; supports atomic cascade deletion (Apple 5.1.1). |
| **2. Google Cloud Platform (GCP)** | Vertex AI `text-embedding-004` API in `asia-south1`; Cloud Run background worker thread for extraction. | All vector generation occurs within the Indian data region (`asia-south1`), fulfilling DPDP localization mandates. |
| **3. Google ADK 2.0** | Subclasses `BaseMemoryService`; `after_agent` async extraction hook; `before_model` bounded injection hook. | Strict token cap (maximum 400 tokens) prevents prompt stuffing and model distraction. |
| **4. assistant-ui** | Memory transparency panel (`unstable_useInteractable`); prompt suggestion pill; one-tap fact deletion. | Responsive on web and `@assistant-ui/react-native`; satisfies Apple App Store Guideline 5.1.1 in-app memory erasure. |
| **5. Agentgateway 1.5.x** | LLM proxy handling memory extraction requests; sanitizes extracted tuples against prompt injection. | Prevents indirect prompt injection from being permanently enshrined in user semantic memory. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/memory/`
  * `supabase_memory.py`: Implements Google ADK's `BaseMemoryService` interface backed by Supabase Vector.
  * `vertex_embeddings.py`: Google Cloud Vertex AI client generating 768-dimensional embeddings via `text-embedding-004` in `asia-south1`.
  * `extractor.py`: Asynchronously extracts semantic `(subject, predicate, object, confidence)` tuples from conversation turns.
  * `callbacks/`
    * `memory_write.py`: `after_agent` callback dispatching async background extraction jobs.
    * `memory_inject.py`: `before_model` callback performing similarity search and bounded context injection.
* `supabase/migrations/20260927000006_supabase_vector.sql`:
  * `public.memory_items` table with vector column (`embedding vector(768)`).
  * HNSW cosine distance index (`CREATE INDEX ON memory_items USING hnsw (embedding vector_cosine_ops)`).
  * Stored procedure `match_user_memories(query_embedding vector, match_threshold float, match_count int)`.
  * RLS policies enforcing tenant and user isolation.
* `apps/web/src/app/settings/memory/page.tsx`: "What Does Workkbot Remember About Me?" management UI.
* `apps/mobile/src/screens/MemoryScreen.tsx`: Mobile memory transparency drawer.

---

## 4. Requirements & Implementation Details

### R06.1: The Tri-Layer Memory Architecture
| Memory Layer | Storage Mechanism | Retrieval Path | Purpose |
|---|---|---|---|
| **Episodic** | ADK Session & Event Log in Supabase Postgres | Replayed by ADK Runner per session | Conversation context, previous questions, message edits |
| **Semantic** | **Vertex AI `text-embedding-004` + Supabase Vector** with HNSW index | Cosine similarity match in `before_model` | Durable facts: user department, preferred formats, client names |
| **Procedural** | Versioned markdown files under `skills/` | Keyword & task routing in `before_model` | Company workflows: PR review steps, invoice drafting rules |

### R06.2: Asynchronous Extraction & Bounded Vector Injection (ADK + GCP + Supabase)
1. **Extraction (Write Path)**:
   - When an assistant turn completes, `after_agent` invokes `extractor.py` asynchronously.
   - Extracts structured facts (e.g. `("User", "prefers", "summaries in bullet points", confidence=0.92)`).
   - Passes text to Vertex AI `text-embedding-004` on GCP (`asia-south1`) to generate a 768-dim vector.
   - Writes record to `public.memory_items` in Supabase with user and org IDs.
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

### R06.3: User Transparency & Self-Service Deletion Panel (assistant-ui + Supabase)
- The web and mobile apps expose a dedicated **Memory Management** panel:
  - Fetches the user's active memories from `public.memory_items` via Supabase client.
  - Lists all remembered items with date learned and confidence score.
  - Users can click **[Delete]** on any item or click **[Purge All Memory]** to execute an instant Supabase delete query.
  - Guarantees full compliance with DPDP Section 12 (Right to Correction and Erasure) and Apple App Store Guideline 5.1.1.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-06.1** | Fact learned in Session 1 is retrieved via Supabase Vector search in Session 2 | `pytest apps/backend/tests/test_memory_recall.py` | [ ] |
| **VAL-06.2** | Memory embedding search executes in <40ms via HNSW index in Supabase | `pytest apps/backend/tests/test_memory_hnsw_speed.py` | [ ] |
| **VAL-06.3** | Supabase RLS guarantees User from Org A cannot retrieve memory items of Org B | `pytest apps/backend/tests/test_memory_tenant_isolation.py` | [ ] |
| **VAL-06.4** | Deleting a fact from the UI permanently drops row and HNSW vector index entry (Apple 5.1.1) | `pytest apps/backend/tests/test_memory_deletion.py` | [ ] |
| **VAL-06.5** | Asynchronous extraction does not add latency to the primary chat SSE stream | `pytest apps/backend/tests/test_memory_async_latency.py` | [ ] |
