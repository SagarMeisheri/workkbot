"""MCP Tool Safety Classifier (Google ADK 2.0 & Spec 04, R04.3).

Heuristically analyzes MCP tool names and descriptions to classify mutating operations
as `critical: true` (requiring in-chat HITL confirmation) and safe retrievals as `critical: false`.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, Set

# Mutating verbs and prefixes requiring HITL approval
MUTATING_PREFIXES = (
    "create_",
    "delete_",
    "update_",
    "send_",
    "insert_",
    "label_",
    "unlabel_",
    "copy_",
    "remove_",
    "modify_",
    "cancel_",
    "post_",
    "execute_",
    "write_",
    "patch_",
)

# Explicitly verified Google Workspace tool classification overrides
EXPLICIT_TOOL_SAFETY: Dict[str, bool] = {
    # Gmail
    "gmail.create_draft": True,
    "gmail.label_message": True,
    "gmail.label_thread": True,
    "gmail.unlabel_message": True,
    "gmail.unlabel_thread": True,
    "gmail.get_message": False,
    "gmail.get_thread": False,
    "gmail.list_drafts": False,
    "gmail.list_labels": False,
    "gmail.search_threads": False,
    # Google Drive
    "drive.create_file": True,
    "drive.copy_file": True,
    "drive.download_file_content": False,
    "drive.get_file_metadata": False,
    "drive.get_file_permissions": False,
    "drive.list_recent_files": False,
    "drive.read_file_content": False,
    "drive.search_files": False,
    # Google Docs
    "docs.read_doc": False,
    "docs.update_doc": True,
    # Google Sheets
    "sheets.get_values": False,
    "sheets.get_spreadsheet": False,
    "sheets.update_spreadsheet": True,
    "sheets.update_values": True,
    "sheets.update_formulas": True,
    "sheets.insert_dimension": True,
    # Google Slides
    "slides.read_presentation": False,
    "slides.update_presentation": True,
    # Google Calendar
    "calendar.create_event": True,
    "calendar.delete_event": True,
    "calendar.update_event": True,
    "calendar.respond_to_event": True,
    "calendar.get_event": False,
    "calendar.list_calendars": False,
    "calendar.list_events": False,
    "calendar.search_events": False,
    "calendar.suggest_time": False,
    # Google Chat
    "chat.send_message": True,
    "chat.mark_as_read": True,
    "chat.mark_as_unread": True,
    "chat.search_conversations": False,
    "chat.list_messages": False,
    "chat.search_messages": False,
    "chat.list_memberships": False,
    # People API
    "people.get_user_profile": False,
    "people.search_contacts": False,
    "people.search_directory_people": False,
}


@dataclass
class ToolSafetyInfo:
    tool_name: str
    is_critical: bool
    reason: str
    action_type: str  # "read" | "write"


class ToolSafetyClassifier:
    """Classifies tools dynamically based on explicit mapping and semantic heuristics."""

    def classify(self, tool_name: str, tool_description: Optional[str] = None) -> ToolSafetyInfo:
        normalized_name = tool_name.strip().lower()
        
        # 1. Check exact tool mapping (support both dotted and underscored format)
        dotted_name = normalized_name.replace("_", ".")
        underscored_name = normalized_name.replace(".", "_")
        for candidate in (normalized_name, dotted_name, underscored_name):
            if candidate in EXPLICIT_TOOL_SAFETY:
                is_crit = EXPLICIT_TOOL_SAFETY[candidate]
                return ToolSafetyInfo(
                    tool_name=tool_name,
                    is_critical=is_crit,
                    reason="Explicitly classified Google Workspace tool",
                    action_type="write" if is_crit else "read",
                )

        # 2. Extract base name without namespace (e.g. 'calendar.create_event' -> 'create_event')
        base_name = normalized_name.split(".")[-1] if "." in normalized_name else normalized_name
        
        # 3. Check mutating prefixes and infixes (e.g. 'create_event' or 'calendar_create_event')
        mutating_infixes = (
            "_create",
            "_delete",
            "_update",
            "_send",
            "_insert",
            "_remove",
            "_modify",
            "_cancel",
            "_write",
            "_patch",
        )
        if base_name.startswith(MUTATING_PREFIXES) or any(inf in normalized_name for inf in mutating_infixes):
            return ToolSafetyInfo(
                tool_name=tool_name,
                is_critical=True,
                reason=f"Tool name contains mutating operation",
                action_type="write",
            )


        # 4. Check description keywords if provided
        if tool_description:
            desc_lower = tool_description.lower()
            mutating_keywords = {"creates", "deletes", "modifies", "updates", "sends", "cancels", "destroys"}
            for kw in mutating_keywords:
                if kw in desc_lower:
                    return ToolSafetyInfo(
                        tool_name=tool_name,
                        is_critical=True,
                        reason=f"Tool description contains mutating keyword '{kw}'",
                        action_type="write",
                    )

        # 5. Default to read-only safe
        return ToolSafetyInfo(
            tool_name=tool_name,
            is_critical=False,
            reason="Read-only retrieval operation",
            action_type="read",
        )


tool_classifier = ToolSafetyClassifier()
