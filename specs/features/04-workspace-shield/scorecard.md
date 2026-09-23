# Block 4 Scorecard: Unified MCP Tools (Workspace & Zoho), Gating & Injection Shield

## 1. Verification Rubric & Exit Gates

| Gate ID | Verification Item | Target | Verification Method | Status |
| :--- | :--- | :--- | :--- | :--- |
| **B4-G1** | Multi-Provider Tool Consent Gate | Invocations of Google or Zoho tools without recorded consent return `AUTH_REQUIRED` challenge | Automated unit tests in `backend/tests/test_tool_guards.py` | [ ] PENDING |
| **B4-G2** | Direct Client Token Access Blocked | Direct client queries to `public.workspace_tokens` return 0 rows via Cloud SQL RLS | RLS verification test asserting client denial | [ ] PENDING |
| **B4-G3** | MCP Toolset Discovery & Invocation | ADK `McpToolset` successfully connects to Google Workspace MCP and Zoho MCP mock servers | Integration test in `backend/tests/test_mcp_toolset.py` | [ ] PENDING |
| **B4-G4** | Indirect Prompt Injection Neutralization | Adversarial text in emails or CRM records is safely enclosed in `<untrusted_content>` and ignored by LLM | Prompt injection test in `backend/tests/test_prompt_injection.py` | [ ] PENDING |
| **B4-G5** | Multi-Provider pgcrypto Encryption | Stored tokens for both Google and Zoho are encrypted at rest with `pgcrypto` AES-256 | Database inspection test validating bytea columns | [ ] PENDING |

---

## 2. Automated Test Execution Commands

```bash
# 1. Test before_tool_callback gating for Google and Zoho
cd backend && pytest -v tests/test_tool_guards.py

# 2. Test McpToolset discovery and tool execution
cd backend && pytest -v tests/test_mcp_toolset.py

# 3. Test indirect prompt injection mitigation
cd backend && pytest -v tests/test_prompt_injection.py

# 4. Test multi-provider vault encryption
cd backend && pytest -v tests/test_vault_security.py
```

---

## 3. Exit Criteria Sign-off
Block 4 is considered complete ONLY when all 5 scorecard gates have passed without exception.
