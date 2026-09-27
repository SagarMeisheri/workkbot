# Spec 01: Google-Exclusive SMB Identity, In-Chat MCP Tool Connector (+) & DPDP Statutory Consent (GCP Day 1)

## 1. Context & Motivation
Indian SMBs (<100 seats) predominantly operate on **Google Workspace** for employee identity, while leveraging **Zoho Workplace** (`.in` datacenter) for operational tools (Zoho Books for GST/invoicing, Zoho CRM for sales). Additionally, India's **DPDP Act 2023 (Sec 5 & 6)** mandates itemized notice and explicit statutory consent prior to processing employee data with AI models.

To eliminate onboarding friction while ensuring strict compliance, Workkbot deploys a streamlined **Dual-Layer Architecture on Google Cloud**:
1. **Layer 1: Google-Exclusive App Authentication (Supabase Auth in Mumbai)**: Employees sign into Workkbot solely through **Google Workspace OAuth** using basic identity scopes (`openid`, `email`, `profile`), verified against company domain whitelists, followed by mandatory DPDP statutory consent.
2. **Layer 2: In-Chat MCP Tool Connector via Plus (`+`) Icon**: Rather than burying integrations deep in Settings, an interactive **Plus (`+`) Icon** sits directly next to the chat typing window. Clicking `+` opens a lightweight popover where users connect or disconnect **Google Workspace MCP** and **Zoho Workplace MCP** via standard OAuth 2.0, securely encrypted in **Supabase Vault (`pgsodium`)**.

---

## 2. Objective & Non-Goals
- **Objective**: 
  - Single-click employee login via Google Workspace OAuth, verified against the organization's approved domains.
  - In-chat **`+` tool connector** adjacent to the chat input allows users to connect Google Workspace and Zoho tools on demand without leaving the conversation.
  - User OAuth tokens for Google and Zoho MCP servers are encrypted at rest in Supabase Vault and auto-refreshed at runtime by the Cloud Run backend.
  - First-time users accept an itemized DPDP privacy notice before issuing chat or tool calls.
  - App Store reviewers receive a deterministic, isolated test login bypassing corporate Google SSO.
- **Non-Goals**: 
  - No Zoho login for app authentication (Zoho is strictly an on-demand MCP tool).
  - No public or unauthorized email sign-ups (strictly blocked by domain hooks).
  - No complex multi-page settings navigation to connect daily tools.

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/auth/`
  * `dependencies.py`: FastAPI security dependency running on Cloud Run validating Supabase JWTs (`auth.uid()`, `org_id`, `role`).
  * `client.py`: Supabase Admin client (`supabase-py`) for administrative tasks and role assignment.
  * `delegation.py`: Interceptor retrieving user's encrypted Google/Zoho OAuth tokens from Supabase Vault to authenticate MCP sessions.
* `supabase/migrations/20260927000001_auth_and_users.sql`:
  * `public.organizations`: (`id`, `name`, `domains`, `created_at`).
  * `public.profiles`: (`id` references `auth.users`, `org_id`, `email`, `role`, `created_at`).
  * `public.user_consents`: (`id`, `user_id`, `org_id`, `consent_version`, `ip_address`, `consented_at`).
  * `public.mcp_connections`: (`id`, `user_id`, `org_id`, `provider`, `vault_secret_id`, `status`, `updated_at`).
  * RLS policies enforcing tenant isolation based on `auth.jwt() ->> 'org_id'`.
* `apps/web/src/app/login/`: Ultra-clean Next.js login UI featuring a single primary **[Continue with Google Workspace]** button.
* `apps/web/src/components/chat/chat-input.tsx`: Chat typing bar incorporating the in-chat `+` tool button.
* `apps/web/src/components/chat/tool-popover.tsx`: In-chat popover rendered on clicking `+`, displaying Google Workspace and Zoho connection cards.
* `apps/web/src/components/auth/consent-modal.tsx`: DPDP statutory consent modal (English & Hindi).
* `apps/mobile/src/components/chat/ToolPopover.tsx`: React Native version of the in-chat `+` tool connector.
* `apps/mobile/src/services/auth.ts`: React Native auth service using `@supabase/supabase-js` and `expo-secure-store`.

---

## 4. Requirements & Implementation Details

### R01.1: Google-Exclusive User Authentication via Supabase Auth (Layer 1)
- **Primary Identity Provider**: Google Workspace OAuth 2.0 via Supabase Auth Google provider:
  - Scopes requested at login: Minimal identity only (`openid`, `email`, `profile`).
  - No sensitive mailbox or drive scopes are requested at sign-in (ensuring instant approval, zero user drop-off, and strict compliance with Google & Apple App Store guidelines).
- **Domain Whitelist Enforcement**:
  - A Supabase Auth Hook (`before-user-created`) checks `email` against `public.organizations.domains`.
  - If the user's email domain is not authorized, the hook aborts with HTTP 403: `"Domain not authorized for this workspace"`.

### R01.2: In-Chat MCP Tool Connector via Plus (`+`) Icon (Layer 2)
An interactive **Plus (`+`) Icon** is positioned immediately next to the chat message input window (in both Web and Mobile apps):

1. **In-Chat Popover UI**:
   - Clicking `+` opens a compact **"Connect Tools"** popover with two primary cards:
     - **Google Workspace** (Gmail, Drive, Docs, Sheets, Calendar)
     - **Zoho Workplace** (Zoho CRM, Zoho Books, Zoho Mail)
   - Each card displays current status:
     - `Connected` badge with a disconnect option.
     - `Connect` button if not yet authorized.
2. **Symmetrical OAuth 2.0 Flow**:
   - Clicking **[Connect]** initiates standard OAuth 2.0 authorization code flow with `access_type=offline`:
     - **Google Workspace**: Authorizes against `https://accounts.google.com/o/oauth2/v2/auth`. Scopes: `gmail.modify`, `calendar.events`, `drive.file`, Docs, Sheets.
     - **Zoho Workplace**: Authorizes against `https://accounts.zoho.in/oauth/v2/auth`. Scopes: `ZohoCRM.modules.ALL`, `ZohoBooks.fullaccess.ALL`, `ZohoMail.messages.ALL`, `offline`.
   - On redirect, Workkbot exchanges code for `access_token` and `refresh_token`, encrypts them into **Supabase Vault (`pgsodium`)**, and updates `public.mcp_connections`.
3. **Instant Agent Tool Registration**:
   - As soon as a connection completes, the active chat session registers the new tools dynamically. The user can immediately ask: *"Search my drive for Q3 sales deck"* or *"Fetch my unpaid Zoho invoices"* without page refresh.
4. **Runtime Token Delegation & Auto-Refresh**:
   - When an agent executes an MCP tool, `delegation.py` on Cloud Run retrieves the decrypted token from Supabase Vault.
   - If expired, Workkbot auto-refreshes using the refresh token (against Google or `https://accounts.zoho.in/oauth/v2/token`) and injects `Authorization: Bearer <access_token>` into the MCP Streamable HTTP / SSE request header.

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
