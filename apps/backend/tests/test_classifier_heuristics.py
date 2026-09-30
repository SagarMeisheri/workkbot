"""Automated Heuristic Tool Safety Classification Tests (Spec 04, VAL-04.1).

Verifies that ToolSafetyClassifier accurately tags mutating actions (send_invoice,
delete_event, create_calendar_event, process_payment) as critical: True,
and pure retrieval actions (search_drive, get_lead, list_messages, query_status)
as critical: False.
"""
import pytest
from src.mcp.classifier import tool_classifier


def test_mutating_actions_flagged_as_critical():
    """Mutating tools must be classified as critical=True (VAL-04.1)."""
    mutating_cases = [
        ("google_calendar_create_event", "Creates a calendar event in user Google Calendar"),
        ("zoho_books_create_invoice", "Generates a tax invoice in Zoho Books"),
        ("send_email_notification", "Sends outbound email to customer"),
        ("delete_user_session", "Deletes active session"),
        ("process_vendor_payment", "Executes payment transaction for vendor"),
        ("update_customer_record", "Updates customer address and GST details"),
        ("cancel_subscription_order", "Cancels customer active order"),
        ("post_message_to_slack", "Posts a message into team channel"),
    ]

    for name, desc in mutating_cases:
        is_crit = tool_classifier.is_critical(name, desc)
        assert is_crit is True, f"Expected {name} to be critical, got False"


def test_retrieval_actions_flagged_as_non_critical():
    """Pure read/retrieval tools must be classified as critical=False (VAL-04.1)."""
    read_cases = [
        ("google_drive_search", "Searches Google Drive for matching files"),
        ("zoho_crm_get_lead", "Retrieves lead details from Zoho CRM"),
        ("list_invoices", "Lists recent customer invoices without modifying"),
        ("fetch_account_balance", "Fetches current ledger balance"),
        ("query_compliance_status", "Returns DPDP statutory compliance status"),
        ("read_document_text", "Reads content of document"),
    ]

    for name, desc in read_cases:
        is_crit = tool_classifier.is_critical(name, desc)
        assert is_crit is False, f"Expected {name} to be non-critical, got True"


def test_parameter_driven_criticality():
    """Tools with dangerous parameters (amount, payment, recipient) are marked critical."""
    schema_with_amount = {
        "properties": {
            "amount": {"type": "number"},
            "recipient": {"type": "string"},
        }
    }
    is_crit = tool_classifier.is_critical(
        tool_name="dispatch_funds",
        description="Dispatches transaction",
        parameters_schema=schema_with_amount,
    )
    assert is_crit is True
