"""Ephemeral In-Session PII Vault (Spec 03, R03.1 & R03.1b).

Maintains a bidirectional mapping between semantic surrogate tokens (e.g. <EMAIL_1>, <IN_PAN_1>)
and real PII strings in backend memory for the active conversational turn.
Supports rehydration for external ERP tool calls (Zoho, Google Workspace) and the user SSE stream.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("workkbot.compliance.vault")

# Canonical token prefix map
_ENTITY_TOKEN_PREFIX = {
    "PERSON": "PERSON",
    "EMAIL_ADDRESS": "EMAIL",
    "INDIA_PAN": "IN_PAN",
    "INDIA_AADHAAR": "IN_AADHAAR",
    "INDIA_UPI": "IN_UPI",
    "INDIA_PHONE": "IN_PHONE",
    "PHONE_NUMBER": "PHONE",
    "LOCATION": "LOCATION",
    "ORGANIZATION": "ORG",
}


class SessionPiiVault:
    """Thread-safe ephemeral session PII vault."""

    def __init__(self):
        self._lock = threading.Lock()
        # session_id -> { token: raw_value }
        self._tokens_to_raw: Dict[str, Dict[str, str]] = {}
        # session_id -> { raw_value: token }
        self._raw_to_tokens: Dict[str, Dict[str, str]] = {}
        # session_id -> { prefix: current_counter }
        self._token_counters: Dict[str, Dict[str, int]] = {}

    def get_or_create_token(self, session_id: str, raw_value: str, entity_type: str) -> str:
        """Assigns or reuses a deterministic surrogate token for a sensitive value within a session."""
        with self._lock:
            self._ensure_session(session_id)
            # If already tokenized, reuse existing token
            if raw_value in self._raw_to_tokens[session_id]:
                return self._raw_to_tokens[session_id][raw_value]

            prefix = _ENTITY_TOKEN_PREFIX.get(entity_type, "SENSITIVE")
            count = self._token_counters[session_id].get(prefix, 0) + 1
            self._token_counters[session_id][prefix] = count

            token = f"<{prefix}_{count}>"
            self._tokens_to_raw[session_id][token] = raw_value
            self._raw_to_tokens[session_id][raw_value] = token
            return token

    def tokenize_text(
        self,
        session_id: str,
        text: str,
        findings: List[Dict[str, Any]],
    ) -> Tuple[str, Dict[str, str]]:
        """
        Replaces detected PII spans with surrogate tokens from right to left to maintain string offsets.
        Returns the sanitized text and the token dictionary for this turn.
        """
        if not findings or not text:
            return text, {}

        # Sort findings descending by start index to replace from end to beginning
        sorted_findings = sorted(findings, key=lambda f: f["start"], reverse=True)
        sanitized = text
        token_map: Dict[str, str] = {}

        for finding in sorted_findings:
            start = finding["start"]
            end = finding["end"]
            raw_val = text[start:end]
            entity_type = finding.get("entity_type", "SENSITIVE")

            token = self.get_or_create_token(session_id, raw_val, entity_type)
            token_map[token] = raw_val
            sanitized = sanitized[:start] + token + sanitized[end:]

        return sanitized, token_map

    def rehydrate_text(self, session_id: str, text: str) -> str:
        """Replaces surrogate tokens in text with original values from the session vault."""
        if not text or session_id not in self._tokens_to_raw:
            return text

        with self._lock:
            tokens = dict(self._tokens_to_raw[session_id])

        result = text
        for token, raw_val in tokens.items():
            if token in result:
                result = result.replace(token, raw_val)
        return result

    def rehydrate_dict(self, session_id: str, data: Any) -> Any:
        """Recursively rehydrates all surrogate tokens within dictionaries, lists, or strings."""
        if isinstance(data, str):
            return self.rehydrate_text(session_id, data)
        elif isinstance(data, dict):
            return {k: self.rehydrate_dict(session_id, v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.rehydrate_dict(session_id, item) for item in data]
        return data

    def mask_text(self, session_id: str, text: str) -> str:
        """Replaces any raw sensitive values known to this session with their surrogate tokens."""
        if not text or session_id not in self._raw_to_tokens:
            return text

        with self._lock:
            raw_map = dict(self._raw_to_tokens[session_id])

        result = text
        for raw_val, token in raw_map.items():
            if raw_val in result:
                result = result.replace(raw_val, token)
        return result

    def mask_dict(self, session_id: str, data: Any) -> Any:
        """Recursively masks known raw PII inside dictionaries, lists, or strings back to tokens."""
        if isinstance(data, str):
            return self.mask_text(session_id, data)
        elif isinstance(data, dict):
            return {k: self.mask_dict(session_id, v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.mask_dict(session_id, item) for item in data]
        return data

    def get_session_tokens(self, session_id: str) -> Dict[str, str]:
        """Returns a snapshot copy of token-to-raw mappings for a session."""
        with self._lock:
            return dict(self._tokens_to_raw.get(session_id, {}))

    def purge_session(self, session_id: str) -> None:
        """Securely clears and purges all token mappings for a completed session."""
        with self._lock:
            self._tokens_to_raw.pop(session_id, None)
            self._raw_to_tokens.pop(session_id, None)
            self._token_counters.pop(session_id, None)

    def create_stream_rehydrator(self, session_id: str) -> "StreamingPiiRehydrator":
        """Creates a streaming rehydrator that handles tokens split across SSE chunks."""
        return StreamingPiiRehydrator(session_id=session_id, vault=self)

    def _ensure_session(self, session_id: str) -> None:
        if session_id not in self._tokens_to_raw:
            self._tokens_to_raw[session_id] = {}
            self._raw_to_tokens[session_id] = {}
            self._token_counters[session_id] = {}


class StreamingPiiRehydrator:
    """Buffers partial token boundaries (e.g. '<IN_' ... 'PAN_1>') across stream chunks."""

    def __init__(self, session_id: str, vault: SessionPiiVault):
        self.session_id = session_id
        self.vault = vault
        self._buffer = ""

    def process_chunk(self, chunk: str) -> str:
        text = self._buffer + chunk
        self._buffer = ""

        # Check if there is an unclosed '<' that looks like an incoming surrogate token
        last_open = text.rfind("<")
        last_close = text.rfind(">")
        if last_open != -1 and last_open > last_close:
            potential_token = text[last_open:]
            # Only buffer if it's token-like (no whitespace or newlines, reasonable token length)
            if " " not in potential_token and "\n" not in potential_token and len(potential_token) < 30:
                self._buffer = potential_token
                text = text[:last_open]

        return self.vault.rehydrate_text(self.session_id, text)

    def flush(self) -> str:
        if self._buffer:
            res = self.vault.rehydrate_text(self.session_id, self._buffer)
            self._buffer = ""
            return res
        return ""


# Global singleton
session_pii_vault = SessionPiiVault()
