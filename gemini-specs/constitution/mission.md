# Constitution: Mission & Non-Negotiable Boundaries

## 1. Project Vision
**Workkbot** is a secure, private, in-app AI assistant platform engineered specifically for organizations of under 100 employees, built on **Supabase** as the unified data, auth, vector, and storage backbone. It delivers conversational chat, dynamic tool discovery via the Model Context Protocol (MCP), generative Artifacts, and persistent memory across web and native mobile apps—combining statutory compliance with India's **DPDP Act 2023** and **guaranteed mobile App Store approval**.

## 2. Target Audience & Personas
- **Primary Persona (The Employee)**: Works exclusively inside the Workkbot web and mobile apps. Connects external accounts (Google, GitHub, Slack, Notion, CRM) via one-click OAuth, interacts with dynamically discovered tools, and authorizes personal write actions via in-chat interactive cards.
- **Secondary Persona (Org Admin / IT Lead)**: Manages IdP-federated user roles, enables allowed MCP providers, monitors token consumption in Indian Rupees (INR), and accesses compliance audit logs and DPDP Data Subject Request (DSR) tools.

## 3. Product Scope & Core Capabilities
- **In-App Focused Workspace**: All interactions, alerts, and workflows occur strictly inside the Workkbot web and mobile apps.
- **Dynamic MCP Tool Discovery**: No hardcoded or fixed tool connectors. Workkbot manages MCP server endpoints; users simply authorize their accounts via OAuth. Available tools are discovered dynamically via the standard MCP `tools/list` protocol.
- **100% User-Centric In-App HITL**: Any tool operation classified by the backend as mutating/write-capable is presented to the **individual user directly in their chat stream** as an interactive approval card. In-app notification drawers and push notifications alert users when away from the thread. No IT admin approval bottlenecks.
- **Tri-Layer Memory System**: Episodic (ADK session/event log in Supabase Postgres), Semantic (Supabase Vector with `pgvector`), and Procedural (authored in `skills/`), paired with a self-service transparency and deletion panel.
- **Generative Artifacts**: Short-lived sandboxed code execution (E2B microVMs or local Docker runner) backed by Supabase Storage and rendered inside origin-isolated iframes and WebViews.
- **Mobile App Store Readiness**: Built-in pre-compliance for Apple App Store (Guidelines 1.2, 2.1, 3.2.2, 4.0, 5.1.1) and Google Play AI policies.

## 4. Non-Negotiable Boundaries & Constraints
- **Boundary 1 (In-App Focus & Privacy)**: All approvals and alerts live inside the Workkbot application and native push notifications. Third-party messaging integrations (e.g. WhatsApp, Telegram) are explicitly out of scope for v1.
- **Boundary 2 (Dynamic Tools via Standard MCP)**: No custom, proprietary, or hardcoded tool APIs. External capabilities must connect strictly via standard Model Context Protocol (MCP) servers with dynamic discovery.
- **Boundary 3 (DPDP Act 2023 Compliance by Design)**: Statutory bilingual notice and consent upon initial login. Real-time Indian PII masking (Aadhaar, PAN, UPI) prior to model dispatch. Automated Right to Erasure (DSR) pipeline cascading through Supabase Auth, database tables, and vector embeddings.
- **Boundary 4 (Sized for <100 Seats on Supabase)**: Single-backend architecture (Python 3.12 FastAPI hosting the ADK 2.0 Runner directly) backed by the unified Supabase platform (PostgreSQL, Auth, Vault, Vector, Realtime, Storage). No premature microservices, Kafka, standalone Redis clusters, or separate vector databases.
- **Out of Scope (v1)**: Multi-tenant public hosting; third-party chat app bots (WhatsApp/Slack bots); consumer self-registration without company domain verification; fine-tuning custom models on premise.
