# Spec 10: App-Store-Certified Native Mobile App (The 5-Framework Architecture)

## 1. Context & Motivation
Submitting an AI assistant app to the Apple App Store and Google Play Store is notorious for high rejection rates.
Common rejection traps include:
- **Apple Guideline 1.2 & 1.2.1 / Google Play AI Policy**: Missing in-app reporting/flagging for AI responses, or lack of objectionable content filtering.
- **Apple Guideline 2.1**: App review team locked out because enterprise SSO MFA blocks them.
- **Apple Guideline 2.5.2**: Unsandboxed code execution altering native behavior.
- **Apple Guideline 3.1.3(c)**: Enterprise-only apps rejected for general public store distribution without clear multi-tenant enterprise login paths.
- **Apple Guideline 5.1.1**: Missing friction-free in-app account and data deletion flow.
- **Apple Guideline 5.1.2(i)**: Undisclosed transmission of user data to third-party AI models without explicit pre-chat consent.
- **Privacy Manifests**: Missing required-reasons API declarations (`PrivacyInfo.xcprivacy`).

This spec builds the **React Native (Expo SDK 52+)** native mobile app integrated with **`@assistant-ui/react-native`**, **`@supabase/supabase-js`**, connected to **Google Cloud Run via Google Cloud Armor in `asia-south1`**, fronted by **Agentgateway 1.5.x**, and executing **Google ADK 2.0** streaming turns, guaranteeing 100% first-pass App Store approval.

### **The North Star: Security & Mobile App Approval**
- **Security**: Hardware-backed session storage in iOS Keychain / Android Keystore (`expo-secure-store`), biometric authentication (`expo-local-authentication`), Cloud Armor WAF with geofencing, and strict tenant RLS.
- **Mobile App Approval (Apple App Store & Google Play)**:
  - **Guideline 1.2 (AI UGC Moderation)**: Native `ActionBarPrimitive` embedding instant **[Report / Flag AI Output]** action on every message bubble.
  - **Guideline 2.1 (App Completeness & Reviewer Sandbox)**: Deterministic review credentials (`apple-reviewer@workkbot.in`) bypassing corporate MFA to enter an isolated demo tenant with pre-seeded sandbox tools.
  - **Guideline 2.5.2 (Execution of Code)**: Sandboxed `react-native-webview` for visual artifacts, strictly prohibiting native runtime code loading.
  - **Guideline 3.1.3(c) (Enterprise Sign-In)**: Compliant enterprise B2B login without in-app purchase paywalls.
  - **Guideline 5.1.1 (In-App Account Deletion)**: One-tap **"Delete Account & Purge Memory"** button in Settings invoking Supabase atomic erasure.
  - **Guideline 5.1.2(i) (AI Data Consent)**: Mandatory bilingual consent modal before starting the first chat session.
  - **Privacy Manifest**: Clean `PrivacyInfo.xcprivacy` declaring all required reasons.

---

## 2. The 5-Framework Architecture Mapping for Spec 10

| Framework | Core Responsibility in Native Mobile | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | `@supabase/supabase-js` using `expo-secure-store`; biometrics unlock; atomic in-app account deletion via `execute_dsr_erasure()`. | Hardware Keychain token storage; complete user purging meets Apple Guideline 5.1.1. |
| **2. Google Cloud Platform (GCP)** | Cloud Armor WAF rate-limiting; Cloud Run HTTP/2 SSE streaming to mobile; Firebase Cloud Messaging (FCM) push alerts. | Edge DDoS protection and Indian geofencing; power-efficient push notifications without persistent sockets. |
| **3. Google ADK 2.0** | Streams tokens and tool confirmation requests to mobile; manages session event checkpoints for offline recovery. | Event-based state allows resuming interrupted mobile streams cleanly. |
| **4. assistant-ui** | `@assistant-ui/react-native` providing native `ThreadPrimitive`, `ComposerPrimitive`, and `ActionBarPrimitive` with Report action. | Smooth 60fps native gestures; direct compliance with Apple Guideline 1.2 AI safety reporting. |
| **5. Agentgateway 1.5.x** | Mobile session proxy evaluating CEL authorization; multiplexes SSE streams; shields upstream MCP tools. | Low memory/bandwidth overhead; enforces parameter sanitization (CVE-2026-29791) on mobile tool calls. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/mobile/`
  * `app/`: Expo Router screens:
    * `(tabs)/chat.tsx`: Main chat screen powered by `@assistant-ui/react-native` and `useAdkRuntime`.
    * `(tabs)/settings.tsx`: Account info, biometric toggle, and DPDP privacy portal.
    * `artifact/[id].tsx`: Sandboxed `WebView` artifact viewer.
  * `components/`:
    * `chat/mobile-action-bar.tsx`: Custom assistant-ui `ActionBarPrimitive` embedding Apple Guideline 1.2 **[Flag / Report AI Output]** action.
    * `chat/mobile-approval-card.tsx`: Native mobile HITL confirmation card using `useAdkToolConfirmations()`.
    * `report-modal.tsx`: Content reporting dialog (inaccurate, offensive, sensitive data leak).
  * `services/`:
    * `supabase.ts`: Supabase client configured with `expo-secure-store` for session persistence:
      ```typescript
      import { createClient } from '@supabase/supabase-js';
      import * as SecureStore from 'expo-secure-store';

      export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        auth: {
          storage: {
            getItem: (key) => SecureStore.getItemAsync(key),
            setItem: (key, value) => SecureStore.setItemAsync(key, value),
            removeItem: (key) => SecureStore.deleteItemAsync(key),
          },
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: false,
        },
      });
      ```
    * `biometrics.ts`: Face ID / Fingerprint gate via `expo-local-authentication`.
    * `offline_cache.ts`: Local conversation storage via `expo-sqlite`.
    * `push_notifications.ts`: Google Firebase Cloud Messaging / Expo Push client handling approval alerts.
* `apps/mobile/app.json`: Configured with Privacy Manifests, permissions, and 17+ Content Rating flags.

---

## 4. Requirements & Implementation Details

### R10.1: Mandatory App Store AI Safety Controls

#### 1. In-App Flag/Report Response (Apple Guideline 1.2 & Google Play Policy)
- Built directly into assistant-ui's native mobile `ActionBarPrimitive` on every message:
  ```tsx
  <ActionBarPrimitive.Root style={styles.actionBar}>
    <ActionBarPrimitive.Copy />
    <ActionBarPrimitive.Reload />
    <ActionBarPrimitive.CustomAction 
      icon="flag" 
      onPress={handleReportContent}
      accessibilityLabel="Report Objectionable AI Content"
    />
  </ActionBarPrimitive.Root>
  ```
- Tapping the flag button opens `report-modal.tsx` offering options:
  - *Inaccurate or Hallucination*
  - *Offensive / Inappropriate Content*
  - *Sensitive Data / Privacy Concern*
  - *Other*
- Submissions insert directly into `public.content_reports` in Supabase Postgres and trigger immediate internal alerts via Google Cloud Logging.

#### 2. Reviewer Sandbox Mode (Apple Guideline 2.1)
- The login screen includes a hidden/debug trigger (or dedicated review credentials: `apple-reviewer@workkbot.in`) that:
  - Bypasses corporate SSO/MFA.
  - Connects to an isolated demo workspace with sandbox tools.
  - Included in App Store Connect **Review Notes** to guarantee Apple reviewers can test the app immediately without login failures.

#### 3. In-App Account & Data Deletion (Apple Guideline 5.1.1)
- Settings screen contains a dedicated button: **"Delete Account & Reset AI Memory"**.
- Tapping it:
  1. Invokes the backend DPDP DSR erasure RPC (`execute_dsr_erasure`) to purge the employee's chat logs, Vault tokens, and `pgvector` memory embeddings.
  2. Calls `supabase.auth.admin.deleteUser()` to remove the user account completely.
  3. Wipes the local SQLite cache and calls `supabase.auth.signOut()`.
  4. Satisfies Apple App Store Guideline 5.1.1 requirement that account deletion must be executable in-app without requiring email or external support.

#### 4. Sandboxed Artifacts (Apple Guideline 2.5.2)
- Generated HTML, JS, or charts render exclusively inside a dedicated `react-native-webview` pointing to `https://artifacts.workkbot.in` via V4 Signed URLs.
- The webview has zero access to native device storage, bridge APIs, or system credentials.

#### 5. Privacy Manifest (`PrivacyInfo.xcprivacy`) & Age Rating (17+)
- `app.json` includes the required-reasons declarations for `NSPrivacyAccessedAPITypes` (disk space, timestamps, user defaults).
- App Store Connect Content Questionnaire is marked **17+ (or Unrestricted Web Access)** to acknowledge open-ended LLM text generation.

### R10.2: Mobile-First Productivity & Cloud Armor Edge Defense
1. **Google Cloud Armor Rate Limiting**: The Cloud Run mobile API endpoint is protected by Cloud Armor rules mitigating credential stuffing and DDoS attacks.
2. **Biometric Unlock**: Once authenticated, returning users unlock the app via Face ID or Fingerprint (`expo-local-authentication`), avoiding repetitive SSO redirects.
3. **Offline Local Cache (`expo-sqlite`)**: The last 20 conversations are cached locally. Messages typed while offline are queued with a visible "Pending Send" indicator and dispatch automatically on reconnection.
4. **Push Notifications for HITL Approvals**: Long-running research tasks or pending tool confirmation requests trigger an in-app push notification via Firebase Cloud Messaging. Tapping the notification takes the user directly to the confirmation card.

---

## 5. Validation Scorecard & Execution Target

### **Execution Target**: `Production Cloud Run Mandatory`
- **Environment**: React Native (Expo SDK 52) on iOS/Android device/simulator communicating with **live Cloud Run multi-container pod in Mumbai (`asia-south1`)**.
- **Why Cloud Run is Mandatory**:
  - **Google Cloud Armor WAF**: Enforces Indian geofencing (`origin.region_code == 'IN'`) and edge rate-limiting at the Google Cloud HTTPS Load Balancer. Cannot be validated on localhost.
  - **Direct VPC Egress**: Enforces metadata firewall rule dropping `169.254.169.254/32`.
  - **Apple App Store Reviewer Submission**: Apple review team tests against live, public HTTPS endpoints (`https://api.workkbot.in`) using pre-provisioned Reviewer Demo credentials (`apple-reviewer@workkbot.in`).

---

### **Tier 1: Unit & Contract Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-10.1** | `npx expo prebuild --clean` generates valid `PrivacyInfo.xcprivacy` with zero missing API declarations | `cd apps/mobile && npx expo prebuild --clean` | [ ] |
| **VAL-10.2** | Offline SQLite queue schema initializes tables for messages, conversations, and sync state | `pnpm --filter @workkbot/mobile test tests/unit/sqlite-queue.test.ts` | [ ] |
| **VAL-10.3** | Sandboxed WebView component strips native JavaScript bridge and restricts origins (Apple 2.5.2) | `pnpm --filter @workkbot/mobile test tests/unit/artifact-webview.test.ts` | [ ] |

### **Tier 2: Zero-Mock Live Integration Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-10.4** | Cloud Armor WAF permits Indian IP traffic and rejects simulated non-Indian IP probes | `uv run pytest -m live_cloud_armor apps/backend/tests/test_cloud_armor_waf.py` | [ ] |
| **VAL-10.5** | Mobile Reviewer Login (`POST /api/v1/auth/reviewer-login`) returns valid JWT and binds demo tenant | `curl -f -X POST https://$PRODUCTION_BACKEND_URL/api/v1/auth/reviewer-login -d '{"email":"apple-reviewer@workkbot.in","password":"ReviewerDemo2026!Secured"}'` | [ ] |
| **VAL-10.6** | In-app mobile account deletion calls `/api/v1/account/delete`, purges local SQLite, and resets state | `uv run pytest apps/backend/tests/test_mobile_account_deletion.py` | [ ] |

### **Tier 3: UI & Front-End E2E Tests (Automated)**
| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-10.7** | Long-pressing any assistant bubble renders native Action Sheet with **[Report Response]** (Apple 1.2) | `pnpm --filter @workkbot/mobile test:e2e tests/e2e/message-report-action.spec.ts` | [ ] |
| **VAL-10.8** | Biometric unlock prompt (`expo-local-authentication`) gates app launch when resumed | `pnpm --filter @workkbot/mobile test:e2e tests/e2e/biometric-gate.spec.ts` | [ ] |
| **VAL-10.9** | Floating mobile composer renders native bottom sheet `+` menu with all 8 action items | `pnpm --filter @workkbot/mobile test:e2e tests/e2e/mobile-composer.spec.ts` | [ ] |

### **Tier 4: Manual Verification Protocol (Apple Reviewer Walkthrough)**
1. **App Store Reviewer Mode**: On a physical iOS device / TestFlight, launch Workkbot. Tap **"Reviewer Sandbox Login"**. Confirm instantaneous login into the isolated demo organization without Google SSO or SMS OTP (Apple Guideline 2.1).
2. **AI Content Moderation (Apple 1.2)**: Send a prompt. When the AI responds, long-press the chat bubble. Tap **"Report AI Response"**. Select reason "Sensitive PII", add comment, tap Submit. Confirm report confirmation toast appears.
3. **Airplane Mode Offline Queue**: Toggle Airplane Mode ON (disconnect WiFi and Cellular). Type: *"Draft a memo to the operations team"*. Tap Send. Confirm the message renders with a grey clock icon and **"Pending Send"** status pill. Toggle Airplane Mode OFF. Confirm message automatically transitions to "Sent" and AI streaming commences.
4. **Complete In-App Account & Cache Erasure (Apple 5.1.1)**: Open mobile Settings -> tap **[Delete Account & Purge Memory]**. Confirm alert. Verify local SQLite database is dropped, auth tokens in Keychain/SecureStore are purged, and app resets to unauthenticated login screen.

