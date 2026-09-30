"""Test VAL-04.1: Heuristic Classifier Safety Assessment (Google Workspace & Spec 04)."""
import pytest
from src.mcp.classifier import tool_classifier, ToolSafetyInfo


def test_google_workspace_mutating_tools_classified_as_critical():
    """Mutating tools must strictly be classified as critical: true (write action)."""
    mutating_tools = [
        "gmail.create_draft",
        "gmail.label_message",
        "gmail.unlabel_thread",
        "drive.create_file",
        "drive.copy_file",
        "docs.update_doc",
        "sheets.update_values",
        "sheets.update_spreadsheet",
        "sheets.update_formulas",
        "sheets.insert_dimension",
        "slides.update_presentation",
        "calendar.create_event",
        "calendar.delete_event",
        "calendar.update_event",
        "calendar.respond_to_event",
        "chat.send_message",
    ]
    for tool_name in mutating_tools:
        safety = tool_classifier.classify(tool_name)
        assert safety.is_critical is True, f"Expected {tool_name} to be critical"
        assert safety.action_type == "write", f"Expected {tool_name} to be write action"


def test_google_workspace_retrieval_tools_classified_as_safe():
    """Read-only tools must strictly be classified as critical: false (read action)."""
    retrieval_tools = [
        "gmail.get_message",
        "gmail.get_thread",
        "gmail.list_drafts",
        "gmail.search_threads",
        "drive.search_files",
        "drive.read_file_content",
        "drive.get_file_metadata",
        "drive.list_recent_files",
        "docs.read_doc",
        "sheets.get_values",
        "sheets.get_spreadsheet",
        "slides.read_presentation",
        "calendar.list_events",
        "calendar.get_event",
        "calendar.search_events",
        "calendar.suggest_time",
        "chat.search_conversations",
        "chat.list_messages",
        "people.get_user_profile",
        "people.search_contacts",
    ]
    for tool_name in retrieval_tools:
        safety = tool_classifier.classify(tool_name)
        assert safety.is_critical is False, f"Expected {tool_name} to be safe"
        assert safety.action_type == "read", f"Expected {tool_name} to be read action"


def test_dynamic_heuristic_prefix_and_description():
    """Unmapped tools with mutating prefixes or descriptions must be caught."""
    # Custom tool with write prefix
    res1 = tool_classifier.classify("custom_erp.cancel_invoice")
    assert res1.is_critical is True
    assert res1.action_type == "write"

    # Custom tool with write keyword in description
    res2 = tool_classifier.classify("internal.archive_record", tool_description="Deletes old archival data")
    assert res2.is_critical is True

    # Safe unknown tool
    res3 = tool_classifier.classify("custom.fetch_catalog")
    assert res3.is_critical is False
    assert res3.action_type == "read"
