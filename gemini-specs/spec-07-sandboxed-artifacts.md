# Spec 07: Sandboxed Code Artifacts & Google Cloud Storage Persistence (GCP Day 1)

## 1. Context & Motivation
Generative Artifacts (data analysis charts, interactive dashboards, generated documents, and scripts) differentiate an enterprise assistant from a simple chatbot. 
However, running untrusted LLM-generated code and rendering dynamic HTML creates massive security risks. Furthermore, trusting filenames returned by sandboxes creates severe **Arbitrary File Write / RCE vulnerabilities (as identified in LibreChat CVE-2026-34371)** where attackers used `../../` path traversal to overwrite host application files.
This spec introduces **hardware-isolated code execution** via E2B microVMs (with a local Docker fallback for cost-sensitive Indian SMBs), **strict filename sanitization**, **persistence via Google Cloud Storage (GCS in `asia-south1`)**, and **isolated-origin rendering** with strict Content Security Policies.

## 2. Objective & Non-Goals
- **Objective**: The assistant can write and execute code in short-lived sandboxes, commit generated outputs through ADK’s Artifact Service into **Google Cloud Storage (GCS)** with strict path traversal sanitization, and render interactive outputs inside a secure, origin-isolated iframe or mobile WebView using V4 Signed URLs.
- **Non-Goals**: No code execution in the primary application container. Sandboxes never have access to production databases or app cookies.

---

## 3. Architecture & File Modifications

### Files to Create:
* `apps/backend/src/artifacts/`
  * `sandbox_manager.py`: Pluggable execution manager supporting E2B Firecracker microVMs or local Docker/gVisor runner.
  * `path_sanitizer.py`: Strict filename and path validator blocking directory traversal sequences (`../`, `/`) mitigating CVE-2026-34371.
  * `tool_execute_code.py`: ADK `FunctionTool` invoking the sandbox environment.
  * `gcs_artifact_service.py`: Backs Google ADK's Artifact Service with Google Cloud Storage (`google-cloud-storage`).
* `supabase/migrations/20260927000007_artifacts_metadata.sql`:
  * `public.artifacts_metadata` table (`id`, `org_id`, `user_id`, `storage_path`, `content_type`, `created_at`) with RLS.
* `apps/web/src/app/artifacts/[id]/`: Isolated-origin rendering route deployed on a separate subdomain (`artifacts.workkbot.in`).
* `apps/mobile/src/components/artifact-viewer.tsx`: In-app sandboxed `WebView` component.

---

## 4. Requirements & Implementation Details

### R07.1: Pluggable Sandbox Engine
- **Primary (Cloud)**: E2B Firecracker microVMs (`e2b-code-interpreter`). Dedicated Linux kernel per session, ~125ms cold boot.
- **SMB Fallback (Cost & On-Premises)**: Local containerized runner using Docker with `--network=none`, `seccomp` profiles, and memory/CPU limits.
- **Lifecycle**: Destroyed immediately after execution completes or after a 3-minute idle timeout.

### R07.2: Google Cloud Storage (GCS) Persistence in Mumbai (`asia-south1`)
- When code execution produces a file, chart, or interactive mini-app:
  - The output bytes are committed to the `workkbot-artifacts-$PROJECT_ID` bucket in **Google Cloud Storage** via `gcs_artifact_service.py`.
  - Path structure: `artifacts/{org_id}/{user_id}/{artifact_id}.html`.
  - The client receives a time-limited **V4 Signed URL** (`expires = 900` seconds / 15 minutes):
    ```python
    blob = bucket.blob(f"{org_id}/{user_id}/{artifact_id}.html")
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=15),
        method="GET"
    )
    ```
- Uniform Bucket-Level Access and IAM roles guarantee strict multi-tenant authorization.

### R07.3: Isolated-Origin Rendering Contract
- **Web Isolation**:
  - Artifacts load inside an `<iframe>` served from a separate subdomain (e.g. `https://artifacts.workkbot.in`).
  - Strict Content Security Policy (CSP):
    ```http
    Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:;
    ```
  - Sandbox flags: `sandbox="allow-scripts"`. The iframe cannot read `parent.document`, access host cookies, or make authenticated API calls with the user's session.
- **Mobile Isolation**:
  - Expo uses `react-native-webview` with `originWhitelist={['https://artifacts.workkbot.in']}` and `javaScriptEnabled={true}`, isolating execution from native device APIs.

### R07.4: Strict Filename Sanitization & Anti-Traversal (CVE-2026-34371)
- `path_sanitizer.py` validates all output metadata returned from the sandbox before saving to GCS or disk:
  - Strips any path separators (`/`, `\`) and traversal tokens (`..`).
  - Whitelists filename characters: `re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)`.
  - Enforces safe extension allowlist (`.html`, `.svg`, `.json`, `.csv`, `.png`, `.pdf`).
  - Blocks any attempt to write outside the scoped GCS prefix or into the host filesystem.

---

## 5. Validation Scorecard

| Check ID | Verification Criteria | Test Command | Pass/Fail |
|:---:|---|---|:---:|
| **VAL-07.1** | Executed script cannot access host filesystem, environment variables, or private network | `pytest apps/backend/tests/test_sandbox_security.py` | [ ] |
| **VAL-07.2** | Sandbox container is destroyed within 180 seconds of completion | `pytest apps/backend/tests/test_sandbox_lifecycle.py` | [ ] |
| **VAL-07.3** | Generated artifact uploaded to GCS and returns valid V4 signed URL | `pytest apps/backend/tests/test_gcs_signed_urls.py` | [ ] |
| **VAL-07.4** | Expired GCS V4 signed URL returns HTTP 403 Forbidden | `pytest apps/backend/tests/test_signed_url_expiry.py` | [ ] |
| **VAL-07.5** | Artifact iframe cannot access parent window's `localStorage` or auth cookies | `pnpm --filter web test:e2e tests/e2e/artifact-sandbox.spec.ts` | [ ] |
| **VAL-07.6** | Filenames with path traversal (`../../app/server.js`) are safely sanitized (CVE-2026-34371) | `pytest apps/backend/tests/test_path_sanitizer.py` | [ ] |
