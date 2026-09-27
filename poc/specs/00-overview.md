# Workkbot Local Proof of Concept (PoC) Specification: Overview

## 1. Executive Summary

This document specifies the **Workkbot Local Proof of Concept (PoC)** — a standalone, self-contained implementation of the Workkbot compliance-first enterprise assistant.

The PoC validates the core capabilities defined in the primary Workkbot specifications (`specs/features/01-sovereign-session` through `05-hitl-cert-in-launch`) **locally on a developer workstation without requiring AWS cloud infrastructure** (no AWS ECS Fargate, RDS PostgreSQL Graviton3, S3 buckets, Cognito User Pools, or CloudWatch).

### Key PoC Objectives:
1. **Minimal Streamlit Interface**: A unified local UI providing conversational chat with `@workkbot`, a task launcher for automated workflows, client-side OAuth connection management, and a real-time privacy/guardrails inspection monitor.
2. **Google ADK 2.0 Agent Harness**: Agentic orchestration powered by Google ADK 2.0 design patterns (`Runner`, `LlmAgent`, `McpToolset`, `callbacks`, and Human-in-the-Loop approval workflows).
3. **Client-Side Connected OAuth**: Local token management for Google Workspace and Zoho Suite with client-side credential storage and a dual-mode fallback (Live OAuth tokens vs. Built-in Realistic Sandbox).
4. **Model Context Protocol (MCP) Toolsets**: Native MCP tool definitions for Google Workspace (Gmail, Drive, Calendar, Docs/Sheets) and Zoho Suite (CRM, Books, Desk).
5. **10 Cross-Platform Automated Tasks**: Ten pre-configured, production-grade business automations bridging Google Workspace and Zoho Suite with intermediate Human-In-The-Loop (HITL) gates for state-changing actions.
6. **Compliance & Privacy Guardrails**:
   - In-process **Microsoft Presidio PII de-identification** with Indian identifiers (`PAN`, `AADHAAR`, `GSTIN`) and global PII, keeping translation tables strictly in ephemeral memory (`temp:pii_map`).
   - **Indirect Prompt Injection Shield** enclosing MCP outputs in `<untrusted_content>` tags.
   - **Pre-execution Consent Gates** checking granular authorization before tool invocation.

---

## 2. Feature Comparison: Full Enterprise Architecture vs. Local PoC

| Capability | Full Enterprise Architecture (`specs/`) | Local Proof of Concept (`poc/`) |
| :--- | :--- | :--- |
| **User Interface** | Expo React Native (iOS/Android/Web) + WhatsApp + Teams/Slack | Minimal, reactive **Streamlit** Web Application |
| **Agent Harness** | Google ADK 2.0 on ECS Fargate (`google-adk[db]>=2.6.2`) | Local **Google ADK 2.0** agent runner & orchestration engine |
| **Database & State** | Amazon RDS PostgreSQL 16 Graviton3 with forced RLS | Local SQLite / in-memory session state |
| **OAuth Token Storage** | RDS `workspace_tokens` table with `pgcrypto` encryption | Client-side encrypted token vault (`client_vault.py`) in Streamlit session |
| **Google Integration** | `@google/workspace-mcp` via Stdio / Cloud OAuth | Google Workspace MCP Toolset (Live OAuth or Local Sandbox) |
| **Zoho Integration** | `mcp.zoho.com` SSE endpoint with AWS-managed tokens | Zoho Suite MCP Toolset (Live OAuth or Local Sandbox) |
| **PII Anonymization** | Microsoft Presidio Graviton3 container + `temp:pii_map` | In-process Presidio engine with regex fallbacks + `temp:pii_map` |
| **Prompt Shield** | Custom ADK `after_tool_callback` `<untrusted_content>` | Active ADK callback shielding raw MCP responses |
| **HITL Approvals** | LongRunningFunctionTool + WhatsApp interactive cards | Interactive Streamlit approval modal with payload inspection |
| **Cloud Dependencies** | AWS KMS, WAFv2, EventBridge, SQS, CloudWatch | **Zero cloud infrastructure required to execute** |

---

## 3. Directory Structure

```
poc/
├── README.md                      # Quickstart and run instructions
├── pyproject.toml                 # Package definition and dependencies (uv)
├── requirements.txt               # Lightweight Python dependencies (export)
├── .env.example                   # Local configuration template
├── specs/                         # PoC architectural and functional specifications
│   ├── 00-overview.md             # This document
│   ├── 01-architecture-local.md   # Local runtime & component architecture
│   ├── 02-mcp-tools-spec.md       # MCP tool schemas for Google & Zoho
│   └── 03-automation-tasks.md     # 10 Google ⇄ Zoho automation specifications
└── src/                           # Complete runnable implementation
    ├── app.py                     # Streamlit frontend application
    ├── core/                      # Security, privacy, and guardrail modules
    │   ├── config.py              # Configuration & environment loader
    │   ├── presidio_guard.py      # Presidio PII de-identification proxy
    │   ├── injection_shield.py    # MCP untrusted content sanitizer
    │   └── hitl.py                # Human-In-The-Loop gatekeeper
    ├── mcp/                       # Model Context Protocol toolsets
    │   ├── client_vault.py        # Client-side OAuth token manager
    │   ├── google_workspace.py    # Google Workspace MCP tools (Gmail/Drive/Cal)
    │   └── zoho_suite.py          # Zoho Suite MCP tools (CRM/Books/Desk)
    ├── adk/                       # Google ADK 2.0 local orchestration harness
    │   └── agent_harness.py       # LlmAgent, Runner, callbacks, and routing
    └── tasks/                     # 10 Cross-Platform Automation Workflows
        └── registry.py            # Automation task catalog & workflow executors
```
