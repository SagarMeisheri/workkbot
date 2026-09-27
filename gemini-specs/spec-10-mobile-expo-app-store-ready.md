# Spec 10: App-Store-Certified Native Mobile App (Expo SDK 52+ & Cloud Armor) (GCP Day 1)

## 1. Context & Motivation
Submitting an AI assistant app to the Apple App Store and Google Play Store is notorious for high rejection rates.
Common rejection traps include:
- **Apple Guideline 1.2 / Google Play AI Policy**: Missing in-app reporting/flagging for AI responses.
- **Apple Guideline 2.1**: App review team locked out because enterprise SSO MFA blocks them.
- **Apple Guideline 3.2.2**: Enterprise-only apps rejected for general public store distribution.
- **Apple Guideline 5.1.1(v)**: Missing in-app account/data deletion flow.
- **Privacy Manifests**: Missing declarations for required-reason native APIs.

This spec builds the **React Native (Expo SDK 52+)** native mobile app integrated with **`@supabase/supabase-js`**, connected to **Google Cloud Run via Google Cloud Armor in `asia-south1`**, and incorporating **pre-baked App Store compliance**, guaranteeing high approval velocity.

## 2. Objective & Non-Goals
- **Objective**: Deliver a production-ready iOS and Android mobile app offering full chat parity, in-app AI content reporting, in-app account/memory purging, biometric unlock, offline caching, and push notifications for HITL approvals via Firebase Cloud Messaging.
- **Non-Goals**: No consumer public signups. The app is distributed to employees via **Apple Business Manager (Custom Apps)**, **Unlisted App Distribution**, or corporate MDM.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/mobile/`
  * `app/`: Expo Router screens:
    * `(tabs)/chat.tsx`: Main chat screen with token streaming and branch navigator.
    * `(tabs)/settings.tsx`: Account info, biometric toggle, and DPDP privacy portal.
    * `artifact/[id].tsx`: Sandboxed `WebView` artifact viewer.
  * `components/`:
    * `message-bubble.tsx`: Message bubble with **[Flag / Report AI Output]** action.
    * `report-modal.tsx`: Content reporting dialog (inaccurate, offensive, hallucination).
    * `in-chat-approval-card.tsx`: Tier 1 inline HITL confirmation card.
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
- Every assistant message bubble features a visible flag icon or long-press context menu action: **"Report AI Response"**.
- Tapping it opens `report-modal.tsx` offering options:
  - *Inaccurate or Hallucination*
  - *Offensive / Inappropriate Content*
  - *Data / Privacy Concern*
  - *Other*
- Submissions insert directly into `public.content_reports` in Supabase Postgres and trigger immediate internal alerts.

#### 2. Reviewer Sandbox Mode (Apple Guideline 2.1)
- The login screen includes a hidden/debug trigger (or dedicated review credentials: `reviewer@workkbot-demo.internal`) that:
  - Bypasses corporate SSO/MFA.
  - Connects to an isolated demo workspace with simulated tools.
  - Included in App Store Connect **Review Notes** to guarantee Apple reviewers can test the app immediately without login failures.

#### 3. In-App Account & Data Deletion (Apple Guideline 5.1.1(v))
- Settings screen contains a dedicated button: **"Delete Account & Reset AI Memory"**.
- Tapping it:
  1. Invokes the backend DPDP DSR erasure RPC (`execute_dsr_erasure`) to purge the employee's chat logs and `pgvector` memory embeddings.
  2. Wipes the local SQLite cache and calls `supabase.auth.signOut()`.
  3. Displays an explicit notice: *"Your local data and AI memory have been purged. Corporate account deactivation is managed by your workspace administrator."*

#### 4. Privacy Manifest & Age Rating (17+)
- `app.json` includes the required-reasons declarations for `NSPrivacyAccessedAPITypes` (disk space, timestamps, user defaults).
- App Store Connect Content Questionnaire is marked **17+ (or Unrestricted Web Access)** to acknowledge open-ended LLM text generation.

### R10.2: Mobile-First Productivity & Cloud Armor Edge Defense
1. **Google Cloud Armor Rate Limiting**: The Cloud Run mobile API endpoint is protected by Cloud Armor rules mitigating credential stuffing and DDoS attacks.
2. **Biometric Unlock**: Once authenticated, returning users unlock the app via Face ID or Fingerprint (`expo-local-authentication`), avoiding repetitive SSO redirects.
3. **Offline Local Cache (`expo-sqlite`)**: The last 20 conversations are cached locally. Messages typed while offline are queued with a visible "Pending Send" indicator and dispatch automatically on reconnection.
4. **Push Notifications for HITL Approvals**: Long-running research tasks or pending tool confirmation requests trigger an in-app push notification via Firebase Cloud Messaging. Tapping the notification takes the user directly to the confirmation card.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-10.1** | Long-pressing any AI message displays the "Report Response" modal | `pytest apps/backend/tests/test_mobile_report_safety.py` | [ ] |
| **VAL-10.2** | Reviewer credentials log in directly to demo tenant without MFA blocking | `curl -f -X POST https://$BACKEND_URL/api/v1/auth/reviewer-login` | [ ] |
| **VAL-10.3** | "Delete Account & Reset Memory" purges local SQLite cache and executes DSR | `pytest apps/backend/tests/test_mobile_account_deletion.py` | [ ] |
| **VAL-10.4** | Biometric prompt gates app launch when backgrounded and resumed | Manual device test with Face ID enabled | [ ] |
| **VAL-10.5** | Offline message queues properly and dispatches upon reconnecting to WiFi | Airplane mode test: type -> toggle WiFi on -> confirm delivery | [ ] |
| **VAL-10.6** | Expo build generates valid `PrivacyInfo.xcprivacy` with zero missing symbols | `npx expo prebuild --clean` | [ ] |
