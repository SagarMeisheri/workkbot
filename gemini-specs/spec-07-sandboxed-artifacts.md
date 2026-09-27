# Spec 07: Sandboxed Code Artifacts & Google Cloud Storage (The 5-Framework Model)

## 1. Context & Motivation
Generative Artifacts (data analysis charts, interactive dashboards, generated documents, and scripts) differentiate an enterprise assistant from a simple chatbot. 
However, running untrusted LLM-generated code creates severe host compromise risks. Furthermore, trusting filenames returned by sandboxes creates severe **Arbitrary File Write / RCE vulnerabilities (e.g. CVE-2026-34371)** where attackers used `../../` path traversal to overwrite host files. In addition, **Apple App Store Guideline 2.5.2** strictly governs the execution of code, requiring that all executable scripts run in isolated sandboxes and cannot alter the native binary.

Workkbot eliminates these risks by routing all artifact generation, execution, storage, and rendering through the **5 Core Frameworks**:
1. **Supabase (Mumbai `ap-south-1`)**: Relational metadata registry (`public.artifacts_metadata`) enforcing multi-tenant isolation via RLS.
2. **Google Cloud Platform (GCP `asia-south1`)**: Google Cloud Storage (GCS) in Mumbai with short-lived V4 Signed URLs and Uniform Bucket-Level Access.
3. **Google ADK 2.0 (`google-adk`)**: Artifact Service orchestrating pluggable sandbox execution (E2B microVMs / Docker runner) and `path_sanitizer.py`.
4. **assistant-ui (`@assistant-ui/react`, `@assistant-ui/react-native`)**: Dual-pane split Canvas workspace (`artifact-canvas.tsx`), `useAdkArtifacts()`, `AssistantFrameProvider`, and `CodeDiff`.
5. **Agentgateway 1.5.x**: CEL authorization gating execution access and filtering output payloads against malicious injection.

### **The North Star: Security & Mobile App Approval**
- **Security**: Complete host isolation via microVMs; zero path traversal (CVE-2026-34371); short-lived V4 signed URLs (15-min expiry); strict iframe CSP with isolated origin (`artifacts.workkbot.in`).
- **Mobile App Approval (Apple Guideline 2.5.2 & 4.0)**: Executable code never runs natively on the device; artifacts render strictly inside a sandboxed `react-native-webview` with origin whitelisting, fully adhering to Apple's executable code guidelines.

---

## 2. The 5-Framework Architecture Mapping for Spec 07

| Framework | Core Responsibility in Artifacts | Security & Mobile Approval Guarantee |
|---|---|---|
| **1. Supabase** | `public.artifacts_metadata` table tracking storage paths, content types, and ownership with RLS. | Prevents unauthorized cross-tenant artifact discovery; deletes metadata upon user deletion (Apple 5.1.1). |
| **2. Google Cloud Platform (GCP)** | GCS bucket in `asia-south1` with V4 Signed URLs; isolated subdomain DNS (`artifacts.workkbot.in`). | Data localization in Mumbai; signed URLs enforce cryptographic time-limited access without public exposure. |
| **3. Google ADK 2.0** | Subclasses Artifact Service; invokes E2B microVMs or Docker; executes `path_sanitizer.py`. | Strict path sanitization completely eliminates directory traversal attacks (CVE-2026-34371). |
| **4. assistant-ui** | Dual-pane split Canvas (`artifact-canvas.tsx`), `AssistantFrameProvider`, and `CodeDiff` element. | Smooth responsive side-by-side view on desktop; seamless full-screen mobile `WebView` (Apple 2.5.2). |
| **5. Agentgateway 1.5.x** | CEL authorization verifying permissions before executing code tools; sanitizes returned content. | Restricts code execution capabilities to verified roles; blocks SSRF probes from within sandbox requests. |

---

## 3. Architecture & File Modifications

### Files to Create / Update:
* `apps/backend/src/artifacts/`
  * `sandbox_manager.py`: Pluggable execution manager supporting E2B Firecracker microVMs or local Docker runner.
  * `path_sanitizer.py`: Strict filename and path validator blocking directory traversal sequences (`../`, `/`) mitigating CVE-2026-34371.
  * `tool_execute_code.py`: ADK `FunctionTool` invoking the sandbox environment.
  * `gcs_artifact_service.py`: Backs Google ADK's Artifact Service with Google Cloud Storage (`google-cloud-storage`).
* `supabase/migrations/20260927000007_artifacts_metadata.sql`:
  * `public.artifacts_metadata` table (`id`, `org_id`, `user_id`, `storage_path`, `content_type`, `created_at`) with RLS.
* `apps/web/src/app/artifacts/[id]/`: Isolated-origin rendering route deployed on a separate subdomain (`artifacts.workkbot.in`).
* `apps/web/src/components/chat/artifact-canvas.tsx`: Dual-pane split canvas view utilizing `useAdkArtifacts()` and `AssistantFrameProvider`.
* `apps/web/src/components/assistant-ui/elements/code-diff.tsx`: Versioned code diff viewer element.
* `apps/mobile/src/components/artifact-viewer.tsx`: In-app sandboxed `WebView` component for Expo SDK 52.

---

## 4. Requirements & Implementation Details

### R07.1: Pluggable Sandbox Engine (Google ADK 2.0 Framework)
- **Primary (Cloud)**: E2B Firecracker microVMs (`e2b-code-interpreter`). Dedicated Linux kernel per session, ~125ms cold boot.
- **SMB Fallback (Cost & Local)**: Containerized runner using Docker with `--network=none`, `seccomp` profiles, and memory/CPU limits.
- **Lifecycle**: Destroyed immediately after execution completes or after a 3-minute idle timeout.

### R07.2: Google Cloud Storage (GCS) Persistence in Mumbai (`asia-south1`)
- When code execution produces a file, chart, or interactive mini-app:
  - Output bytes are committed to `workkbot-artifacts-$PROJECT_ID` in **Google Cloud Storage** via `gcs_artifact_service.py`.
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

### R07.3: Isolated-Origin Rendering & Apple 2.5.2 Compliance
- **Web Isolation**:
  - Artifacts load inside an `<iframe>` served from a separate subdomain (`https://artifacts.workkbot.in`).
  - Strict Content Security Policy (CSP):
    ```http
    Content-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:;
    ```
  - Sandbox flags: `sandbox="allow-scripts"`. The iframe cannot read `parent.document`, access host cookies, or make authenticated API calls with the user's session.
- **Mobile Isolation (Apple Guideline 2.5.2)**:
  - Expo mobile app renders artifacts exclusively via `react-native-webview` with `originWhitelist={['https://artifacts.workkbot.in']}` and `javaScriptEnabled={true}`, completely isolating execution from native iOS/Android device APIs.

### R07.4: Strict Filename Sanitization & Anti-Traversal (CVE-2026-34371)
- `path_sanitizer.py` validates all output metadata returned from the sandbox before saving to GCS:
  - Strips any path separators (`/`, `\`) and traversal tokens (`..`).
  - Whitelists filename characters: `re.sub(r'[^a-zA-Z0-9_\-\.]', '', filename)`.
  - Enforces safe extension allowlist (`.html`, `.svg`, `.json`, `.csv`, `.png`, `.pdf`).
  - Blocks any attempt to write outside the scoped GCS prefix or into the host container filesystem.

### R07.5: Assistant-UI Dual-Pane Canvas & Versioned Diffs (assistant-ui Framework)
- When the assistant produces code or an interactive visual artifact:
  - The client leverages `useAdkArtifacts()` from `@assistant-ui/react-google-adk` to track session artifact metadata.
  - The layout transitions into a split Canvas view (`artifact-canvas.tsx`), toggleable via the header action icon `↗` in `ThreadHeader`.
  - For interactive HTML/JS apps, `AssistantFrameProvider` embeds the isolated subdomain iframe with bridge-level postMessage communication.
  - For generated code, scripts, or SQL queries, assistant-ui's `CodeDiff` element renders side-by-side or inline syntax-highlighted diffs across revisions.

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
| **VAL-07.7** | Mobile WebView renders artifacts securely without native bridge exposure (Apple 2.5.2) | `pnpm --filter mobile test:e2e tests/e2e/artifact-webview.spec.ts` | [ ] |
