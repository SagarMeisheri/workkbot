# Spec 05: Dynamic MCP OAuth Hub & In-App Notification Center via FCM (GCP Day 1)

## 1. Context & Motivation
Hardcoded provider connectors (e.g. custom Slack, Zoho, or Google tool wrappers) are brittle and unmaintainable. 
Furthermore, allowing dynamic user/admin connections to external endpoints introduces severe **Server-Side Request Forgery (SSRF)** risks (as witnessed in Open WebUI and LibreChat CVE-2026-31943, where attackers accessed cloud metadata `169.254.169.254` via IPv4-mapped IPv6 or DNS rebinding).
This spec establishes on **Google Cloud (`asia-south1`)**:
1. **The Dynamic MCP OAuth & OpenAPI Hub**: A user-facing connection center where employees connect to standard MCP providers via OAuth and import OpenAPI/Swagger specs for Indian SMB APIs (Tally, Zoho Books, internal ERPs) dynamically virtualized by **Agentgateway 1.5.x**.
2. **Deep SSRF & DNS-Rebind Immunity**: Strict IP validation rejecting loopback, link-local, cloud metadata, RFC1918 addresses, and IPv4-mapped IPv6 encodings before any outbound connection is established.
3. **The In-App Notification Center**: A centralized notification drawer powered by **Supabase Realtime (`postgres_changes`)** and **Firebase Cloud Messaging (FCM)** on Google Cloud.

## 2. Objective & Non-Goals
- **Objective**: Employees manage their own connected MCP tools via one-click OAuth; admins import validated OpenAPI specs virtualized into MCP tools by Agentgateway; outbound connections pass strict anti-SSRF scrutiny; pending tool approvals and background task completions are surfaced through a unified in-app notification drawer synced via Supabase Realtime and FCM push alerts.
- **Non-Goals**: No unverified URL fetches. No hardcoded tool APIs. No third-party chat messaging bots (no WhatsApp/Telegram). The Workkbot app is the exclusive workspace.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/mcp/hub/`
  * `provider_catalog.py`: Defines registered MCP server endpoints and their OAuth 2.0 client configurations.
  * `oauth_flow.py`: Manages the authorization code exchange and encrypted persistence in Supabase Vault.
  * `ssrf_validator.py`: Deep IP and DNS resolver checking resolved IPs against forbidden CIDRs and IPv4-mapped IPv6 encodings (CVE-2026-31943).
  * `openapi_importer.py`: Validates and registers SMB OpenAPI 3.0/Swagger specs into Agentgateway's dynamic route table.
  * `schema_cache.py`: Caches dynamically fetched `tools/list` JSON schemas in Supabase Postgres (`discovered_tools`) with automatic invalidation.
* `apps/backend/src/notifications/`
  * `fcm_service.py`: Google Cloud Firebase Cloud Messaging client dispatching background push alerts to Expo mobile clients.
* `supabase/migrations/20260927000005_notifications.sql`:
  * `public.user_notifications` table with Supabase Realtime replication enabled (`ALTER PUBLICATION supabase_realtime ADD TABLE public.user_notifications`).
  * RLS policies ensuring users only receive their own notifications.
* `apps/web/src/app/settings/connections/`: User MCP Connection Hub UI (OAuth and OpenAPI importers).
* `apps/web/src/components/chat/generative-ui-registry.tsx`: SMB Generative UI registry using `@assistant-ui/react-generative-ui` for Tally and Zoho Books responses.
* `apps/web/src/components/assistant-ui/elements/mcp-config.tsx`: Assistant-ui MCP server status and management element.
* `apps/web/src/components/notifications/notification-drawer.tsx`: Slide-out notification drawer listening to Supabase Realtime channel.

---

## 4. Requirements & Implementation Details

### R05.1: The Extensible Connectors Hub with Supabase Vault
- Accessible directly from assistant-ui's composer `+ -> Connectors >` or the sidebar `Settings -> Connectors`:
  - **Tabs**:
    - `Yours`: Displays active employee connections with live health status, authorized scopes, and disconnect actions.
    - `Discover`: Directory of 3,000+ ecosystem and verified MCP connectors with author attribution (`by Google`, `by Notion`, `by Slack`, `by Atlassian`, `by Canva`, `by HubSpot`, `by Asana`, `by Linear`, `by Anthropic`).
  - **Header Controls**:
    - Search input (`🔍 Search connectors`) with debounced querying.
    - Filter pills by capability: Top connectors, Productivity, CRM, Finance, Engineering, Design.
    - **`+ Add ▾` Button**: Modal action allowing admins and users to register a custom MCP server (via SSE/stdio container endpoint) or import an OpenAPI 3.0 specification.
- **Connection Flow**:
  1. The user clicks **[+]** on their chosen connector card in `Discover`.
  2. Completes standard OAuth 2.0 authorization code flow in their browser.
  3. The Cloud Run callback exchanges the code, writes the encrypted credentials to **Supabase Vault (`pgsodium`)** as `mcp_token_${user_id}_${provider_id}`, and updates `public.mcp_connections`.
  4. Discovered tools from the new MCP server are fetched via `tools/list`, cached in `public.discovered_tools`, and registered in the active ADK session through Agentgateway.

### R05.2: OpenAPI-to-MCP Virtualization via Agentgateway
- Admins can connect internal Indian business REST APIs (e.g. Zoho Books, Tally ERP, internal logistics) by importing their OpenAPI 3.0/Swagger JSON.
- `openapi_importer.py` validates schema structure and forwards it to Agentgateway's OpenAPI engine.
- Agentgateway dynamically exposes the REST endpoints as native MCP tools to the ADK `LlmAgent`, enforcing parameter sanitization (CVE-2026-29791) on path, query, and header parameters.

### R05.3: Strict Anti-SSRF, DNS Rebinding & IPv6 Guardrails
- `ssrf_validator.py` executes before registering any user-supplied OpenAPI URL or webhook:
  - Resolves domain to all underlying IP addresses immediately before socket connection.
  - Rejects private, loopback, multicast, or link-local ranges: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and `169.254.0.0/16`.
  - Normalizes IPv6 representations, explicitly rejecting **IPv4-mapped IPv6** notations (e.g., `::ffff:127.0.0.1` or `::ffff:169.254.169.254`) mitigating **CVE-2026-31943**.
  - Disables automatic HTTP 301/302 redirect following to prevent redirect-based SSRF probes.

### R05.4: In-App Notification Center via Supabase Realtime & FCM
- `public.user_notifications` table:
  - `id`, `org_id`, `user_id`, `type`, `title`, `body`, `action_url`, `read_at`, `created_at`.
- **Live Synchronization**:
  - Web and mobile apps subscribe to Supabase Realtime channel `user-notifications`.
- **Native Mobile Push via Google Firebase Cloud Messaging (FCM)**:
  - If the user's mobile app is backgrounded, `fcm_service.py` dispatches an FCM push alert. Tapping it routes directly to the in-app confirmation card via deep link (`workkbot://chat/:conversation_id?approval_id=:id`).

### R05.5: Generative UI Rendering for Virtualized SMB APIs
- Virtualized SMB tools (e.g. Tally GST calculator, Zoho Books invoice lookup) return structured UI payloads rendered by `@assistant-ui/react-generative-ui`.
- The assistant can call the `present({ display })` primitive or emit typed generative objects registered in `smbGenerativeUiLibrary`.
- Financial metrics, tax summaries, and customer ledgers render as interactive, beautifully formatted cards with actions (e.g., "Download PDF", "Re-compute ITC") rather than raw JSON or plain markdown tables.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-05.1** | User completes OAuth flow; available tools populate dynamically in Supabase DB | `pytest apps/backend/tests/test_mcp_oauth_flow.py` | [ ] |
| **VAL-05.2** | Disconnected account drops tokens from Supabase Vault and removes tools from session | `pytest apps/backend/tests/test_mcp_disconnect.py` | [ ] |
| **VAL-05.3** | Importing OpenAPI spec generates functional MCP tools via Agentgateway | `pytest apps/backend/tests/test_openapi_virtualization.py` | [ ] |
| **VAL-05.4** | SSRF validator blocks attempts to connect to `169.254.169.254` and `::ffff:127.0.0.1` | `pytest apps/backend/tests/test_ssrf_validator.py` | [ ] |
| **VAL-05.5** | Inserting row in `user_notifications` triggers Supabase Realtime event in web client | `pnpm --filter web test:e2e tests/e2e/notifications.spec.ts` | [ ] |
| **VAL-05.6** | Background mobile push alert dispatches cleanly via Firebase Cloud Messaging | `pytest apps/backend/tests/test_fcm_dispatch.py` | [ ] |
