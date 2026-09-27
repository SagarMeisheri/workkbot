# Spec 06: Native Mobile App (React Native / Expo)

## 1. Context & Motivation
By this point `api`'s contract is proven across web usage covering chat, tools, HITL, memory, Artifacts, and skills. This spec builds the native mobile client against that already-stable contract — deliberately last, since building it earlier would mean building against a moving target.

## 2. Objective & Non-Goals
- **Objective**: A React Native (Expo) app offering feature parity with the web chat experience — auth, streaming chat, tool-call visibility, HITL approval notifications, memory panel, and sandboxed Artifact rendering — with offline resilience and push notifications for long-running tasks.
- **Non-Goals**: No mobile-only features not present on web. No fully native (Swift/Kotlin) rewrite — explicitly out of scope per the constitution unless a future spec documents a capability Expo/RN genuinely cannot deliver.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/mobile/` — Expo-managed React Native app: chat screen, tool-call/artifact timeline items, approvals notification handling, memory panel, settings.
* `apps/mobile/auth/` — `expo-auth-session` OIDC + PKCE flow, `expo-secure-store`-backed token storage, biometric unlock gate.
* `apps/mobile/offline/` — local cache (`expo-sqlite`) of the last N conversations; outbound message queue for send-while-offline.
* `apps/mobile/push/` — Expo push notification registration and handling for "task ready" / "approval needed" notifications.
* `apps/mobile/artifact/` — in-app WebView Artifact renderer, isolated-origin per Spec 04's rendering contract.

### Files to Modify:
* `packages/api-client/` — confirm the typed client generated from `api`'s schema is consumed as-is by `mobile`, with no mobile-specific forked client.
* `packages/shared-types/` — no changes expected if Specs 01–05 kept the contract stable; any gap found here is itself a signal a prior spec's contract wasn't actually complete.

### Files to Delete / Deprecate:
* None.

---

## 4. Requirements & Implementation Details

### R06.1: Auth parity with web
- Standard OIDC authorization-code-with-PKCE flow via `expo-auth-session` against the same IdP as web; tokens stored in `expo-secure-store` (Keychain/Keystore-backed).
- Biometric unlock (Face ID/fingerprint) gates access to a cached session so the user isn't forced through the full IdP flow on every app launch.

### R06.2: Offline resilience
- The last N conversations are cached locally so the app opens instantly without a network round-trip.
- A message sent while offline is queued locally and sent automatically on reconnect, with a visible "pending send" state — never silently dropped.

### R06.3: Push notifications for async work
- HITL approval requests requiring the current user's action, and long-running tool/Artifact jobs completing, trigger a push notification via Expo's push service (APNs/FCM-backed).

### R06.4: Artifact rendering parity
- Artifacts render inside an in-app WebView following the same isolated-origin principle as Spec 04's web iframe — no interactive generated content is ever interpreted as a native RN component.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass / Fail |
|:---:|---|---|:---:|
| **VAL-01** | Login via OIDC+PKCE succeeds on both iOS and Android against the shared IdP | Manual device test, both platforms | [ ] |
| **VAL-02** | Cached tokens are stored via secure, Keychain/Keystore-backed storage, never plain `AsyncStorage` | Code review + static check for disallowed storage APIs | [ ] |
| **VAL-03** | A message composed while offline sends automatically on reconnect without duplication | Manual test: airplane mode, compose, reconnect | [ ] |
| **VAL-04** | A pending HITL approval assigned to the current user triggers a push notification | Integration test against Expo push service (sandbox) | [ ] |
| **VAL-05** | A rendered Artifact in the mobile WebView cannot access the app's stored auth tokens | Security test: attempt token access from inside the WebView context | [ ] |
| **VAL-06** | `mobile` consumes `packages/api-client` unmodified — no forked or duplicated API client logic | Code review / dependency graph check | [ ] |
