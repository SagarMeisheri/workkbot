"""Tool Safety Classification & Mutating Action Heuristics (Spec 04, R04.3).

Evaluates whether dynamically discovered tools require Human-In-The-Loop (HITL)
authorization by scanning tool names, descriptions, and parameter schemas
for mutating verbs and high-risk parameters.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Set


class ToolSafetyClassifier:
    """Semantic classifier categorizing MCP tools as critical (mutating) or non-critical (read-only)."""

    MUTATING_VERBS: Set[str] = {
        "create",
        "send",
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
        "upload",
        "insert",
        "remove",
        "patch",
        "dispatch",
        "revoke",
        "drop",
        "truncate",
        "purge",
        "transfer",
        "order",
        "buy",
        "approve",
        "reject",
    }

    READONLY_VERBS: Set[str] = {
        "get",
        "list",
        "search",
        "fetch",
        "read",
        "query",
        "check",
        "inspect",
        "find",
        "retrieve",
        "count",
        "status",
        "summary",
    }

    RISK_PARAMETERS: Set[str] = {
        "amount",
        "payment",
        "recipient",
        "iban",
        "account_number",
        "card_number",
        "destination",
        "transfer_to",
        "funds",
        "invoice_amount",
    }

    def is_critical(
        self,
        tool_name: str,
        description: str = "",
        parameters_schema: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Determines if a tool is critical (requires user confirmation) or safe to auto-execute."""
        normalized_name = tool_name.lower().replace("-", "_")
        tokens = set(re.split(r"[_\s]+", normalized_name))

        # Check name tokens for mutating verbs
        if tokens & self.MUTATING_VERBS:
            return True

        # Check description tokens
        desc_tokens = set(re.split(r"\W+", description.lower())) if description else set()
        if desc_tokens & self.MUTATING_VERBS:
            # Verify it's not explicitly framed as pure retrieval in description
            # e.g., "list invoices without modifying"
            mutating_found = desc_tokens & self.MUTATING_VERBS
            # If the tool name itself is explicitly read-only and no mutating words in name, check context
            if tokens & self.READONLY_VERBS:
                pass
            else:
                return True

        # Check parameters schema for high-risk parameters
        if parameters_schema and isinstance(parameters_schema, dict):
            properties = parameters_schema.get("properties", {})
            param_names = {k.lower() for k in properties.keys()}
            if param_names & self.RISK_PARAMETERS:
                return True

        # Pure retrieval actions default to non-critical
        if tokens & self.READONLY_VERBS:
            return False

        return False


tool_classifier = ToolSafetyClassifier()
