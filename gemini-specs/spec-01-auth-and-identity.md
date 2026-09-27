# Spec 01: Enterprise Identity, Extensible Connectors Hub & DPDP Consent (The 5-Framework Model)

## 1. Context & Motivation
Indian SMBs (<100 seats) predominantly operate on **Google Workspace** for employee identity, while leveraging **Zoho Workplace** (`.in` datacenter) for operational tools (Zoho Books for GST/invoicing, Zoho CRM for sales). However, Google Workspace and Zoho are merely Day-1 seed connectors to bootstrap the workspace. In reality, Workkbot's connector plane is an **open-ended, extensible Model Context Protocol (MCP) ecosystem** capable of connecting any number of enterprise SaaS tools, custom internal databases, and developer platforms. Additionally, India's **DPDP Act 2023 (Sec 5 & 6)** and **Apple App Store Review Guidelines (1.2, 2.1, 5.1.1, 5.1.2i)** mandate explicit itemized notice, statutory consent, reviewer demo access, and complete in-app account deletion.

To eliminate onboarding friction while ensuring strict security and isolation, Workkbot routes all identity, authorization, and consent decisions through the **5 Core Frameworks**:
1. **Supabase**: Unified identity provider, domain-whitelisted access, hardware-encrypted Vault for third-party MCP tokens, and tenant-isolated relational persistence with RLS.
2. **Google Cloud Platform (GCP)**: Cloud Run multi-container hosting, Cloud Armor WAF rate-limiting on auth endpoints, and Cloud Logging for security audit trails.
3. **Google ADK 2.0**: In-process conversational agent runtime binding sessions to authenticated identities and surfacing in-stream auth challenges via `useAdkAuthRequests()`.
4. **assistant-ui**: The canonical visual surface providing the sidebar footer authentication state (`-> Sign in` / profile), floating composer `+` action menu, the interactive Connectors Hub Modal (`[ Yours | Discover ]`), and inline OAuth challenge cards.
5. **Agentgateway 1.5.x**: Rust-based proxy evaluating CEL authorization policies per-session, ensuring that tool execution is strictly isolated to the user's authorized credentials with zero cross-tenant leakage.

### **The North Star: Security & Mobile App Approval**
- **Security**: Zero plaintext tokens (all sealed in Supabase Vault via `pgsodium`), strict domain whitelisting, session-scoped CEL policy enforcement in Agentgateway, and statutory consent stored immutably.
- **Mobile App Approval (Apple & Google Play)**:
  - **Apple Guideline 2.1 (App Completeness)**: Built-in Reviewer Sandbox credentials (`apple-reviewer@workkbot.in`) allowing instantaneous login into an isolated Supabase tenant without corporate Google SSO.
  - **Apple Guideline 5.1.1 (Data Collection & Storage)**: Native in-app account deletion triggering complete erasure across Supabase Auth, database records, and third-party Vault tokens.
  - **Apple Guideline 5.1.2(i) (Third-Party AI Disclosure)**: Explicit pre-chat bilingual statutory consent outlining exact data flow to AI models.
  - **Apple Guideline 3.1.3(c) (Enterprise Sign-In)**: Compliant enterprise B2B login without in-app purchase gating.

---

## 2. The 5-Framework Architecture Mapping for Spec 01

| Framework | Core Responsibility in Identity & Connectors Hub | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | GoTrue Auth for Google Workspace OAuth, `public.user_consents`, `public.mcp_connections`, and Supabase Vault (`pgsodium`) for token hardware encryption. | Enforces RLS by `auth.jwt() ->> 'org_id'`. In-app account deletion via `auth.admin.deleteUser()` purges all associated vault tokens and session records (Apple 5.1.1). |
| **2. Google Cloud Platform (GCP)** | FastAPI backend running on Cloud Run in Mumbai (`asia-south1`) verifying Supabase JWKS; Cloud Armor WAF protecting auth endpoints. | Direct VPC Egress prevents metadata credential extraction. Cloud Armor blocks non-Indian IPs (`origin.region_code == 'IN'`). |
| **3. Google ADK 2.0** | Binds active agent sessions to authenticated user context; pauses execution and emits auth challenges when tools lack credentials. | Emits standard ADK auth events consumed by assistant-ui; prevents unauthenticated tool dispatch in agent loop. |
| **4. assistant-ui** | Sidebar footer (`-> Sign in` / avatar profile), floating composer `+` action dropdown, Connectors Hub Modal (`[ Yours | Discover ]`), and inline auth challenge cards (`useAdkAuthRequests`). | Responsive cross-platform interface (`@assistant-ui/react` and `@assistant-ui/react-native`); enables seamless OAuth popup and mobile deep-linking. |
| **5. Agentgateway 1.5.x** | Sidecar proxy on `127.0.0.1:8080` receiving delegated tokens from backend and evaluating CEL authorization rules. | Evaluates `request.auth.claims.sub == resource.owner`; completely blocks cross-tenant and cross-user tool access. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/auth/`
  * `dependencies.py`: FastAPI security dependency validating Supabase JWTs (`auth.uid()`, `org_id`, `role`).
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

### R01.1: Google-Exclusive User Authentication via Supabase Auth (Supabase + GCP + assistant-ui)
- **Primary Identity Provider**: Google Workspace OAuth 2.0 via Supabase Auth:
  - Scopes requested at login: Minimal identity only (`openid`, `email`, `profile`).
  - No sensitive mailbox or drive scopes are requested at sign-in (ensuring instant approval, zero user drop-off, and strict compliance with Google & Apple App Store guidelines).
  - Can be initiated via the dedicated `/login` route or directly from the canonical sidebar footer `-> Sign in` action in assistant-ui.
- **Domain Whitelist Enforcement**:
  - A Supabase Auth Hook (`before-user-created`) checks `email` against `public.organizations.domains`.
  - If the user's email domain is not authorized, the hook aborts with HTTP 403: `"Domain not authorized for this workspace"`.

### R01.2: In-Chat Capability Extension via Composer Plus (`+`) & Connectors Hub Modal (assistant-ui + Supabase Vault + Agentgateway)
An interactive **Plus (`+`) Icon** is positioned directly inside the bottom-left of assistant-ui's floating composer container, sitting alongside the `[ Chat | Canvas ]` mode toggle and `ModelSelector` pill:

1. **Hierarchical Action Menu UI**:
   - Clicking `+` opens a structured dropdown menu modeled after modern generative AI interfaces:
     - `📎 Add files or photos` (`⌘U`): Ingests spreadsheets, PDFs, invoices, and photos via assistant-ui's `AttachmentPrimitive`.
     - `📷 Take a screenshot`: Captures current screen for Gemini 2.0 multimodal visual reasoning.
     - `📁 Add to project >`: Binds conversation context to an organizational workspace or project folder.
     - `────────` (divider)
     - `📑 Skills >`: Submenu displaying discovered content-as-data skills (Spec 08: GST calculation, invoice audit, Tally sync).
     - `🔲 Connectors >`: Opens the full **Connectors Hub Modal**:
       - **Seed Starters**: Google Workspace (Drive, Gmail, Calendar, Docs, Sheets) and Zoho Workplace (Zoho CRM, Zoho Books, Zoho Mail) are provided out-of-the-box as initial reference connectors to launch the app.
       - **Open-Ended Extensibility**: The Connectors Hub supports any number of third-party or enterprise MCP servers across productivity, engineering, design, and finance.
     - `🎨 Design system >` / `🧩 Add plugins`: Dynamic plugin and OpenAPI virtualization hub (Spec 05).
     - `────────` (divider)
     - `🌐 Web search` (`✓` toggle): Enables real-time Google Search grounding via Vertex AI.
2. **The Connectors Hub Modal (`[ Yours | Discover ]`)**:
   - Triggered either from `+ -> Connectors >` in the composer or via sidebar `Settings -> Connectors`.
   - **Header Controls**: Title **"Connectors"**, Segmented Toggle **`[ Yours | Discover ]`**, Search Bar **`🔍 Search connectors`**, and prominent **`+ Add ▾`** action for custom MCP endpoints (SSE/stdio) or OpenAPI specs.
   - **Two-Column Connector Card Grid**:
     - Verified Checkmark Badge (`☑`), 2-line capability description, publisher attribution (`by Google`, `by Zoho`, `by Notion`, `by Slack`, `by Atlassian`, `by Canva`, `by Figma`, `by HubSpot`), and action button **`+`** (Install / Connect).
   - **`Yours` Tab**: Displays active connections, live health status, authorized scopes, and **[Disconnect]** / **[Re-authorize]** actions.
3. **Symmetrical OAuth 2.0 Flow & Supabase Vault Storage**:
   - Clicking **`+`** initiates OAuth 2.0 authorization code flow with `access_type=offline`.
   - Backend exchanges code for `access_token` and `refresh_token`, encrypts them into **Supabase Vault (`pgsodium`)** as `mcp_token_${user_id}_${provider_id}`, and updates `public.mcp_connections`.
4. **Instant Tool Registration via Agentgateway**:
   - As soon as a connection completes, the active chat session registers the new tools through Agentgateway (`http://127.0.0.1:8080/mcp`).
   - The user can immediately ask: *"Search my drive for Q3 sales deck"* or *"Fetch my unpaid Zoho invoices"* without page reload.
5. **Runtime Token Delegation & Auto-Refresh**:
   - When an agent executes an MCP tool, `delegation.py` on Cloud Run retrieves the decrypted token from Supabase Vault, auto-refreshes if needed, and passes it to Agentgateway.
6. **Per-Session CEL Isolation in Agentgateway**:
   - Agentgateway evaluates CEL authorization policies enforcing that a session can only invoke tools backed by credentials owned by `request.auth.claims.sub`.

### R01.3: App Store Reviewer Test Account (Apple Guideline 2.1 & Google Play Compliance)
- A seed script provisions a dedicated reviewer test account in Supabase Auth:
  - Email: `apple-reviewer@workkbot.in`
  - Password: Pre-configured in App Store review notes.
  - Bypasses corporate Google SSO and MFA.
  - Bound to an isolated demo organization with pre-seeded mock Google Workspace and Zoho tool responses for seamless reviewer testing.

### R01.4: DPDP Act 2023 Statutory Consent & AI Disclosure (Apple Guideline 5.1.2i)
- Upon first login, users encounter a mandatory blocking interstitial before accessing chat:
  - Notice available in **English and Hindi**.
  - Itemized disclosures:
    1. Conversations and tool calls will be processed by AI models to assist with daily workflows.
    2. Connected workspace tools will be queried based on user instructions.
    3. Derived facts and preferences will be stored in semantic memory to personalize responses.
    4. Users retain the Right to Access, Correct, and Erase their personal data at any time.
  - Recording: User consent is logged in `public.user_consents` with timestamp, user ID, and IP address.

### R01.5: In-App Account & Data Deletion (Apple Guideline 5.1.1 Compliance)
- The profile drawer in assistant-ui provides a prominent, destructive **[Delete Account & Purge Data]** button.
- Triggering this calls the backend `/api/v1/account/delete` endpoint:
  - Atomically invokes `auth.admin.deleteUser(user_id)`.
  - Cascades complete deletion across `profiles`, `mcp_connections`, Supabase Vault secrets, chat sessions, and vector embeddings.
  - Meets Apple App Store Guideline 5.1.1 requirement that account deletion must be executable in-app without requiring email or external support.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-01.1** | Email with unapproved domain (`user@gmail.com`) is rejected by Supabase Auth hook | `pytest apps/backend/tests/test_auth_domain_whitelist.py` | [ ] |
| **VAL-01.2** | Google Workspace OAuth login succeeds requesting only basic identity (`openid`, `email`, `profile`) | `pytest apps/backend/tests/test_google_oauth_scopes.py` | [ ] |
| **VAL-01.3** | Reviewer credentials log in cleanly and access isolated demo organization (Apple 2.1) | `curl -f -X POST https://$BACKEND_URL/api/v1/auth/reviewer-login` | [ ] |
| **VAL-01.4** | First-time user cannot call `/chat` without signing DPDP statutory consent (Apple 5.1.2i) | `pytest apps/backend/tests/test_dpdp_consent_gate.py` | [ ] |
| **VAL-01.5** | In-chat `+` icon opens tool popover and connects Google Workspace MCP via OAuth | `pnpm --filter web test:e2e tests/e2e/tool-popover.spec.ts` | [ ] |
| **VAL-01.6** | In-chat `+` icon connects Zoho Workplace MCP via `accounts.zoho.in` and stores token in Vault | `pytest apps/backend/tests/test_zoho_oauth_vault.py` | [ ] |
| **VAL-01.7** | Multi-tenant isolation verified: User from Org A cannot access Org B MCP connections or secrets | `pytest apps/backend/tests/test_mcp_tenant_isolation.py` | [ ] |
| **VAL-01.8** | Token delegation from Supabase Vault to Agentgateway securely injects upstream bearer token | `pytest apps/backend/tests/test_agentgateway_token_delegation.py` | [ ] |
| **VAL-01.9** | In-app account deletion purges user, vault secrets, and sessions completely (Apple 5.1.1) | `pytest apps/backend/tests/test_account_deletion_flow.py` | [ ] |
