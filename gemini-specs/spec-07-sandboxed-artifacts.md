# Spec 07: Sandboxed Code Artifacts & Supabase Storage Persistence

## 1. Context & Motivation
Generative Artifacts (data analysis charts, interactive dashboards, generated documents, and scripts) differentiate an enterprise assistant from a simple chatbot. 
However, running untrusted LLM-generated code and rendering dynamic HTML creates massive security risks.
This spec introduces **hardware-isolated code execution** via E2B microVMs (with a local Docker fallback for cost-sensitive Indian SMBs), **persistence via Supabase Storage**, and **isolated-origin rendering**.

## 2. Objective & Non-Goals
- **Objective**: The assistant can write and execute code in short-lived sandboxes, commit generated outputs through ADK’s Artifact Service into **Supabase Storage**, and render interactive outputs inside a secure, origin-isolated iframe or mobile WebView.
- **Non-Goals**: No code execution in the primary application container. Sandboxes never have access to production databases or app cookies.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/artifacts/`
  * `sandbox_manager.py`: Pluggable execution manager supporting E2B Firecracker microVMs or local Docker/gVisor runner.
  * `tool_execute_code.py`: ADK `FunctionTool` invoking the sandbox environment.
  * `supabase_artifact_service.py`: Backs Google ADK's Artifact Service with Supabase Storage.
* `supabase/migrations/20260927000007_artifacts_storage.sql`:
  * Creates `artifacts` bucket in Supabase Storage with RLS enabled.
  * `public.artifacts_metadata` table (`id`, `org_id`, `user_id`, `storage_path`, `content_type`, `created_at`).
* `apps/web/src/app/artifacts/[id]/`: Isolated-origin rendering route deployed on a separate subdomain (`artifacts.company.in`).
* `apps/mobile/src/components/artifact-viewer.tsx`: In-app sandboxed `WebView` component.

---

## 4. Requirements & Implementation Details

### R07.1: Pluggable Sandbox Engine
- **Primary (Cloud)**: E2B Firecracker microVMs (`e2b-code-interpreter`). Dedicated Linux kernel per session, ~125ms cold boot.
- **SMB Fallback (Cost & On-Premises)**: Local containerized runner using Docker with `--network=none`, `seccomp` profiles, and memory/CPU limits.
- **Lifecycle**: Destroyed immediately after execution completes or after a 3-minute idle timeout.

### R07.2: Supabase Storage Persistence
- When code execution produces a file, chart, or interactive mini-app:
  - The output bytes are committed to the `artifacts` bucket in **Supabase Storage** via `supabase_artifact_service.py`.
  - Path structure: `artifacts/{org_id}/{user_id}/{artifact_id}.html`.
  - The client receives a time-limited signed URL (`expiresIn = 900` seconds / 15 minutes):
    ```python
    signed_url_res = supabase.storage.from_("artifacts").create_signed_url(
        path=f"{org_id}/{user_id}/{artifact_id}.html",
        expires_in=900
    )
    ```
- RLS Policies on Supabase Storage ensure only users within the same organization can generate or read signed URLs.

### R07.3: Isolated-Origin Rendering Contract
- **Web Isolation**:
  - Artifacts load inside an `<iframe>` served from a separate subdomain (e.g. `https://artifacts.workkbot.app`).
  - Strict Content Security Policy (CSP):
    ```http
    Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:;
    ```
  - Sandbox flags: `sandbox="allow-scripts"`. The iframe cannot read `parent.document`, access host cookies, or make authenticated API calls with the user's session.
- **Mobile Isolation**:
  - Expo uses `react-native-webview` with `originWhitelist={['https://artifacts.workkbot.app']}` and `javaScriptEnabled={true}`, isolating execution from native device APIs.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Method / Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-07.1** | Executed script cannot access host filesystem, environment variables, or private network | Security test script attempting outbound network and env read | [ ] |
| **VAL-07.2** | Sandbox container is destroyed within 180 seconds of completion | Monitor active container / sandbox count | [ ] |
| **VAL-07.3** | Generated artifact uploaded to Supabase Storage and returns valid signed URL | Test artifact execution and verify file in Supabase Storage | [ ] |
| **VAL-07.4** | Expired Supabase signed URL returns HTTP 403 Forbidden | Test GET request with expired signature | [ ] |
| **VAL-07.5** | Artifact iframe cannot access parent window's `localStorage` or auth cookies | Automated browser test attempting cross-origin DOM read | [ ] |
