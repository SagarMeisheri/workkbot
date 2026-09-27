# Constitution: Mission & Non-Negotiable Boundaries

## 1. Project Vision
**Workkbot** is a secure, private, in-app AI assistant platform engineered specifically for organizations of under 100 employees, built and deployed on **Google Cloud Platform (asia-south1 / Mumbai)** from Day 1 with **Supabase (Mumbai)** as the unified data, auth, vector, and storage backbone. It delivers conversational chat via Google ADK 2.0 and Vertex AI, dynamic tool discovery via the Model Context Protocol (MCP), generative Artifacts backed by Google Cloud Storage, and persistent memory across web and native mobile apps—combining statutory compliance with India's **DPDP Act 2023** and **guaranteed mobile App Store approval**.

## 2. Target Audience & Personas
- **Primary Persona (The Employee)**: Works exclusively inside the Workkbot web and mobile apps. Connects external accounts (Google Workspace, Zoho Workplace) via one-click in-chat OAuth, interacts with dynamically discovered tools, and authorizes personal write actions via in-chat interactive cards.
- **Secondary Persona (Org Admin / IT Lead)**: Manages IdP-federated user roles, enables allowed MCP providers, monitors token consumption in Indian Rupees (INR), and accesses compliance audit logs and DPDP Data Subject Request (DSR) tools.

## 3. Product Scope & Core Capabilities
- **Day-1 Google Cloud Serverless & Agentic Deployment**: The unified FastAPI backend (hosting the Google ADK 2.0 Runner) and **Agentgateway 1.5.x** (Rust proxy) deploy as a multi-container pod on **Google Cloud Run** in `asia-south1` (Mumbai), alongside the Next.js 15 web app, with zero-cold-start and native HTTP/2 SSE streaming.
- **In-App Focused Workspace**: All interactions, alerts, and workflows occur strictly inside the Workkbot web and mobile apps.
- **Dynamic MCP Tool Discovery & Federation**: No hardcoded or fixed tool connectors. Agentgateway federates MCP server endpoints; users simply authorize their accounts via OAuth. Available tools are discovered dynamically via `tools/list` with automated tool poisoning and shadowing defense.
- **100% User-Centric In-App HITL**: Any tool operation classified by the backend as mutating/write-capable is presented to the **individual user directly in their chat stream** as an interactive approval card. In-app notification drawers and push notifications alert users when away from the thread. No IT admin approval bottlenecks.
- **Tri-Layer Memory System**: Episodic (ADK session/event log in Supabase Postgres), Semantic (Supabase Vector with `pgvector` HNSW index and Vertex AI `text-embedding-004`), and Procedural (authored in `skills/`), paired with a self-service transparency and deletion panel.
- **Generative Artifacts**: Short-lived sandboxed code execution (E2B microVMs or local Docker runner) backed by Google Cloud Storage (GCS) and rendered inside origin-isolated subdomains with strict CSP and path traversal sanitization.
- **Mobile App Store Readiness**: Built-in pre-compliance for Apple App Store (Guidelines 1.2, 2.1, 3.2.2, 4.0, 5.1.1) and Google Play AI policies.

## 4. Non-Negotiable Boundaries & Constraints
- **Boundary 1 (Day-1 GCP Deployment in Mumbai)**: All backend workloads and data storage reside within Google Cloud's Mumbai region (`asia-south1`) to satisfy the Indian DPDP Act 2023 data localization principles. Cloud Build, Artifact Registry, Cloud Run, and Cloud Armor are deployed from Day 1.
- **Boundary 2 (In-App Focus & Privacy)**: All approvals and alerts live inside the Workkbot application and native push notifications. Third-party messaging integrations (e.g. WhatsApp, Telegram) are explicitly out of scope for v1.
- **Boundary 3 (Dynamic Tools via Standard MCP & Agentgateway)**: No custom, proprietary, or hardcoded tool APIs. External capabilities must connect strictly via standard Model Context Protocol (MCP) servers federated through Agentgateway with dynamic discovery and anti-poisoning filters.
- **Boundary 4 (DPDP Act 2023 Compliance & SSRF Immunity)**: Statutory bilingual notice and consent upon initial login. Real-time Indian PII masking (Aadhaar, PAN, UPI) via Google Cloud DLP prior to model dispatch. Automated Right to Erasure (DSR) pipeline cascading through Supabase Auth, database tables, and vector embeddings. Cloud Run VPC egress firewall blocks access to `169.254.169.254`.
- **Boundary 5 (Sized for <100 Seats on Lean Stack)**: Multi-container Cloud Run architecture: Python 3.12 FastAPI (hosting the ADK 2.0 Runner) paired with Agentgateway 1.5.x (Rust data plane on loopback `127.0.0.1:8080`), backed by the unified Supabase platform (PostgreSQL, Auth, Vault, Vector, Realtime) in Mumbai. No premature microservices, Kafka, standalone Redis clusters, or separate vector databases.
- **Out of Scope (v1)**: Multi-tenant public hosting; third-party chat app bots (WhatsApp/Slack bots); consumer self-registration without company domain verification; fine-tuning custom models on premise.
