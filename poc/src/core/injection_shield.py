"""
Workkbot Local PoC: Indirect Prompt Injection Shield & Tool Consent Gate
Enforces Workkbot Invariant #6:
- Verifies granular consent prior to MCP tool execution.
- Encloses raw external data inside <untrusted_content> XML tags to block injection attacks.
"""
import hashlib
from typing import Any, Dict, Tuple


class InjectionShield:
    def __init__(self):
        # Default local permissions: grant both by default in local PoC or allow toggle
        self.consents: Dict[str, bool] = {
            "WORKSPACE_INTEGRATION": True,
            "ZOHO_INTEGRATION": True,
        }

    def verify_consent(self, tool_name: str) -> Tuple[bool, str]:
        """
        Verifies if the required consent is active for the given tool.
        """
        if tool_name.startswith("gmail_") or tool_name.startswith("drive_") or tool_name.startswith("calendar_"):
            if not self.consents.get("WORKSPACE_INTEGRATION", False):
                return False, "Access blocked: 'WORKSPACE_INTEGRATION' consent has not been granted by user."
        elif tool_name.startswith("zoho_"):
            if not self.consents.get("ZOHO_INTEGRATION", False):
                return False, "Access blocked: 'ZOHO_INTEGRATION' consent has not been granted by user."
        return True, "Consent verified."

    def set_consent(self, consent_type: str, granted: bool):
        self.consents[consent_type] = granted

    def wrap_untrusted_content(self, server: str, tool_name: str, raw_output: Any) -> str:
        """
        Encloses raw data from third-party tools within <untrusted_content> XML envelope
        to prevent untrusted email bodies, calendar notes, or CRM records from hijacking the LLM.
        """
        text_content = str(raw_output)
        content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()[:12]
        
        # Neutralize obvious prompt override sequences inside third-party content
        sanitized_content = text_content.replace("System:", "[Sanitized-System]:")
        sanitized_content = sanitized_content.replace("IGNORE PREVIOUS INSTRUCTIONS", "[Sanitized-Jailbreak-Attempt]")
        sanitized_content = sanitized_content.replace("<|im_start|>", "[Sanitized-Token]")
        sanitized_content = sanitized_content.replace("<|im_end|>", "[Sanitized-Token]")

        wrapped = (
            f'<untrusted_content source="mcp:{server}:{tool_name}" integrity="{content_hash}">\n'
            f"{sanitized_content}\n"
            f"</untrusted_content>"
        )
        return wrapped
