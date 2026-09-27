# Spec 01: Google-Exclusive SMB Identity, Extensible MCP Connectors Hub & DPDP Statutory Consent (GCP Day 1)

## 1. Context & Motivation
Indian SMBs (<100 seats) predominantly operate on **Google Workspace** for employee identity, while leveraging **Zoho Workplace** (`.in` datacenter) for operational tools (Zoho Books for GST/invoicing, Zoho CRM for sales). However, **Google Workspace and Zoho are merely Day-1 seed connectors** to bootstrap the workspace. In reality, Workkbot's connector plane is an **open-ended, extensible Model Context Protocol (MCP) ecosystem** capable of connecting any number of enterprise SaaS tools, custom internal databases, and developer platforms. Additionally, India's **DPDP Act 2023 (Sec 5 & 6)** mandates itemized notice and explicit statutory consent prior to processing employee data with AI models.

To eliminate onboarding friction while ensuring strict security and isolation, Workkbot deploys a unified **Dual-Layer Architecture on Google Cloud powered by assistant-ui**:
1. **Layer 1: Google-Exclusive App Authentication (Assistant-UI Sidebar Footer & Supabase Auth)**: Employees sign into Workkbot solely through **Google Workspace OAuth** using basic identity scopes (`openid`, `email`, `profile`), verified against company domain whitelists, followed by mandatory DPDP statutory consent. Authentication is triggered directly from the canonical assistant-ui sidebar footer (`-> Sign in`), or automatically gated when attempting to send an unauthenticated prompt via `ComposerPrimitive.Send`. Once authenticated, the footer dynamically transitions into the employee profile avatar, name, org badge, and DPDP privacy settings.
2. **Layer 2: In-Chat Capability Extension via Composer Plus (`+`) & Connectors Hub Modal**: Rather than burying integrations deep in Settings, an interactive **Plus (`+`) Icon** is permanently anchored inside the bottom-left controls of assistant-ui's floating composer container (`ComposerPrimitive.AddAttachment`), adjacent to the `[ Chat | Canvas ]` mode toggle and model selector. Clicking `+` opens a unified action menu with categorized submenus:
   - **File & Multimodal Ingestion**:
     - `Add files or photos` (`⌘U`): Ingests spreadsheets, PDFs, invoices, and photos via assistant-ui's `AttachmentPrimitive`.
     - `Take a screenshot`: Captures current screen for Gemini 2.0 multimodal visual reasoning.
     - `Add to project >`: Binds conversation context to an organizational workspace or project folder.
   - **Agentic Capabilities & Extensible Connectors Hub**:
     - `Skills >`: Browse and invoke content-as-data skills (Spec 08: GST calculator, invoice reconciler, Tally sync).
     - `Connectors >`: Opens the **Connectors Hub Modal** featuring:
       - **Tabs `[ Yours | Discover ]`**: `Yours` manages active connections with live status and disconnect actions; `Discover` browses a categorized catalog of verified MCP servers (Google Drive, Gmail, Google Calendar, Canva, Microsoft 365, Notion, Figma, Slack, Atlassian Jira/Confluence, HubSpot, Asana, Linear, Zoho CRM, Zoho Books, Tally Prime).
       - **Header Controls**: Live search (`🔍 Search connectors`), category filters, and a prominent **`+ Add ▾`** button to connect custom MCP endpoints (SSE/stdio) or import SMB OpenAPI specs (Spec 05).
       - **Credentials**: Hardware-encrypted in **Supabase Vault (`pgsodium`)** as `mcp_token_${user_id}_${provider_id}`.
     - `Add plugins`: Dynamic plugin and OpenAPI virtualization hub (Spec 05).
   - **Grounding Toggle**:
     - `Web search` (`✓` toggle): Enables real-time Google Search grounding via Vertex AI.
   If an agent invocation requires authorization mid-conversation, assistant-ui's `useAdkAuthRequests()` and `useAdkSubmitAuth()` automatically surface inline authentication challenges directly in the chat stream.

---

## 2. Objective & Non-Goals
- **Objective**: 
  - Single-click employee login via Google Workspace OAuth, triggered from the canonical assistant-ui sidebar footer (`-> Sign in`) or composer gate, verified against the organization's approved domains.
  - In-chat **`+` Action Menu** anchored inside assistant-ui's floating composer container allows users to attach files, grab screenshots, bind projects, select skills, manage the **Connectors Hub** (`Yours` / `Discover`), and toggle web search without leaving the conversation.
  - Symmetrical OAuth 2.0 connection engine supporting an open-ended catalog of MCP servers beyond the initial Google and Zoho starters (Microsoft 365, Notion, Slack, Canva, Figma, Atlassian, HubSpot, Linear, Asana, Tally).
  - In-stream OAuth challenges surfaced seamlessly via assistant-ui's `useAdkAuthRequests()` and `useAdkSubmitAuth()`.
  - User OAuth tokens for any connected MCP server are encrypted at rest in Supabase Vault, auto-refreshed at runtime by the backend, and securely forwarded to Agentgateway for upstream MCP authentication.
  - Agentgateway enforces per-session CEL isolation, preventing cross-tenant or cross-user tool access.
  - First-time users accept an itemized DPDP privacy notice before issuing chat or tool calls.
  - App Store reviewers receive a deterministic, isolated test login bypassing corporate Google SSO.
- **Non-Goals**: 
  - No Zoho or third-party login for app authentication (app authentication is Google Workspace exclusive; all other providers are on-demand MCP connectors).
  - No public or unauthorized email sign-ups (strictly blocked by domain hooks).
  - No complex multi-page settings navigation to connect daily tools.

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/auth/`
  * `dependencies.py`: FastAPI security dependency running on Cloud Run validating Supabase JWTs (`auth.uid()`, `org_id`, `role`).
  * `client.py`: Supabase Admin client (`supabase-py`) for administrative tasks and role assignment.
  * `delegation.py`: Interceptor retrieving user's encrypted OAuth tokens from Supabase Vault for any connected provider and provisioning authenticated session headers to Agentgateway (`http://127.0.0.1:8080/mcp`).
* `supabase/migrations/20260927000001_auth_and_users.sql`:
  * `public.organizations`: (`id`, `name`, `domains`, `created_at`).
  * `public.profiles`: (`id` references `auth.users`, `org_id`, `email`, `role`, `created_at`).
  * `public.user_consents`: (`id`, `user_id`, `org_id`, `consent_version`, `ip_address`, `consented_at`).
  * `public.mcp_connections`: (`id`, `user_id`, `org_id`, `provider`, `scopes`, `vault_secret_id`, `status`, `updated_at`).
  * RLS policies enforcing tenant isolation based on `auth.jwt() ->> 'org_id'`.
* `apps/web/src/app/login/`: Ultra-clean Next.js login UI featuring a single primary **[Continue with Google Workspace]** button.
* `apps/web/src/components/sidebar/sidebar-auth-footer.tsx`: Canonical assistant-ui sidebar footer displaying `-> Sign in` (unauthenticated) or employee profile avatar, name, and DPDP privacy settings (authenticated).
* `apps/web/src/components/chat/connectors-hub-modal.tsx`: Comprehensive Connectors Hub Modal featuring `[ Yours | Discover ]` tabs, search, category directory, and `+ Add ▾` custom MCP action.
* `apps/web/src/components/auth/consent-modal.tsx`: DPDP statutory consent modal (English & Hindi).
* `apps/mobile/src/components/chat/ConnectorsModal.tsx`: React Native version of the Connectors Hub.
* `apps/mobile/src/services/auth.ts`: React Native auth service using `@supabase/supabase-js` and `expo-secure-store`.

---

## 4. Requirements & Implementation Details

### R01.1: Google-Exclusive User Authentication via Supabase Auth (Layer 1)
- **Primary Identity Provider**: Google Workspace OAuth 2.0 via Supabase Auth Google provider:
  - Scopes requested at login: Minimal identity only (`openid`, `email`, `profile`).
  - No sensitive mailbox or drive scopes are requested at sign-in (ensuring instant approval, zero user drop-off, and strict compliance with Google & Apple App Store guidelines).
  - Can be initiated via the dedicated `/login` route or directly from the canonical sidebar footer `-> Sign in` action.
- **Domain Whitelist Enforcement**:
  - A Supabase Auth Hook (`before-user-created`) checks `email` against `public.organizations.domains`.
  - If the user's email domain is not authorized, the hook aborts with HTTP 403: `"Domain not authorized for this workspace"`.

### R01.2: In-Chat Capability Extension via Composer Plus (`+`) Action Menu (Layer 2)
An interactive **Plus (`+`) Icon** is positioned directly inside the bottom-left of assistant-ui's floating composer container, sitting alongside the `[ Chat | Canvas ]` mode toggle and `ModelSelector` pill:

1. **Hierarchical Action Menu UI**:
   - Clicking `+` opens a structured dropdown menu modeled after modern generative AI interfaces:
     - `📎 Add files or photos` (`⌘U`): Ingests spreadsheets, PDFs, invoices, and photos via assistant-ui's `AttachmentPrimitive`.
     - `📷 Take a screenshot`: Captures current screen for Gemini 2.0 multimodal visual reasoning.
     - `📁 Add to project >`: Binds conversation context to an organizational workspace or project folder.
     - `────────` (divider)
     - `📑 Skills >`: Submenu displaying discovered content-as-data skills (Spec 08: GST calculation, invoice audit, Tally sync).
     - `🔲 Connectors >`: Opens the full **Connectors Hub Modal** (or quick submenu):
       - **Seed Starters**: Google Workspace (Drive, Gmail, Calendar, Docs, Sheets) and Zoho Workplace (Zoho CRM, Zoho Books, Zoho Mail) are provided out-of-the-box as initial reference connectors to launch the app.
       - **Open-Ended Extensibility**: The Connectors Hub supports any number of third-party or enterprise MCP servers across productivity, engineering, design, and finance.
     - `🎨 Design system >` / `🧩 Add plugins`: Dynamic plugin and OpenAPI virtualization hub (Spec 05).
     - `────────` (divider)
     - `🌐 Web search` (`✓` toggle): Enables real-time Google Search grounding via Vertex AI.
2. **The Connectors Hub Modal (`Settings` & `Customize > Connectors`)**:
   - Triggered either from `+ -> Connectors >` in the composer or via sidebar `Settings -> Connectors`.
   - **Left-Hand Navigation Sidebar**:
     - `🔍 Search` navigation bar for quickly filtering modal panes.
     - **Settings**: `General`, `Account`, `Privacy` (DPDP consent & export), `Billing`, `Capabilities`, `Memory`, `Reflect`, `Time and focus`, `Claude Code`.
     - **Customize**: `Skills` (Spec 08 content-as-data skills), `Connectors` (Active View), `Plugins` (OpenAPI & dynamic extensions).
   - **Main Content Pane**:
     - **Header Bar**:
       - Title: **"Connectors"**
       - Segmented Toggle: **`[ Yours | Discover ]`** (`Discover` selected by default for exploring available integrations).
       - Search Bar: **`🔍 Search connectors`** for filtering the catalog in real-time.
       - Filter Button: Capabilities and category filter icon.
       - **`+ Add ▾`** Action: Dropdown allowing users and admins to add custom MCP endpoints (via SSE or containerized stdio) or import OpenAPI specifications.
       - Close Button: **`✕`** icon to dismiss modal.
     - **Category Subheader**:
       - Section heading: **"Top connectors"** with count badge (e.g., `3282`).
       - Quick navigation: **"Show all ➔"** link.
     - **Two-Column Connector Card Grid**:
       - Each card features:
         - Brand Logo / Icon.
         - Verified Checkmark Badge (`☑`).
         - 2-line capability description.
         - Publisher attribution (e.g., `by Google`, `by Anthropic`, `by Notion`, `by Slack`, `by Canva`, `by Figma`, `by Atlassian`, `by HubSpot`, `by Asana`, `by Linear`, `by Zoho`).
         - Top-right action button **`+`** (Install / Connect), transitioning to a status toggle or disconnect menu when active.
       - Ecosystem Catalog includes: **Google Drive**, **Gmail**, **Google Calendar**, **Canva**, **Microsoft 365**, **Notion**, **Figma**, **Slack**, **Atlassian MCP** (Jira & Confluence), **HubSpot**, **Asana**, **Linear**, **Zoho CRM**, **Zoho Books**, **Tally Prime**, and custom endpoints.
     - **`Yours` Tab**:
       - Displays all currently connected MCP servers for the authenticated user, showing live health status, authorized scopes, and **[Disconnect]** / **[Re-authorize]** actions.

3. **Symmetrical OAuth 2.0 Flow & Supabase Vault Storage**:
   - Clicking **`+`** on any connector card initiates standard OAuth 2.0 authorization code flow with `access_type=offline`:
     - **Google Workspace** (Seed): `https://accounts.google.com/o/oauth2/v2/auth`. Scopes: `gmail.modify`, `calendar.events`, `drive.file`, Docs, Sheets.
     - **Zoho Workplace** (Seed): `https://accounts.zoho.in/oauth/v2/auth`. Scopes: `ZohoCRM.modules.ALL`, `ZohoBooks.fullaccess.ALL`, `ZohoMail.messages.ALL`, `offline`.
     - **Ecosystem Connectors**: Standard OAuth 2.0 endpoints for Microsoft 365, Notion, Slack, Canva, Figma, Atlassian, HubSpot, etc.
   - On redirect, Workkbot exchanges code for `access_token` and `refresh_token`, encrypts them into **Supabase Vault (`pgsodium`)** as `mcp_token_${user_id}_${provider_id}`, and updates `public.mcp_connections`.

4. **Instant Agent Tool Registration via Agentgateway**:
   - As soon as a connection completes, the active chat session registers the new tools through Agentgateway (`http://127.0.0.1:8080/mcp`).
   - The user can immediately ask: *"Search my drive for Q3 sales deck"*, *"Summarize Jira tickets assigned to me"*, or *"Fetch my unpaid Zoho invoices"* without page refresh.

5. **Runtime Token Delegation & Auto-Refresh**:
   - When an agent executes an MCP tool, `delegation.py` on Cloud Run retrieves the decrypted token from Supabase Vault.
   - If expired, Workkbot auto-refreshes using the provider's token endpoint.
   - Workkbot injects the fresh token into the session context sent to Agentgateway (`http://127.0.0.1:8080/mcp`), which sets `Authorization: Bearer <access_token>` into the upstream MCP server request.

6. **Per-Session CEL Isolation in Agentgateway**:
   - Agentgateway evaluates CEL authorization policies enforcing that a session can only invoke tools backed by credentials owned by `request.auth.claims.sub` (the authenticated user).
   - Cross-user or cross-org tool discovery is blocked at the proxy layer.

### R01.3: App Store Reviewer Test Account (Apple & Google Approval Guarantee)
- A seed script provisions a dedicated reviewer test account in Supabase Auth:
  - Email: `reviewer@workkbot-demo.internal`
  - Password: Pre-configured in App Store review notes.
  - Bypasses corporate Google SSO and MFA.
  - Bound to an isolated demo organization with pre-seeded mock Google Workspace and Zoho tool responses for seamless reviewer testing.

### R01.4: DPDP Act 2023 Statutory Consent Interceptor (Sec 5 & 6)
- Upon first login, users encounter a mandatory blocking interstitial before accessing chat:
  - Notice available in **English and Hindi**.
  - Itemized disclosures:
    1. Conversations and tool calls will be processed by AI models to assist with daily workflows.
    2. Connected workspace tools (Google Drive/Gmail, Zoho CRM/Books) will be queried based on user instructions.
    3. Derived facts and preferences will be stored in semantic memory to personalize responses.
    4. Users retain the Right to Access, Correct, and Erase their personal data at any time under DPDP Act 2023.
  - Recording: User consent is logged in `public.user_consents` with timestamp, user ID, and IP address.

### R01.5: Session Management & JWT Verification on Cloud Run
- Supabase Auth issues short-lived JWT access tokens and secure refresh tokens with automatic token rotation.
- In FastAPI on Cloud Run, incoming requests pass through `get_current_user`:
  - Verifies the Supabase JWT using the Supabase JWKS endpoint.
  - Extracts `user_id = payload["sub"]`, `org_id = payload["app_metadata"]["org_id"]`, and `role = payload["app_metadata"]["role"]`.
  - Attaches user context and resolved MCP vault secret pointers to the FastAPI request state.
  - Propagates JWT claims in loopback headers to Agentgateway (`127.0.0.1:8080`) for CEL policy evaluation.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-01.1** | Email with unapproved domain (`user@gmail.com`) is rejected by Supabase Auth hook | `pytest apps/backend/tests/test_auth_domain_whitelist.py` | [ ] |
| **VAL-01.2** | Google Workspace OAuth login succeeds requesting only basic identity (`openid`, `email`, `profile`) | `pytest apps/backend/tests/test_google_oauth_scopes.py` | [ ] |
| **VAL-01.3** | Reviewer credentials log in cleanly and access isolated demo organization | `curl -f -X POST https://$BACKEND_URL/api/v1/auth/reviewer-login` | [ ] |
| **VAL-01.4** | First-time user cannot call `/chat` without signing DPDP statutory consent | `pytest apps/backend/tests/test_dpdp_consent_gate.py` | [ ] |
| **VAL-01.5** | In-chat `+` icon opens tool popover and connects Google Workspace MCP via OAuth | `pnpm --filter web test:e2e tests/e2e/tool-popover.spec.ts` | [ ] |
| **VAL-01.6** | In-chat `+` icon connects Zoho Workplace MCP via `accounts.zoho.in` and stores token in Vault | `pytest apps/backend/tests/test_zoho_oauth_vault.py` | [ ] |
| **VAL-01.7** | Multi-tenant isolation verified: User from Org A cannot access Org B MCP connections or secrets | `pytest apps/backend/tests/test_mcp_tenant_isolation.py` | [ ] |
| **VAL-01.8** | Token delegation from Supabase Vault to Agentgateway securely injects upstream bearer token | `pytest apps/backend/tests/test_agentgateway_token_delegation.py` | [ ] |
