# Sovereign Enterprise AI Assistant: Mission Constitution

## 1. Vision & Purpose
The Sovereign Enterprise AI Assistant is an enterprise-grade, client-facing conversational intelligence system engineered for security-conscious Indian enterprises (BFSI, Healthcare, Legal, and Enterprise B2B). It provides conversational automation, deep enterprise knowledge retrieval, and on-demand integration with enterprise productivity suites—specifically **Google Workspace** (Gmail, Drive, Docs, Sheets, Calendar) and **Zoho Suite** (Zoho CRM, Zoho Mail, Zoho Desk, Zoho Analytics via `mcp.zoho.com`)—using the open **Model Context Protocol (MCP)**, while guaranteeing strict digital sovereignty and regulatory compliance under Indian jurisprudence.

---

## 2. Target Audience & Enterprise Persona
- **Enterprises Operating in India**: Organizations subject to statutory data localization and privacy mandates.
- **Enterprise Employees & Clients (Data Principals)**: Users interacting with corporate systems via mobile and web interfaces requiring high-trust AI collaboration.
- **Data Protection Officers (DPOs) & Chief Information Security Officers (CISOs)**: Internal auditors requiring auditable proof of consent, zero data retention, and rapid execution of Data Principal Rights.

---

## 3. Core Mandates & Regulatory Anchors

### A. Digital Personal Data Protection (DPDP) Act, 2023 Compliance (Day 1 / Block 1)
1. **Notice & Itemised Consent (Sections 5 & 6)**:
   - No data processing or LLM inference may proceed without explicit, unbundled, granular, timestamped, and logged consent records.
   - Independent consent gates for core conversational processing (`CORE_CHAT`), Google Workspace tools (`WORKSPACE_INTEGRATION`), and Zoho Suite (`ZOHO_INTEGRATION`).
2. **Consent Withdrawal (Section 6(4))**:
   - One-tap revocation mechanism instantly terminates active agent pipelines and unlinks third-party OAuth access tokens across Workspace and Zoho.
3. **Storage Limitation & Erasure (Section 8(7))**:
   - Automated 90-day time-to-live (TTL) on all chat logs and conversational session state, enforced at the database layer.
4. **Security Safeguards (Section 8(5))**:
   - Hardware-backed keystores (`expo-secure-store`) on mobile for credentials; support for FIDO2/biometric Passkeys and enterprise SSO via Google Cloud Identity Platform.
   - In-flight memory masking of sensitive Indian identifiers aligned with Google Cloud Sensitive Data Protection infoTypes (`INDIA_AADHAAR_NUMBER`, `INDIA_PAN_INDIVIDUAL`, `INDIA_GST_INDIVIDUAL`, `PHONE_NUMBER`, `EMAIL_ADDRESS`) before prompts leave application memory.
   - Encrypted token storage using PostgreSQL `pgcrypto` with sovereign customer-managed keys (CMEK) via Google Cloud KMS in `asia-south1`.
5. **Data Principal Rights (Sections 11–14)**:
   - **Right to Access (Section 11)**: Native self-service data export delivering machine-readable JSON of all stored data.
   - **Right to Correction & Erasure ("Forget Me", Section 12)**: Cascading zero-trace purge across databases, vector stores, session indices, and tool tokens.
   - **Right of Grievance Redressal (Section 13)**: Integrated redressal channel detailing the designated Data Protection Officer.

### B. CERT-In Cybersecurity Directives & Infrastructure Shield
- Append-only, tamper-resistant audit logs (`audit_logs`) recording user ID, action timestamps synchronized to Indian Standard Time (IST) / NTP, tool invocations, and execution status.
- Edge perimeter security via Google Cloud Armor WAF and Serverless NEG in `asia-south1`, enforcing OWASP protection and India-only IP geofencing where mandated.

---

## 4. Inviolable Non-Goals
1. **No Global Multi-Region Fallback**: Under no circumstances shall network routing failover to regions outside `asia-south1` (Mumbai). If `asia-south1` is unreachable, the system must fail closed with an explicit sovereignty error.
2. **No Unsolicited Ingestion**: The assistant must never proactively crawl, index, or scan Google Drive, Gmail, Calendar, or Zoho CRM/Mail records without explicit user invocation and tool-level consent.
3. **No Model Training on Enterprise Data**: All LLM inference operates under Zero Data Retention (ZDR); customer prompts and responses are never retained for model tuning or evaluation by Google Cloud.
4. **No Autonomous Write Actions**: Destructive or outbound actions (`send_email`, `create_calendar_event`, `create_crm_deal`) must never execute autonomously without Human-in-the-Loop (HITL) confirmation cards.
