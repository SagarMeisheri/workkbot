# Sovereign Enterprise AI Assistant: Techstack Invariants & Architecture Constraints

## 1. Monorepo Topology
The project is organized as a polyglot monorepo:
- **Root**: `pnpm` workspace managing cross-platform frontend, shared schemas, and deployment tooling.
- **Backend**: Python 3.12+ package managed via `pyproject.toml` (compatible with `uv` and standard `pip`), leveraging Google ADK 2.6+ (`google-adk>=2.6.2`).
- **Frontend**: Expo (React Native) project with Expo Router, `@assistant-ui/react-native`, and `expo-secure-store`.
- **Infra**: Dockerfiles, Cloud Build pipelines, Cloud Armor WAF configurations, and Cloud SQL migration manifests.
- **Shared**: Canonical JSON schemas and TypeScript types.

---

## 2. Pinned Technologies & Regional Locks

| Layer | Technology | Version / Specification | Sovereign Region Constraint |
| :--- | :--- | :--- | :--- |
| **Compute** | Google Cloud Run | Linux Container (Multi-stage Python 3.12-slim) | **`asia-south1` (Mumbai)** |
| **Edge Security & WAF** | Google Cloud Armor | OWASP Top 10, Rate Limiting, Geo-filtering via Serverless NEG | **`asia-south1` (Mumbai)** |
| **Agent Orchestration** | Google Agent Development Kit | ADK 2.6+ (`google-adk>=2.6.2`, `google-genai>=1.0.0`) | In-process execution in `asia-south1` |
| **Tool Protocol** | Model Context Protocol (MCP) | `google.adk.tools.mcp_tool.McpToolset` (`mcp>=1.0.0`) | Native client integration in backend |
| **Enterprise Integrations**| Google Workspace & Zoho MCP | Official Workspace MCP & Zoho MCP (`mcp.zoho.com`) | In-flight encrypted OAuth in Mumbai |
| **LLM Inference** | Google Vertex AI Gemini Flash | Gemini 2.0 Flash (`google-genai` SDK) | **`asia-south1-aiplatform.googleapis.com`** |
| **Data Protection & PII** | Sensitive Data Protection (DLP) | Indian infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_INDIVIDUAL`, etc.) | **`asia-south1` (Mumbai)** |
| **Database** | Google Cloud SQL for PostgreSQL | PostgreSQL 16+ (Private IP, Direct VPC Egress, `asyncpg`) | **`asia-south1` (Mumbai)** |
| **Vector Embeddings** | Cloud SQL `pgvector` | `vector(768)` (Vertex AI text-embedding-004) | Pinned inside sovereign Cloud SQL |
| **Encryption Keys** | Google Cloud KMS | Customer-Managed Encryption Keys (CMEK) | **`asia-south1` (Mumbai)** |
| **Token Vault** | Cloud SQL `pgcrypto` | AES-256 encrypted column storage (Cloud KMS CMEK) | Sovereign PostgreSQL storage |
| **Enterprise Identity** | Google Cloud Identity Platform | Passkeys (FIDO2), SAML 2.0 / OIDC, SMS OTP | Pinned with Indian Data Sovereignty |
| **Frontend Runtime** | Expo / React Native | Expo SDK 51+, React Native 0.74+ | Client device (iOS / Android / Web) |
| **Chat Interface** | `@assistant-ui/react-native` | Latest (following `with-expo` architecture) | Native client |
| **Device Security** | `expo-secure-store` | Hardware Keychain / KeyStore | Kept on-device |

---

## 3. Immutable Architectural Invariants

### 1. Sovereignty Lock & Zero Cross-Border Routing
- Every API call to Vertex AI must explicitly pass `api_endpoint="asia-south1-aiplatform.googleapis.com"` and `location="asia-south1"`.
- Cloud SQL instance connection string, private VPC IP, and Cloud KMS key rings must point strictly to India data centers (`asia-south1`).
- Any attempt to configure fallback endpoints to `us-central1`, `europe-west1`, or global multi-region clusters is a blocking violation.

### 2. Zero Data Retention (ZDR) & State Scoping
- Vertex AI Gemini Flash client must omit `SessionResumptionConfig` and disable any server-side prompt/context caching.
- Production environment configurations must reference a signed Google Cloud Data Processing Addendum (DPA) and Abuse Monitoring Opt-Out form to eliminate the 24-hour transient logging window.
- **State Scoping Invariant**: The in-flight PII pseudonymization map is stored strictly under `callback_context.state['temp:pii_map']`. ADK guarantees that `temp:`-scoped state keys are ephemeral and discarded upon invocation completion, preventing PII translation maps from touching persistent storage.

### 3. Unified Tool Execution via Model Context Protocol (MCP)
- External third-party integrations (Google Workspace, Zoho CRM, Zoho Desk, Zoho Mail) are executed exclusively through ADK's `McpToolset`.
- Custom one-off REST API clients for tool integrations are prohibited.
- All MCP tool outputs are intercepted by the `after_tool_callback` and sanitized within `<untrusted_content source="mcp:{server}:{tool}">` XML tags to neutralize indirect prompt injection.

### 4. Row-Level Security (RLS) & Tenant Isolation
- Every table holding personal data (`consent_logs`, `adk_sessions`, `adk_events`, `user_memories`, `workspace_tokens`, `audit_logs`) must have RLS enabled and forced unconditionally:
  ```sql
  ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;
  ALTER TABLE <table_name> FORCE ROW LEVEL SECURITY;
  CREATE POLICY "<table_name>_owner_isolation" ON <table_name>
    FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
  ```
  FastAPI sets the transaction-scoped variable `app.current_user_id` upon acquiring a connection via `SET LOCAL`.

### 5. Edge Shielding via Cloud Armor & Non-Root Containers
- Cloud Run containers execute as a non-privileged system user (`appuser` with UID/GID 10001) on port 8080.
- All public ingress passes through a Google Cloud Serverless Network Endpoint Group (NEG) secured with Cloud Armor WAF policies enforcing rate limiting, OWASP rules, and geo-filtering.
