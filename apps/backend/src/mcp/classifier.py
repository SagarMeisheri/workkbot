"""Automated Tool Safety Classifier (Spec 04, R04.3).

Evaluates dynamically discovered MCP tools:
- Scans tool name, description, and parameter schemas for write/mutating verbs.
- Assigns `critical: true` to actions requiring in-chat Human-In-The-Loop (HITL) confirmation.
- Assigns `critical: false` to pure retrieval/read actions.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

MUTATING_VERBS = {
    "send",
    "create",
    "delete",
    "update",
    "modify",
    "post",
    "write",
    "execute",
    "cancel",
    "pay",
    "payment",
    "process",
    "dispatch",
    "remove",
    "insert",
    "archive",
    "transfer",
    "destroy",
    "drop",
    "close",
    "terminate",
    "refund",
    "charge",
    "publish",
}

READ_VERBS = {
    "get",
    "list",
    "search",
    "fetch",
    "read",
    "query",
    "describe",
    "show",
    "view",
    "check",
    "find",
    "inspect",
    "preview",
}


class ToolSafetyClassifier:
    """Classifies tools into read-only vs. mutating (critical) actions."""

    @classmethod
    def is_critical(
        cls,
        tool_name: str,
        description: str = "",
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determines whether a tool requires interactive confirmation before execution.
        Returns True if mutating/critical, False if pure read/retrieval.
        """
        name_lower = tool_name.lower().replace("-", "_").replace(".", "_")
        tokens = set(re.findall(r"[a-z0-9]+", name_lower))

        # Check explicit name tokens against mutating verbs
        for verb in MUTATING_VERBS:
            if verb in tokens:
                return True

        # Check prefixes/suffixes in snake_case (e.g., create_event, delete_lead, send_invoice)
        parts = name_lower.split("_")
        if parts and parts[0] in MUTATING_VERBS:
            return True
        if parts and parts[-1] in MUTATING_VERBS:
            return True

        # Check description content for clear mutation declarations
        desc_lower = description.lower() if description else ""
        for verb in MUTATING_VERBS:
            # Match word boundary
            if re.search(rf"\b{verb}\b", desc_lower):
                # Ensure it's not simply "how to create" or "retrieves created"
                if not re.search(rf"\b(retrieves|reads|lists|gets|views|shows)\b.*?\b{verb}", desc_lower):
                    return True

        # Check parameter schema for destructive flags or financial fields
        if parameters_schema and isinstance(parameters_schema, dict):
            props = parameters_schema.get("properties", {})
            if isinstance(props, dict):
                prop_names = set(props.keys())
                destructive_keys = {
                    "confirm", "force", "purge", "destructive", "delete_permanently",
                    "amount", "payment", "recipient", "disburse", "payee"
                }
                if prop_names.intersection(destructive_keys):
                    return True

        return False

    @classmethod
    def classify_tool(
        cls,
        tool_name: str,
        description: str = "",
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Returns structured classification metadata for a tool."""
        critical = cls.is_critical(tool_name, description, parameters_schema)
        return {
            "name": tool_name,
            "critical": critical,
            "action_type": "mutating" if critical else "read_only",
            "requires_hitl": critical,
        }


tool_classifier = ToolSafetyClassifier
