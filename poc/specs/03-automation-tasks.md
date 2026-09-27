# Workkbot Local Proof of Concept (PoC) Specification: 10 Cross-Platform Automation Tasks

This document defines the 10 production-grade cross-platform automation tasks bridging **Google Workspace** and **Zoho Suite**, orchestrated via the **Google ADK 2.0** agent runner with in-process **Presidio PII shielding** and **Human-In-The-Loop (HITL)** approvals.

---

## 1. Automation Task Catalog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               10 Google Workspace ⇄ Zoho Suite Automation Tasks            │
├─────┬──────────────────────────────────────┬─────────────┬──────────────────┤
│ ID  │ Task Title                           │ Direction   │ HITL Write Gate  │
├─────┼──────────────────────────────────────┼─────────────┼──────────────────┤
│ T01 │ Lead Ingestion & Qualification       │ Google→Zoho │ Approve CRM Lead │
│ T02 │ Pre-Meeting Deal Dossier             │ Zoho→Google │ Auto (Read-only) │
│ T03 │ Overdue Invoice Chaser               │ Zoho→Google │ Approve Email    │
│ T04 │ Contract Execution & Deal Closure    │ Google→Zoho │ Approve Deal Win │
│ T05 │ Support Escalation Bridge            │ Google→Zoho │ Approve Ticket   │
│ T06 │ Customer Financial Health Sync       │ Zoho→Google │ Approve Doc Sync │
│ T07 │ Client Onboarding Workspace Setup    │ Zoho→Google │ Approve Folders  │
│ T08 │ Post-Meeting Minutes & CRM Action    │ Google→Zoho │ Approve CRM Log  │
│ T09 │ Receipt Extraction & Expense Booking │ Google→Zoho │ Approve Expense  │
│ T10 │ Weekly Executive Revenue Digest      │ Zoho→Google │ Approve Digest   │
└─────┴──────────────────────────────────────┴─────────────┴──────────────────┘
```

---

## 2. Detailed Task Workflows

### Task 1: Inbound Lead Ingestion & CRM Creation
- **Trigger**: New customer inquiry email received in Gmail (e.g. `subject: "Inquiry for Enterprise Advisory"`).
- **Tool Sequence**:
  1. `gmail_search(query="is:unread label:inbox Enterprise Advisory")`
  2. `gmail_read_thread(thread_id)`
  3. Extract contact info, company name, requirements, and budget.
  4. Presidio PII check on lead details.
  5. **HITL Gate**: Present proposed Lead card to user for approval.
  6. `zoho_crm_create_lead(...)`
  7. `gmail_send_message(to=lead_email, subject="Thanks for reaching out", ...)`

### Task 2: Pre-Meeting Client Dossier Generator
- **Trigger**: Upcoming client meeting on Google Calendar within the next 24 hours.
- **Tool Sequence**:
  1. `calendar_list_events(time_min=now, time_max=now+24h)`
  2. Parse client domain/email from attendees list.
  3. `zoho_crm_search(module="Deals", query=client_name)`
  4. `zoho_books_get_customer_balance(customer_id=client_id)`
  5. Synthesize background dossier (open deals, past interactions, unpaid dues, talking points).
  6. `drive_upload_file(name="Briefing_Dossier_{Client}.md", ...)`

### Task 3: Overdue Invoice Chaser with Personalized Dunning
- **Trigger**: Periodic receivables check or manual trigger for overdue payments.
- **Tool Sequence**:
  1. `zoho_books_get_unpaid_invoices(min_days_overdue=7)`
  2. Retrieve primary billing contact email and invoice aging bracket (e.g. 15 days, 30 days).
  3. Presidio anonymizes amounts and bank details before model drafting.
  4. LLM composes polite, professional payment reminder tailored to the client's tier.
  5. **HITL Gate**: User reviews drafted email body, recipient, and invoice summary.
  6. `gmail_send_message(to=client_email, subject="Follow-up: Invoice #{number}", body=draft)`

### Task 4: Contract Execution & Deal Closure
- **Trigger**: Executed PDF agreement (e.g. `Client_Signed_Master_Agreement.pdf`) detected in Google Drive folder.
- **Tool Sequence**:
  1. `drive_search(query="name contains 'Signed' and mimeType='application/pdf'")`
  2. `drive_read_file(file_id)` -> Extract agreement value, start date, and client entity name.
  3. `zoho_crm_search(module="Deals", query=client_name)`
  4. **HITL Gate**: Prompt user to verify contract details and approve closing the deal.
  5. `zoho_crm_update_deal(deal_id, stage="Closed Won", amount=contract_value)`
  6. `zoho_books_create_invoice(customer_id, items=[first_milestone], ...)`

### Task 5: High-Priority Support Escalation Bridge
- **Trigger**: Incoming email containing urgent distress keywords (e.g. `subject: "URGENT: Production Outage"`).
- **Tool Sequence**:
  1. `gmail_search(query="is:unread (urgent OR critical OR outage)")`
  2. `gmail_read_thread(thread_id)`
  3. `zoho_crm_search(module="Contacts", query=sender_email)` to check SLA tier (e.g. Gold / Enterprise).
  4. **HITL Gate**: Prompt user to approve filing emergency ticket and booking engineering call.
  5. `zoho_desk_create_ticket(subject, description, priority="High")`
  6. `calendar_create_event(summary="P0 Escalation Triage: {Client}", start_time=now+30m, attendees=[team])`

### Task 6: Customer Financial Health & Receivables Sync
- **Trigger**: Monthly financial reconciliation or executive review request.
- **Tool Sequence**:
  1. `zoho_books_get_unpaid_invoices()`
  2. Aggregate receivables by client, calculate DSO (Days Sales Outstanding) and overdue aging.
  3. Fetch active deals in `zoho_crm_search(module="Deals", query="stage=Pipeline")`.
  4. **HITL Gate**: User reviews compiled financial summary table.
  5. `drive_upload_file(name="Monthly_Client_Financial_Health_Report.md", content=table)`

### Task 7: Client Onboarding Workspace Provisioner
- **Trigger**: New account closed or added in Zoho CRM.
- **Tool Sequence**:
  1. `zoho_crm_search(module="Accounts", query="status='New Customer'")`
  2. Retrieve company name, primary stakeholder, and contract scope.
  3. **HITL Gate**: User confirms provisioning client drive structure and kickoff event.
  4. `drive_upload_file(name="01_Contracts_and_Compliance/README.txt", ...)`
  5. `drive_upload_file(name="02_Deliverables_and_Reports/README.txt", ...)`
  6. `calendar_create_event(summary="Project Kickoff: {Company}", start_time=next_monday, ...)`

### Task 8: Post-Meeting Minutes & CRM Action Sync
- **Trigger**: Completed meeting transcript or audio notes file saved to Google Drive.
- **Tool Sequence**:
  1. `drive_search(query="name contains 'Meeting_Notes' or name contains 'Transcript'")`
  2. `drive_read_file(file_id)`
  3. Extract discussion summary, agreed milestones, and action items with owners.
  4. `zoho_crm_search(module="Deals", query=meeting_client)`
  5. **HITL Gate**: User approves CRM deal log and scheduled action item dates.
  6. `zoho_crm_update_deal(deal_id, notes="Meeting Summary: {summary}")`
  7. `calendar_create_event(summary="Action Item Follow-up: {Item}", start_time=due_date)`

### Task 9: Receipt OCR & Expense Entry
- **Trigger**: Uploaded vendor bill or receipt PDF in Google Drive (`Drive/Receipts`).
- **Tool Sequence**:
  1. `drive_search(query="'Receipts' in parents and mimeType='application/pdf'")`
  2. `drive_read_file(file_id)` -> Extract Vendor Name, Amount in INR, GSTIN, Invoice Date.
  3. Presidio verifies GSTIN format (`\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}`).
  4. **HITL Gate**: User inspects extracted receipt data and confirms expense booking.
  5. `zoho_books_record_expense(vendor_name, amount, gstin, category="Office & Advisory")`

### Task 10: Weekly Executive Revenue & Pipeline Digest
- **Trigger**: Weekly scheduled briefing or Monday morning executive request.
- **Tool Sequence**:
  1. `zoho_crm_search(module="Deals", query="stage != 'Closed Lost'")` -> Compute total weighted pipeline.
  2. `zoho_books_get_unpaid_invoices()` -> Calculate pending cash collections for the week.
  3. Synthesize executive memo highlighting top 3 risks, expected closures, and overdue collections.
  4. **HITL Gate**: Executive reviews digest before dispatching to management.
  5. `gmail_send_message(to="partners@firm.in", subject="Weekly Executive Business Digest", body=digest)`
  6. `drive_upload_file(name="Executive_Digest_{Date}.md", content=digest)`
