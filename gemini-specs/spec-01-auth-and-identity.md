# Spec 01: Enterprise & SMB Identity + DPDP Statutory Consent via Supabase Auth

## 1. Context & Motivation
Indian SMBs (<100 seats) rely on **Google Workspace**, **Zoho Workplace**, or company domain email, rarely holding expensive Okta or Microsoft Entra ID P1/P2 licenses. Furthermore, India's **DPDP Act 2023 (Sec 5 & 6)** mandates clear, itemized notice and explicit consent before processing employee data with AI models.
This spec implements multi-provider SMB authentication, token management, and statutory consent interceptors directly on **Supabase Auth**.

## 2. Objective & Non-Goals
- **Objective**: Employees authenticate via Google Workspace, Zoho OAuth, Enterprise SAML/OIDC (Entra/Okta), or domain-restricted Magic Links using Supabase Auth. First-time users accept an itemized DPDP privacy notice. App Store reviewers get a dedicated test login.
- **Non-Goals**: No public, unverified sign-ups. Email addresses outside the organization's verified domain(s) are blocked by Supabase Auth domain hooks.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/auth/`
  * `dependencies.py`: FastAPI security dependency extracting and validating Supabase JWTs (`auth.uid()`, `org_id`, `role`).
  * `client.py`: Supabase Admin client (`supabase-py`) for administrative actions (e.g. reviewer account creation, role assignments).
* `supabase/migrations/20260927000001_auth_and_users.sql`:
  * `public.organizations` table (`id`, `name`, `domains`, `created_at`).
  * `public.profiles` table (`id` references `auth.users`, `org_id`, `email`, `role`, `created_at`).
  * `public.user_consents` table (`id`, `user_id`, `org_id`, `consent_version`, `ip_address`, `consented_at`).
  * RLS policies enforcing tenant isolation based on `auth.jwt() ->> 'org_id'`.
* `apps/web/src/app/login/`: Next.js login UI using `@supabase/ssr` with Google, Zoho, SAML SSO, and Magic Link options.
* `apps/web/src/components/auth/consent-modal.tsx`: DPDP statutory consent modal.
* `apps/mobile/src/services/auth.ts`: React Native auth service using `@supabase/supabase-js` and `expo-secure-store`.

---

## 4. Requirements & Implementation Details

### R01.1: Multi-Provider Authentication via Supabase Auth
- **Supported Identity Methods**:
  1. **Google OAuth 2.0**: Configured via Supabase Auth Google provider.
  2. **Zoho OAuth 2.0**: Custom OpenID Connect (OIDC) provider in Supabase Auth.
  3. **Enterprise SAML 2.0 / OIDC**: Built-in Supabase SSO for Microsoft Entra ID or Okta.
  4. **Domain-Restricted Magic Link**: Email OTP/magic link via Supabase Auth, restricted strictly to approved company domains via Supabase Auth Hooks (`before-user-created`).
- Block all unapproved domains: Auth hook aborts user creation with an error message: `"Domain not authorized for this workspace"`.

### R01.2: App Store Reviewer Test Account (Apple & Google Approval Guarantee)
- A seed script provisions a dedicated reviewer test account in Supabase Auth:
  - Email: `reviewer@workkbot-demo.internal`
  - Password: Pre-configured in App Store review notes.
  - Bypasses corporate MFA.
  - Bound to an isolated demo organization in `public.organizations` with seeded chat threads.

### R01.3: DPDP Act 2023 Statutory Consent Interceptor (Sec 5 & 6)
- Upon first login, users encounter a mandatory blocking interstitial before accessing chat:
  - Notice available in **English and Hindi**.
  - Itemized disclosures:
    1. Conversations and tool calls will be processed by AI models to assist with daily workflows.
    2. Derived facts and preferences will be stored in semantic memory to personalize responses.
    3. Users retain the Right to Access, Correct, and Erase their personal data at any time under DPDP Act 2023.
  - Recording: User consent is logged in `public.user_consents` with timestamp, user ID, and IP address.
  - RLS Policy:
    ```sql
    CREATE POLICY "Users can insert their own consent" ON public.user_consents
      FOR INSERT WITH CHECK (auth.uid() = user_id);
    CREATE POLICY "Users can view their own consent" ON public.user_consents
      FOR SELECT USING (auth.uid() = user_id);
    ```

### R01.4: Session Management & JWT Verification
- Supabase Auth issues short-lived JWT access tokens and secure refresh tokens with automatic token rotation.
- In FastAPI, incoming requests pass through `get_current_user`:
  - Verifies the Supabase JWT using the Supabase JWT secret or JWKS endpoint.
  - Extracts `user_id = payload["sub"]`, `org_id = payload["app_metadata"]["org_id"]`, and `role = payload["app_metadata"]["role"]`.
  - Attaches user context to the FastAPI request state.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-01.1** | Email with unapproved domain (`user@gmail.com`) is rejected by Supabase Auth hook | Test signup with unauthorized domain | [ ] |
| **VAL-01.2** | Reviewer credentials log in cleanly and access demo organization | Supabase Auth login with reviewer credentials | [ ] |
| **VAL-01.3** | First-time user cannot call `/chat` without signing DPDP consent | Unconsented user request to `/chat` returns HTTP 403 `CONSENT_REQUIRED` | [ ] |
| **VAL-01.4** | Expired JWT refresh succeeds via Supabase Auth; revoked session cannot authenticate | Refresh token rotation test | [ ] |
| **VAL-01.5** | Multi-tenant isolation verified: User from Org A cannot read Org B profiles | SQL test executing select under Org A JWT | [ ] |
