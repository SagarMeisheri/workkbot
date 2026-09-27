"""
Workkbot Local PoC: Google ADK 2.0 Native Guardrail Callbacks
Integrates Presidio PII de-identification, consent gating, HITL interception,
and prompt injection shielding into official ADK 2.0 lifecycle hooks.
"""
from typing import Any, Dict, Optional
from src.core.presidio_guard import PresidioGuard
from src.core.injection_shield import InjectionShield
from src.core.hitl import HitlGatekeeper


class WorkkbotGuardrailCallbacks:
    """
    Implements ADK 2.0 callbacks for Agent & Runner execution:
    - before_model_callback: In-process Presidio PII anonymization into ephemeral RAM (temp:pii_map)
    - after_model_callback: Rehydrates PII surrogate tokens in LLM response
    - before_tool_callback: Granular consent check & Human-In-The-Loop (HITL) mutation intercept
    - after_tool_callback: Untrusted content wrapping (<untrusted_content> injection shield)
    """

    def __init__(
        self,
        presidio: PresidioGuard,
        shield: InjectionShield,
        hitl: HitlGatekeeper,
    ):
        self.presidio = presidio
        self.shield = shield
        self.hitl = hitl

    def before_model(self, callback_context: Any, llm_request: Any) -> Optional[Any]:
        """
        De-identifies sensitive PII (PAN, Aadhaar, GSTIN, Email, Phone) from prompt
        before sending to the Gemini LLM. Stores mapping in ephemeral state (temp:pii_map).
        """
        pii_map = callback_context.state.get("temp:pii_map", {})
        if hasattr(llm_request, "contents") and llm_request.contents:
            for content in llm_request.contents:
                parts = getattr(content, "parts", []) or []
                for part in parts:
                    text_val = getattr(part, "text", None)
                    if text_val:
                        anon_text, new_map, _ = self.presidio.anonymize(text_val)
                        part.text = anon_text
                        pii_map.update(new_map)
        callback_context.state["temp:pii_map"] = pii_map
        return None  # Let model execution proceed

    def after_model(self, callback_context: Any, llm_response: Any) -> Optional[Any]:
        """
        Rehydrates surrogate tokens in model response before presentation to user.
        """
        pii_map = callback_context.state.get("temp:pii_map", {})
        if pii_map and hasattr(llm_response, "content") and llm_response.content:
            parts = getattr(llm_response.content, "parts", []) or []
            for part in parts:
                text_val = getattr(part, "text", None)
                if text_val:
                    part.text = self.presidio.rehydrate(text_val, pii_map)
        return None  # Return None to keep modified response

    def before_tool(self, tool: Any, args: Dict[str, Any], tool_context: Any) -> Optional[Dict[str, Any]]:
        """
        1. Checks user consent for tool invocation.
        2. Intercepts mutating actions for Human-In-The-Loop approval.
        """
        tool_name = getattr(tool, "name", str(tool))
        server_name = getattr(tool, "server", "system")

        # 1. Verify consent
        allowed, msg = self.shield.verify_consent(tool_name)
        if not allowed:
            return {"error": msg, "blocked": True}

        # 2. Check if tool requires HITL approval
        is_mutating = getattr(tool, "is_mutating", False)
        bypass_hitl = tool_context.state.get("bypass_hitl", False)

        if is_mutating and not bypass_hitl:
            approval = self.hitl.create_approval_request(
                action_name=tool_name,
                target_service=server_name,
                summary=f"Approval required to execute mutating tool {tool_name}",
                payload=args,
            )
            # Returning a dict skips the normal tool execution and returns this result
            return {
                "status": "pending_human_approval",
                "message": f"Operation paused. Human approval required for {tool_name}.",
                "hitl_request_id": approval.id,
            }

        return None  # Proceed with tool execution

    def after_tool(
        self, tool: Any, args: Dict[str, Any], tool_context: Any, tool_response: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Encloses raw tool output inside <untrusted_content> XML envelope
        to block indirect prompt injection.
        """
        tool_name = getattr(tool, "name", str(tool))
        server_name = getattr(tool, "server", "external")
        shielded = self.shield.wrap_untrusted_content(server_name, tool_name, tool_response)
        return {"shielded_output": shielded, "result": tool_response}
