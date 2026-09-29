"""ADK before_model_callback: PII Anonymization & Reversible Tokenization (Spec 03, R03.1).

Intercepts prompt text before it leaves for Vertex AI:
1. Runs Presidio Tier-1 (spaCy NER + Indian identifiers) & Cloud DLP Tier-2.
2. Replaces sensitive entities with surrogate tokens (<PERSON_1>, <IN_PAN_1>, <EMAIL_1>).
3. Saves token-to-PII dictionary in ephemeral SessionPiiVault.
4. Rewrites the prompt content in-place so Vertex AI receives zero raw PII.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.compliance.presidio_engine import presidio_engine
from src.compliance.dlp_engine import dlp_engine
from src.compliance.session_pii_vault import session_pii_vault
from src.compliance.cert_in_logger import cert_in_logger

logger = logging.getLogger("workkbot.compliance.anonymize_callback")


def anonymize_text(session_id: str, text: str) -> Tuple[str, Dict[str, str]]:
    """
    Core anonymization pipeline:
    Runs Presidio + Cloud DLP, updates SessionPiiVault, and returns tokenized text.
    """
    if not text:
        return text, {}

    # 1. Tier 1: Presidio Analyzer with full spaCy & Indian patterns
    findings = presidio_engine.analyze(text)

    # 2. Tier 2: Google Cloud DLP API deep scan if available
    dlp_findings = dlp_engine.inspect_text(text)
    if dlp_findings:
        # Merge non-overlapping DLP findings
        for df in dlp_findings:
            overlap = any(
                not (df["end"] <= f["start"] or df["start"] >= f["end"])
                for f in findings
            )
            if not overlap:
                findings.append(df)
        findings.sort(key=lambda x: x["start"])

    if not findings:
        return text, {}

    # 3. Tokenize text using SessionPiiVault
    sanitized_text, token_map = session_pii_vault.tokenize_text(session_id, text, findings)

    # 4. Structured CERT-In audit logging
    cert_in_logger.log_security_event(
        event_type="PII_REDACTED",
        session_id=session_id,
        details={
            "detected_count": len(findings),
            "tokens_generated": list(token_map.keys()),
        },
    )

    return sanitized_text, token_map


def pii_anonymize_callback(
    callback_context_or_session_id: Any,
    llm_request_or_text: Optional[Any] = None,
) -> Any:
    """
    Canonical Google ADK before_model_callback.
    Supports both ADK (callback_context, llm_request) and direct (session_id, text) signatures.
    """
    # Direct function call signature: anonymize(session_id, text)
    if isinstance(callback_context_or_session_id, str) and isinstance(llm_request_or_text, str):
        session_id = callback_context_or_session_id
        text = llm_request_or_text
        sanitized, token_map = anonymize_text(session_id, text)
        return sanitized, token_map

    # Canonical ADK signature: (callback_context: CallbackContext, llm_request: LlmRequest)
    callback_context = callback_context_or_session_id
    llm_request = llm_request_or_text

    session_id = (
        getattr(callback_context, "session_id", None)
        or getattr(getattr(callback_context, "session", None), "id", None)
        or "default_session"
    )

    if llm_request and hasattr(llm_request, "contents"):
        for content in llm_request.contents:
            if hasattr(content, "parts") and content.parts:
                for part in content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        sanitized, _ = anonymize_text(session_id, text)
                        part.text = sanitized

    # Returning None allows the ADK model runner to proceed with the sanitized prompt
    return None
