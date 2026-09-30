# Spec 05: Dynamic Connectors Hub (Composio Platform), SMB OpenAPI Virtualizer & In-App Notification Center via FCM (The 5-Framework Model)

## 1. Context & Motivation
Handcoded provider connectors (e.g. custom Slack, Zoho, or Google tool wrappers) are brittle and expensive to maintain. Allowing dynamic user/admin connections to external endpoints also introduces severe **Server-Side Request Forgery (SSRF)** risks (e.g. CVE-2026-31943, where attackers accessed cloud metadata `169.254.169.254` via IPv4-mapped IPv6 or DNS rebinding).

Workkbot eliminates these vulnerabilities while maximizing integration agility by adopting the **Two-Tier Gateway Model** within the **5 Core Frameworks**:
1. **Composio Platform (v3.1 Managed Connectors & Auth Plane)**: Provides 1,000+ certified application toolkits (Google Workspace, Zoho Workplace, Notion, Slack, Jira, Linear, GitHub, etc.) with automated OAuth token refresh cycles and managed Connect Links, eliminating hand-rolled OAuth code exchanges.
2. **Agentgateway 1.5.x (In-Pod Infrastructure Data Plane)**: Dynamic OpenAPI-to-MCP virtualizer for proprietary Indian SMB ERPs (e.g. local Tally Prime / custom billing APIs), deep anti-SSRF IP/DNS validation (CVE-2026-31943), and CEL-based tenant isolation.
3. **Supabase (Mumbai `ap-south-1`)**: Hardware token encryption via Supabase Vault (`pgsodium`), `public.tool_connections` and `public.user_notifications` with Supabase Realtime pub/sub replication, and strict RLS.
4. **Google Cloud Platform (GCP `asia-south1`)**: Cloud Run multi-container pod, Firebase Cloud Messaging (FCM) on Google Cloud for mobile push alerts, and VPC egress firewall drops.
5. **Google ADK 2.0 (`google-adk`)**: Registers Composio session tools and virtualized SMB tools in active `LlmAgent` sessions and emits structured generative UI data payloads.
6. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-generative-ui`, `@assistant-ui/react-native`)**: Connectors Hub Modal (`[ Yours | Discover ]`), slide-out In-App Notification Drawer, and `@assistant-ui/react-generative-ui` (`present({ display })`) rendering rich financial ledgers and GST cards.

### **The North Star: Security & Mobile App Approval**
- **Security**: Complete immunity against SSRF and DNS rebinding; token storage sealed in Composio and Supabase Vault; parameter sanitization (CVE-2026-29791).
- **Mobile App Approval (Apple & Google Play)**: 
  - **Guideline 5.1.1 (Account & Data Deletion)**: Disconnecting a provider or deleting an account invokes `composio.client.connected_accounts.delete(nanoid, revoke_on_delete=True)` to revoke upstream provider tokens instantly.
  - **Guideline 2.1 (App Completeness)**: Native FCM push alerts bring users directly to in-chat confirmation cards via deep links (`workkbot://chat/:conversation_id?approval_id=:id`) without background processing restrictions; Generative UI renders natively inside `@assistant-ui/react-native`.

---

## 2. The 5-Framework Architecture Mapping for Spec 05

| Framework / Layer | Core Responsibility in Dynamic Hub & Alerts | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | Supabase Vault token encryption; `public.user_notifications` with Realtime pub/sub; `public.tool_connections` with RLS. | All notifications and credentials are tenant-isolated (`auth.jwt() ->> 'org_id'`); deletion cascades to Vault and Composio (Apple 5.1.1). |
| **2. Google Cloud Platform (GCP)** | Firebase Cloud Messaging (FCM) dispatch; Cloud Run backend; Direct VPC Egress blocking metadata SSRF. | Dispatches native APNs/FCM alerts without battery drain; drops all egress to `169.254.169.254`. |
| **3. Google ADK 2.0** | `McpToolset` dynamically ingests tools produced by Agentgateway and Composio sessions; emits structured business objects for generative UI. | Encapsulates tools safely within the agent context; supports interactive confirmation pause on virtualized actions. |
| **4. assistant-ui** | Connectors Hub Modal (`[ Yours | Discover ]`), Notification Drawer (`notification-drawer.tsx`), and `@assistant-ui/react-generative-ui`. | Generates responsive, interactive UI cards (Tally GST, invoices); supports native mobile touch interactions. |
| **5. Agentgateway 1.5.x** | OpenAPI-to-MCP virtualization for local SMB ERPs; deep anti-SSRF IP/DNS resolver; parameter sanitization; CEL authorization. | Blocks IPv4-mapped IPv6 (`::ffff:169.254.169.254`), private CIDRs, and parameter tampering (CVE-2026-31943). |
| **Tier 2: Composio Platform** | Managed Connect Links (`session.authorize(toolkit)`); dynamic toolkit catalog (`toolkits.list()`); upstream token revocation. | Zero manual token refresh boilerplate; instant upstream token revocation on disconnect (`revoke_on_delete=True`). |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/mcp/hub/`
  * `composio_hub.py`: Queries Composio v3.1 toolkits catalog (`toolkits.list()`), category endpoints, and generates managed Connect Links (`session.authorize(toolkit)`).
  * `ssrf_validator.py`: Deep IP and DNS resolver checking resolved IPs against forbidden CIDRs and IPv4-mapped IPv6 encodings (CVE-2026-31943) for custom user-supplied OpenAPI endpoints.
  * `openapi_importer.py`: Validates and registers proprietary Indian SMB OpenAPI 3.0/Swagger specs (Tally Prime, custom ERPs) into Agentgateway's dynamic route table.
  * `schema_cache.py`: Caches dynamically fetched tool definitions in Supabase Postgres (`public.discovered_tools`) with automatic invalidation.
* `apps/backend/src/notifications/`
  * `fcm_service.py`: Google Cloud Firebase Cloud Messaging client dispatching background push alerts to Expo mobile clients.
* `supabase/migrations/20260927000005_notifications.sql`:
  * `public.user_notifications` table with Supabase Realtime replication enabled (`ALTER PUBLICATION supabase_realtime ADD TABLE public.user_notifications`).
  * `public.tool_connections` table tracking Composio connection IDs, auth config IDs, and statuses.
  * RLS policies ensuring users only access their own connections and notifications.
* `apps/web/src/components/chat/connectors-hub-modal.tsx`: Comprehensive Connectors Hub Modal (`[ Yours | Discover ]`) querying Composio toolkits and launching Connect Links.
* `apps/web/src/components/chat/generative-ui-registry.tsx`: SMB Generative UI registry using `@assistant-ui/react-generative-ui` for Tally and Zoho Books responses.
* `apps/web/src/components/assistant-ui/elements/mcp-config.tsx`: Assistant-ui MCP server status and management element.
* `apps/web/src/components/notifications/notification-drawer.tsx`: Slide-out notification drawer listening to Supabase Realtime channel.
* `apps/mobile/src/services/notifications.ts`: Expo Notifications and FCM client listener with deep-linking handler.

---

## 4. Requirements & Implementation Details

### R05.1: The Extensible Connectors Hub with Composio Platform (assistant-ui + Composio)
- Accessible directly from assistant-ui's composer `+ -> Connectors >` or sidebar `Settings -> Connectors`:
  - **Tabs**:
    - `Yours`: Displays active employee connections fetched from `public.tool_connections` with live health status, authorized scopes, and disconnect actions.
    - `Discover`: Directory of ecosystem and verified MCP connectors dynamically populated from Composio API v3.1 (`composio.toolkits.list(managed_by="composio", sort_by="usage")`) with author attribution (`by Google`, `by Zoho`, `by Notion`, `by Slack`, `by Atlassian`, `by Canva`, `by HubSpot`, `by Linear`, `by Tally`).
  - **Header Controls**:
    - Search input (`🔍 Search connectors`) with debounced querying.
    - Filter pills by capability populated from `composio.toolkits.list_categories()`: Top connectors, Productivity, Accounting & Finance, CRM, Communication, Developer.
    - **`+ Add ▾` Button**: Action allowing admins to register proprietary internal SMB OpenAPI 3.0/Swagger specifications (e.g. on-premise Tally Prime).
- **Connection Flow**:
  1. The user clicks **[Connect]** on their chosen connector card in `Discover`.
  2. Frontend calls `POST /api/v1/mcp/connectors/initiate { "toolkit": "googleworkspace" }`.
  3. Backend calls `session.authorize(toolkit="googleworkspace")` (or `composio.connected_accounts.link(...)`) and returns a secure Connect Link.
  4. Web/mobile client opens the Connect Link in a focused popup/tab. User completes standard OAuth with the provider.
  5. Composio exchanges the authorization code, stores credentials in SOC-2 encrypted storage, and notifies Workkbot.
  6. Backend updates `public.tool_connections`, and Supabase Realtime updates the card badge to green "Connected".

### R05.2: OpenAPI-to-MCP Virtualization via Agentgateway for Proprietary Indian SMB APIs
- Admins can connect internal Indian business REST APIs (local Tally Prime ERP bridge, custom inventory) by uploading OpenAPI 3.0/Swagger JSON specs.
- `openapi_importer.py` validates schema structure and forwards it to Agentgateway's in-pod OpenAPI engine on loopback (`127.0.0.1:8080`).
- Agentgateway dynamically exposes the endpoints as native MCP tools to Google ADK 2.0, enforcing parameter sanitization (CVE-2026-29791) on path, query, and header parameters.

### R05.3: Strict Anti-SSRF, DNS Rebinding & IPv6 Guardrails (Agentgateway + GCP)
- `ssrf_validator.py` executes before registering any user-supplied OpenAPI URL or custom webhook:
  - Resolves domain to all underlying IP addresses immediately before socket connection.
  - Rejects private, loopback, multicast, or link-local ranges: `127.0.0.1/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and `169.254.0.0/16`.
  - Normalizes IPv6 representations, explicitly rejecting **IPv4-mapped IPv6** notations (e.g., `::ffff:127.0.0.1` or `::ffff:169.254.169.254`), completely inoculating against **CVE-2026-31943**.
  - Disables automatic HTTP 301/302 redirect following to prevent redirect-based SSRF probes.

### R05.4: In-App Notification Center via Supabase Realtime & FCM (Supabase + GCP + assistant-ui)
- `public.user_notifications` table:
  - `id`, `org_id`, `user_id`, `type`, `title`, `body`, `action_url`, `read_at`, `created_at`.
- **Live Synchronization**:
  - Web and mobile apps subscribe to Supabase Realtime channel `user-notifications`.
- **Native Mobile Push via Firebase Cloud Messaging (FCM)**:
  - If the user's mobile app is backgrounded, `fcm_service.py` dispatches an FCM push alert. Tapping it routes directly to the in-app confirmation card via deep link (`workkbot://chat/:conversation_id?approval_id=:id`).

### R05.5: Generative UI for Virtualized SMB APIs (assistant-ui + ADK)
- Virtualized SMB tools return structured UI payloads rendered by `@assistant-ui/react-generative-ui`.
- The assistant calls the `present({ display })` primitive or emits typed generative objects.
- Financial metrics, tax summaries, and customer ledgers render as interactive, beautifully formatted cards with actions (e.g., "Download PDF", "Re-compute ITC") rather than raw JSON or plain markdown tables.

### R05.6: Instant In-App Disconnection & Upstream Token Revocation (Apple Guideline 5.1.1 & DPDP Act 2023)
- When a user disconnects a connector in the `Yours` tab or triggers full account erasure (`DELETE /api/v1/account/delete`):
  1. Workkbot calls `composio.client.connected_accounts.delete(nanoid=connection_id, revoke_on_delete=True)`.
  2. The upstream OAuth provider instantly revokes the access and refresh token pair.
  3. Supabase deletes the record in `public.tool_connections` and purges any session credentials in Supabase Vault.

---

## 5. Validation Scorecard & Execution Target

### **Execution Target**: `Localhost (Zero-Mock)`
- **Environment**: Next.js 15 (`localhost:3000`), FastAPI (`localhost:8000`), Agentgateway (`127.0.0.1:8080`), and live Composio Platform client on developer machine.
- **Live Cloud Boundaries**:
  - Live Supabase Realtime (`postgres_changes` / Broadcast) in Mumbai (`ap-south-1`) sending live toast notifications to browser.
  - Live Firebase Cloud Messaging (FCM) admin SDK dispatching push notifications.
  - Live Composio Platform SDK fetching verified toolkits and generating Connect Links.
  - Real Agentgateway OpenAPI virtualization compiler with anti-SSRF filters.

---

### **Tier 1: Unit & Contract Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-05.1** | Anti-SSRF validator strictly blocks `169.254.169.254`, `::ffff:127.0.0.1`, and private RFC 1918 subnets | `uv run pytest apps/backend/tests/test_ssrf_validator.py` | [ ] |
| **VAL-05.2** | OpenAPI parser converts Indian ERP specs (Zoho Books / Tally) into valid MCP tool declarations | `uv run pytest apps/backend/tests/test_openapi_virtualization.py` | [ ] |
| **VAL-05.3** | Disconnecting a provider revokes token via `revoke_on_delete=True` and drops record from Supabase | `uv run pytest apps/backend/tests/test_mcp_disconnect.py` | [ ] |

### **Tier 2: Zero-Mock Live Integration Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-05.4** | Composio Hub queries toolkits catalog and generates functional Connect Link | `uv run pytest apps/backend/tests/test_composio_hub_catalog.py` | [ ] |
| **VAL-05.5** | Inserting row into `public.user_notifications` broadcasts Realtime event to live WebSocket subscriber | `uv run pytest apps/backend/tests/test_realtime_broadcast.py` | [ ] |
| **VAL-05.6** | Background notification alert dispatches through live Firebase Cloud Messaging (FCM) client | `uv run pytest -m live_fcm apps/backend/tests/test_fcm_dispatch.py` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-05.7** | Connectors Hub Modal `+ Add ▾ -> OpenAPI Spec` opens drawer and imports custom API endpoint | `pnpm --filter @workkbot/web test:e2e tests/e2e/openapi-import.spec.ts` | [ ] |
| **VAL-05.8** | Generative UI renders interactive GST invoice preview card via `@assistant-ui/react-generative-ui` | `pnpm --filter @workkbot/web test:e2e tests/e2e/generative-ui.spec.ts` | [ ] |
| **VAL-05.9** | Supabase Realtime notification toast pops up on web client without page reload | `pnpm --filter @workkbot/web test:e2e tests/e2e/realtime-toasts.spec.ts` | [ ] |

### **Tier 4: Manual Verification Protocol**
1. **Dynamic Tool Import**: In `http://localhost:3000/chat`, open `+ -> Connectors >`. Click **`+ Add ▾`** and select **"OpenAPI Endpoint"**. Paste sample Petstore/Zoho test spec URL. Click "Register Tool". Confirm new tool appears in `Yours` tab with a green "Active" badge.
2. **Composio Connect Link**: In `Discover` tab, click **[Connect]** on Google Workspace or Slack. Confirm a popup opens with Composio's managed OAuth flow. Complete sign-in, close window, and observe the card transition to **[Connected]** in the `Yours` tab.
3. **Generative UI GST Card**: Prompt: *"Generate an invoice preview for Acme Corp with GSTIN 27ABCDE1234F1Z5 for 10 laptops at ₹60,000 each + 18% GST"*. Verify assistant-ui renders a rich, styled GST invoice component (with CGST 9% + SGST 9% breakdown, download PDF button, and editable line items).
4. **Realtime Push Toast**: In a separate terminal or Supabase Dashboard, insert a test notification into `public.user_notifications`. Verify an in-app banner toast appears in the top-right corner of the web interface within 1 second.
