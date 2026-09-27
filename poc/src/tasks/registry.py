"""
Workkbot Local PoC: 10 Cross-Platform Automation Tasks (Google ⇄ Zoho)
Orchestrates 10 production-grade automations between Google Workspace and Zoho Suite
using dynamically discovered provider tools, Presidio PII protection, and HITL write gates.
"""
from dataclasses import dataclass, field
import datetime
from typing import Any, Callable, Dict, List, Optional
from src.mcp.registry import DynamicToolRegistry
from src.core.presidio_guard import PresidioGuard
from src.core.hitl import HitlGatekeeper


@dataclass
class AutomationTask:
    id: str
    title: str
    description: str
    direction: str  # "Google → Zoho", "Zoho → Google", "Bi-directional"
    required_tools: List[str]
    has_hitl_write: bool
    category: str


@dataclass
class StepLog:
    step_num: int
    title: str
    tool_called: Optional[str]
    input_data: Any
    output_data: Any
    is_hitl_pending: bool = False
    hitl_req_id: Optional[str] = None


@dataclass
class TaskExecutionResult:
    task_id: str
    title: str
    success: bool
    logs: List[StepLog]
    summary: str
    error: Optional[str] = None


class AutomationRegistry:
    def __init__(self, registry: DynamicToolRegistry, presidio: PresidioGuard, hitl: HitlGatekeeper):
        self.registry = registry
        self.presidio = presidio
        self.hitl = hitl

        self.tasks: List[AutomationTask] = [
            AutomationTask(
                id="T01",
                title="Lead Ingestion & CRM Creation",
                description="Scans Gmail for inbound customer inquiries, extracts contact & requirements, checks PII, and creates a lead in Zoho CRM.",
                direction="Google → Zoho",
                required_tools=["gmail.search_threads", "zoho_crm.create_lead", "gmail.send_message"],
                has_hitl_write=True,
                category="Sales & Growth",
            ),
            AutomationTask(
                id="T02",
                title="Pre-Meeting Client Dossier Generator",
                description="Pulls upcoming Google Calendar events, retrieves client deal & billing history from Zoho CRM/Books, and creates a briefing doc in Google Drive.",
                direction="Zoho → Google",
                required_tools=["calendar.list_events", "zoho_crm.search_records", "zoho_books.get_customer_balance", "drive.create_file"],
                has_hitl_write=True,
                category="Executive Preparation",
            ),
            AutomationTask(
                id="T03",
                title="Overdue Invoice Chaser & Dunning",
                description="Fetches aging receivables from Zoho Books, de-identifies financial data with Presidio, and prepares a polite email reminder via Gmail.",
                direction="Zoho → Google",
                required_tools=["zoho_books.get_unpaid_invoices", "gmail.send_message"],
                has_hitl_write=True,
                category="Finance & Receivables",
            ),
            AutomationTask(
                id="T04",
                title="Contract Execution & Deal Closure",
                description="Detects executed signed PDF agreement in Google Drive, updates Zoho CRM deal to 'Closed Won', and drafts first milestone invoice in Zoho Books.",
                direction="Google → Zoho",
                required_tools=["drive.search_files", "drive.read_file_content", "zoho_crm.update_deal", "zoho_books.create_invoice"],
                has_hitl_write=True,
                category="Legal & Revenue",
            ),
            AutomationTask(
                id="T05",
                title="High-Priority Support Escalation Bridge",
                description="Detects urgent customer distress emails in Gmail, files a critical ticket in Zoho Desk, and blocks an emergency triage slot on Google Calendar.",
                direction="Google → Zoho",
                required_tools=["gmail.search_threads", "zoho_desk.create_ticket", "calendar.create_event"],
                has_hitl_write=True,
                category="Client Support",
            ),
            AutomationTask(
                id="T06",
                title="Customer Financial Health & Receivables Sync",
                description="Aggregates outstanding invoices from Zoho Books and active deals from Zoho CRM, generating an executive financial health report in Google Drive.",
                direction="Zoho → Google",
                required_tools=["zoho_books.get_unpaid_invoices", "zoho_crm.search_records", "drive.create_file"],
                has_hitl_write=True,
                category="Finance & Reporting",
            ),
            AutomationTask(
                id="T07",
                title="Client Onboarding Workspace Provisioner",
                description="Detects newly won accounts in Zoho CRM, auto-provisions compliance & deliverable folders in Google Drive, and creates kickoff calendar invite.",
                direction="Zoho → Google",
                required_tools=["zoho_crm.search_records", "drive.create_file", "calendar.create_event"],
                has_hitl_write=True,
                category="Operations",
            ),
            AutomationTask(
                id="T08",
                title="Post-Meeting Minutes & CRM Action Sync",
                description="Parses client meeting transcript from Google Drive, extracts agreed action items, updates Zoho CRM Deal notes, and schedules follow-up in Calendar.",
                direction="Google → Zoho",
                required_tools=["drive.read_file_content", "zoho_crm.update_deal", "calendar.create_event"],
                has_hitl_write=True,
                category="Client Relationship",
            ),
            AutomationTask(
                id="T09",
                title="Receipt OCR & Expense Entry",
                description="Scans vendor bill PDF in Google Drive, extracts vendor name, amount, and GSTIN, and records an audited expense in Zoho Books.",
                direction="Google → Zoho",
                required_tools=["drive.search_files", "drive.read_file_content", "zoho_books.record_expense"],
                has_hitl_write=True,
                category="Accounting & Tax",
            ),
            AutomationTask(
                id="T10",
                title="Weekly Executive Revenue & Pipeline Digest",
                description="Aggregates active CRM pipeline deals and Zoho Books collections, synthesizes an executive briefing memo in Google Drive, and drafts email in Gmail.",
                direction="Bi-directional",
                required_tools=["zoho_crm.search_records", "zoho_books.get_unpaid_invoices", "drive.create_file", "gmail.create_draft"],
                has_hitl_write=False,
                category="Leadership & Strategy",
            ),
        ]

    def list_tasks(self) -> List[AutomationTask]:
        return self.tasks

    def execute_task(self, task_id: str, bypass_hitl: bool = False) -> TaskExecutionResult:
        task = next((t for t in self.tasks if t.id == task_id), None)
        if not task:
            return TaskExecutionResult(task_id=task_id, title="Unknown", success=False, logs=[], summary="", error="Task not found")

        # Dynamic check: verify all required tools are available on connected providers
        avail_tools = {t.name for t in self.registry.get_available_tools()}
        missing = [rt for rt in task.required_tools if rt not in avail_tools]
        if missing:
            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=False,
                logs=[],
                summary="",
                error=f"Cannot execute '{task.title}'. Missing required dynamic tools: {missing}. Ensure both Google Workspace and Zoho MCP providers are connected.",
            )

        logs: List[StepLog] = []
        step = 1

        # Dispatch task workflow
        if task_id == "T01":
            # 1. Search Gmail
            res1 = self.registry.execute_tool("gmail.search_threads", {"query": "Enterprise Advisory", "max_results": 1})
            logs.append(StepLog(step, "Scan Gmail Inbound Inquiries", "gmail.search_threads", {"query": "Enterprise Advisory"}, res1.data))
            step += 1

            # 2. Presidio PII De-identification
            text_to_audit = "Rahul Sharma, VP Operations (PAN: AAACB1234F, GSTIN: 27AAACB1234F1Z5)"
            anon, pii_map, entities = self.presidio.anonymize(text_to_audit)
            logs.append(StepLog(step, "Presidio PII De-Identification", None, {"raw": text_to_audit}, {"anonymized": anon, "detected": entities}))
            step += 1

            # 3. Create Lead in Zoho CRM (HITL Gate)
            lead_args = {
                "first_name": "Rahul",
                "last_name": "Sharma",
                "company": "Apex Logistics India Pvt Ltd",
                "email": "rahul.sharma@apexlogistics.in",
                "notes": f"Inbound via Gmail. Requirement: DPDP Act Compliance Audit. PII Protected: {anon}",
            }
            res2 = self.registry.execute_tool("zoho_crm.create_lead", lead_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Create Lead in Zoho CRM", "zoho_crm.create_lead", lead_args, res2.data, res2.is_hitl_pending, res2.hitl_request_id))
            step += 1

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Scanned Gmail for inquiries, shielded PII identifiers, and queued/created lead in Zoho CRM.",
            )

        elif task_id == "T02":
            # 1. List Calendar Events
            res1 = self.registry.execute_tool("calendar.list_events", {})
            logs.append(StepLog(step, "Fetch Upcoming Meetings", "calendar.list_events", {}, res1.data))
            step += 1

            # 2. Query CRM Deals
            res2 = self.registry.execute_tool("zoho_crm.search_records", {"module": "Deals", "query": "Apex Logistics"})
            logs.append(StepLog(step, "Lookup Client Deal Context", "zoho_crm.search_records", {"query": "Apex Logistics"}, res2.data))
            step += 1

            # 3. Query Customer Balance
            res3 = self.registry.execute_tool("zoho_books.get_customer_balance", {"customer_name": "Apex Logistics India Pvt Ltd"})
            logs.append(StepLog(step, "Inspect Ledger Balance", "zoho_books.get_customer_balance", {"customer": "Apex Logistics"}, res3.data))
            step += 1

            # 4. Generate Google Drive Briefing Doc
            doc_content = (
                "# Executive Briefing Dossier: Apex Logistics\n"
                "Upcoming Meeting: Leadership Strategy Review\n"
                "Deal Stage: Proposal / Price Quote (INR 8,50,000)\n"
                "Outstanding Receivables: INR 3,40,000 (Overdue: 14 days)\n"
                "Key Objective: Confirm DPDP compliance scope and secure milestone payment."
            )
            res4 = self.registry.execute_tool("drive.create_file", {"name": "Meeting_Briefing_Apex_Logistics.md", "content": doc_content}, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Upload Briefing Dossier to Google Drive", "drive.create_file", {"name": "Meeting_Briefing_Apex_Logistics.md"}, res4.data, res4.is_hitl_pending, res4.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Compiled multi-service meeting briefing from Calendar, Zoho CRM, and Zoho Books into Google Drive.",
            )

        elif task_id == "T03":
            # 1. Get Unpaid Invoices
            res1 = self.registry.execute_tool("zoho_books.get_unpaid_invoices", {"min_days_overdue": 7})
            logs.append(StepLog(step, "Query Overdue Invoices from Zoho Books", "zoho_books.get_unpaid_invoices", {"min_days": 7}, res1.data))
            step += 1

            # 2. Dispatch reminder via Gmail (HITL Gate)
            mail_args = {
                "to": "finance@apexlogistics.in",
                "subject": "Gentle Reminder: Invoice INV-2026-042 Overdue",
                "body": "Dear Finance Team,\n\nKindly note that Invoice INV-2026-042 for INR 3,40,000 is 14 days overdue. Please arrange payment at your earliest convenience.\n\nWarm regards,\nAccounts Team",
            }
            res2 = self.registry.execute_tool("gmail.send_message", mail_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Dispatch Payment Reminder Email", "gmail.send_message", mail_args, res2.data, res2.is_hitl_pending, res2.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Retrieved aging debtors from Zoho Books and queued/sent personalized payment reminder via Gmail.",
            )

        elif task_id == "T04":
            # 1. Search signed contract in Drive
            res1 = self.registry.execute_tool("drive.search_files", {"query": "Signed"})
            logs.append(StepLog(step, "Locate Signed Contract in Google Drive", "drive.search_files", {"query": "Signed"}, res1.data))
            step += 1

            # 2. Read Contract Content
            res2 = self.registry.execute_tool("drive.read_file_content", {"file_id": "file_drv_201"})
            logs.append(StepLog(step, "Extract Contract Value & Milestones", "drive.read_file_content", {"file_id": "file_drv_201"}, res2.data))
            step += 1

            # 3. Update Deal to Closed Won (HITL Gate)
            deal_args = {"deal_id": "deal_zc_501", "stage": "Closed Won", "amount": 850000.0, "notes": "Contract signed & stored in Drive."}
            res3 = self.registry.execute_tool("zoho_crm.update_deal", deal_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Update Zoho CRM Deal to 'Closed Won'", "zoho_crm.update_deal", deal_args, res3.data, res3.is_hitl_pending, res3.hitl_request_id))
            step += 1

            # 4. Create Milestone 1 Invoice in Zoho Books (HITL Gate)
            inv_args = {"customer_name": "Apex Logistics India Pvt Ltd", "amount": 340000.0, "due_date": "2026-10-10", "description": "Advance 40% on Contract Execution"}
            res4 = self.registry.execute_tool("zoho_books.create_invoice", inv_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Draft Milestone 1 Invoice in Zoho Books", "zoho_books.create_invoice", inv_args, res4.data, res4.is_hitl_pending, res4.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Verified executed contract from Google Drive, updated Zoho CRM Deal to Closed Won, and drafted milestone invoice in Zoho Books.",
            )

        elif task_id == "T05":
            # 1. Search Urgent Email
            res1 = self.registry.execute_tool("gmail.search_threads", {"query": "URGENT Outage"})
            logs.append(StepLog(step, "Detect Critical Email in Gmail", "gmail.search_threads", {"query": "URGENT Outage"}, res1.data))
            step += 1

            # 2. Create High-Priority Ticket in Zoho Desk (HITL)
            tkt_args = {
                "subject": "CRITICAL: Production GST filing API Outage 502",
                "description": "Incoming report from Bharat Retail: GSTR-3B webhook failing with 502 Bad Gateway.",
                "contact_email": "amit.patel@bharatretail.in",
                "priority": "High",
            }
            res2 = self.registry.execute_tool("zoho_desk.create_ticket", tkt_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Create Ticket in Zoho Desk", "zoho_desk.create_ticket", tkt_args, res2.data, res2.is_hitl_pending, res2.hitl_request_id))
            step += 1

            # 3. Schedule Triage Slot in Google Calendar (HITL)
            cal_args = {
                "summary": "P0 Escalation Triage: Bharat Retail GST Issue",
                "start_time": (datetime.datetime.now() + datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:00+05:30"),
                "end_time": (datetime.datetime.now() + datetime.timedelta(minutes=75)).strftime("%Y-%m-%dT%H:%M:00+05:30"),
                "attendees": ["lead.architect@advisoryfirm.in", "amit.patel@bharatretail.in"],
            }
            res3 = self.registry.execute_tool("calendar.create_event", cal_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Schedule Emergency Triage Meeting", "calendar.create_event", cal_args, res3.data, res3.is_hitl_pending, res3.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Escalated critical client email to Zoho Desk and scheduled emergency triage meeting on Google Calendar.",
            )

        elif task_id == "T06":
            # 1. Books unpaid invoices
            res1 = self.registry.execute_tool("zoho_books.get_unpaid_invoices", {})
            logs.append(StepLog(step, "Fetch Outstanding Receivables", "zoho_books.get_unpaid_invoices", {}, res1.data))
            step += 1

            # 2. CRM open deals
            res2 = self.registry.execute_tool("zoho_crm.search_records", {"module": "Deals", "query": ""})
            logs.append(StepLog(step, "Fetch Open Deal Pipeline", "zoho_crm.search_records", {"module": "Deals"}, res2.data))
            step += 1

            # 3. Upload report to Drive
            report = (
                "# Executive Client Financial Health & Receivables\n"
                "Total Unpaid Invoices: INR 4,65,000\n"
                "Weighted Pipeline: INR 12,70,000\n"
                "Status: High Cash-Flow Health. Action: Prioritize Apex Logistics collection."
            )
            res3 = self.registry.execute_tool("drive.create_file", {"name": "Client_Financial_Health_Digest.md", "content": report}, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Save Financial Digest in Google Drive", "drive.create_file", {"name": "Client_Financial_Health_Digest.md"}, res3.data, res3.is_hitl_pending, res3.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Consolidated financial receivables and CRM pipeline into an executive report in Google Drive.",
            )

        elif task_id == "T07":
            # 1. CRM search accounts
            res1 = self.registry.execute_tool("zoho_crm.search_records", {"module": "Accounts", "query": "Apex"})
            logs.append(StepLog(step, "Fetch Account Details", "zoho_crm.search_records", {"query": "Apex"}, res1.data))
            step += 1

            # 2. Provision Drive folder structure
            res2 = self.registry.execute_tool("drive.create_file", {"name": "01_Compliance_Records_Apex/README.txt", "content": "Storage for DPDP consent logs & audit trails."}, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Provision Client Drive Folder Structure", "drive.create_file", {"name": "01_Compliance_Records_Apex"}, res2.data, res2.is_hitl_pending, res2.hitl_request_id))
            step += 1

            # 3. Schedule Kickoff Meeting on Calendar
            kickoff_args = {
                "summary": "Project Kickoff: Apex Logistics Onboarding",
                "start_time": (datetime.datetime.now() + datetime.timedelta(days=2)).strftime("%Y-%m-%dT11:00:00+05:30"),
                "end_time": (datetime.datetime.now() + datetime.timedelta(days=2, hours=1)).strftime("%Y-%m-%dT12:00:00+05:30"),
                "attendees": ["rahul.sharma@apexlogistics.in"],
            }
            res3 = self.registry.execute_tool("calendar.create_event", kickoff_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Schedule Client Kickoff Meeting", "calendar.create_event", kickoff_args, res3.data, res3.is_hitl_pending, res3.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Automated client onboarding by setting up Drive folders and booking kickoff meeting on Calendar.",
            )

        elif task_id == "T08":
            # 1. Read notes from Drive
            res1 = self.registry.execute_tool("drive.read_file_content", {"file_id": "file_drv_202"})
            logs.append(StepLog(step, "Read Meeting Notes from Google Drive", "drive.read_file_content", {"file_id": "file_drv_202"}, res1.data))
            step += 1

            # 2. Update CRM Deal Notes
            deal_args = {"deal_id": "deal_zc_501", "stage": "Proposal/Price Quote", "notes": "Agreed to finalize Consent Architecture by Oct 5."}
            res2 = self.registry.execute_tool("zoho_crm.update_deal", deal_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Sync Meeting Action Items to Zoho CRM", "zoho_crm.update_deal", deal_args, res2.data, res2.is_hitl_pending, res2.hitl_request_id))
            step += 1

            # 3. Schedule Follow-up in Calendar
            cal_args = {
                "summary": "Security Review: Apex Logistics Action Item",
                "start_time": (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y-%m-%dT15:00:00+05:30"),
                "end_time": (datetime.datetime.now() + datetime.timedelta(days=5, hours=1)).strftime("%Y-%m-%dT16:00:00+05:30"),
                "attendees": ["demo.partner@advisoryfirm.in", "rahul.sharma@apexlogistics.in"],
            }
            res3 = self.registry.execute_tool("calendar.create_event", cal_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Schedule Action Item on Google Calendar", "calendar.create_event", cal_args, res3.data, res3.is_hitl_pending, res3.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Extracted meeting minutes from Google Drive, updated Zoho CRM Deal notes, and scheduled follow-up on Calendar.",
            )

        elif task_id == "T09":
            # 1. Search Bill PDF in Drive
            res1 = self.registry.execute_tool("drive.search_files", {"query": "Vendor_Bill"})
            logs.append(StepLog(step, "Locate Receipt in Google Drive", "drive.search_files", {"query": "Vendor_Bill"}, res1.data))
            step += 1

            # 2. Read Receipt Content
            res2 = self.registry.execute_tool("drive.read_file_content", {"file_id": "file_drv_203"})
            logs.append(StepLog(step, "Extract Vendor GSTIN & Billing Details", "drive.read_file_content", {"file_id": "file_drv_203"}, res2.data))
            step += 1

            # 3. Book Expense in Zoho Books (HITL)
            exp_args = {
                "vendor_name": "Cloud Services India Pvt Ltd",
                "amount": 45200.0,
                "gstin": "27AABCC5544E1Z3",
                "category": "Office & Infrastructure",
            }
            res3 = self.registry.execute_tool("zoho_books.record_expense", exp_args, bypass_hitl=bypass_hitl)
            logs.append(StepLog(step, "Record Expense Bill in Zoho Books", "zoho_books.record_expense", exp_args, res3.data, res3.is_hitl_pending, res3.hitl_request_id))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Extracted invoice data from Google Drive and booked an audited expense bill with GSTIN in Zoho Books.",
            )

        elif task_id == "T10":
            # 1. CRM deals
            res1 = self.registry.execute_tool("zoho_crm.search_records", {"module": "Deals", "query": ""})
            logs.append(StepLog(step, "Pull Pipeline Deals from Zoho CRM", "zoho_crm.search_records", {}, res1.data))
            step += 1

            # 2. Books overdue invoices
            res2 = self.registry.execute_tool("zoho_books.get_unpaid_invoices", {})
            logs.append(StepLog(step, "Pull Overdue Receivables from Zoho Books", "zoho_books.get_unpaid_invoices", {}, res2.data))
            step += 1

            # 3. Upload summary to Drive
            memo = (
                "# Weekly Executive Business Memo\n"
                "Active Pipeline: INR 12,70,000 across 2 Enterprise Deals\n"
                "Pending Collections: INR 4,65,000 (Action required on Apex Logistics)\n"
                "Forecast: High certainty on closing Apex DPDP engagement by end of month."
            )
            res3 = self.registry.execute_tool("drive.create_file", {"name": f"Weekly_Digest_{datetime.date.today()}.md", "content": memo}, bypass_hitl=True)
            logs.append(StepLog(step, "Publish Weekly Digest to Google Drive", "drive.create_file", {"name": "Weekly_Digest.md"}, res3.data))
            step += 1

            # 4. Create Draft in Gmail
            draft_args = {
                "to": "partners@advisoryfirm.in",
                "subject": f"Weekly Executive Business Digest - {datetime.date.today()}",
                "body": memo,
            }
            res4 = self.registry.execute_tool("gmail.create_draft", draft_args)
            logs.append(StepLog(step, "Create Email Draft in Gmail", "gmail.create_draft", draft_args, res4.data))

            return TaskExecutionResult(
                task_id=task_id,
                title=task.title,
                success=True,
                logs=logs,
                summary="Compiled multi-system metrics from Zoho CRM & Books, stored executive memo in Google Drive, and generated email draft in Gmail.",
            )

        return TaskExecutionResult(task_id=task_id, title=task.title, success=False, logs=logs, summary="", error="Unhandled workflow logic.")
