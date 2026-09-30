"""Human-in-the-Loop (HITL) In-Chat Confirmation Handler (Google ADK 2.0 & Spec 04, R04.4).

Bridges ADK's `ToolContext.request_confirmation()` to interactive client stream events,
enabling touch-friendly mobile and web confirmation without admin bottlenecks.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional
import uuid


import hashlib
import json

@dataclass
class ToolConfirmationRequest:
    confirmation_id: str
    tool_name: str
    service_name: str
    action_title: str
    parameters: Dict[str, Any]
    confirmation_hash: str = ""
    security_notice: str = "Action requires employee authorization before execution."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool_confirmation_request",
            "confirmation_id": self.confirmation_id,
            "confirmation_hash": self.confirmation_hash,
            "tool_name": self.tool_name,
            "service_name": self.service_name,
            "action_title": self.action_title,
            "parameters": self.parameters,
            "security_notice": self.security_notice,
        }


def format_confirmation_request(
    tool_name: str,
    parameters: Dict[str, Any],
    confirmation_id: Optional[str] = None,
) -> ToolConfirmationRequest:
    """Creates a structured confirmation payload for assistant-ui ApprovalCard with parameter binding hash."""
    cid = confirmation_id or f"hitl_{uuid.uuid4().hex[:12]}"
    
    # Compute deterministic parameter hash to bind confirmed parameters cryptographically (VULN-04 Defense)
    param_str = json.dumps(parameters, sort_keys=True)
    chash = hashlib.sha256(f"{tool_name}:{param_str}".encode()).hexdigest()[:16]

    # Human-friendly service identification
    service = "Google Workspace"
    if "gmail" in tool_name:
        service = "Gmail"
    elif "calendar" in tool_name:
        service = "Google Calendar"
    elif "drive" in tool_name:
        service = "Google Drive"
    elif "docs" in tool_name:
        service = "Google Docs"
    elif "sheets" in tool_name:
        service = "Google Sheets"
    elif "chat" in tool_name:
        service = "Google Chat"

    # Human-friendly action title
    action_part = tool_name.split(".")[-1].replace("_", " ").title()
    title = f"{action_part} in {service}"

    return ToolConfirmationRequest(
        confirmation_id=cid,
        tool_name=tool_name,
        service_name=service,
        action_title=title,
        parameters=parameters,
        confirmation_hash=chash,
    )
