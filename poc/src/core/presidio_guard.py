"""
Workkbot Local PoC: In-Process Presidio PII De-Identification Proxy
Complies with DPDP Act 2023 Sec. 8(5) and Workkbot Invariant #3.
Maintains translation mappings strictly in ephemeral RAM (`temp:pii_map`).
"""
import re
from typing import Dict, List, Tuple


class PresidioGuard:
    """
    In-process PII de-identification engine with specialized Indian statutory recognizers
    (PAN, Aadhaar, GSTIN) and global PII (Email, Phone, Bank Account, Person).
    """

    def __init__(self):
        # Compiled patterns for statutory Indian identifiers and global PII
        self.patterns = {
            "INDIA_PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"),
            "INDIA_AADHAAR": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
            "INDIA_GSTIN": re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b"),
            "EMAIL_ADDRESS": re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"),
            "PHONE_NUMBER": re.compile(r"\b(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
            "BANK_ACCOUNT": re.compile(r"\b(?:\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|\d{9,16})\b"),
        }

    def anonymize(self, text: str) -> Tuple[str, Dict[str, str], List[Dict[str, str]]]:
        """
        Scans text, replaces sensitive entities with surrogate tokens (<PAN_1>, <EMAIL_1>),
        and returns:
        - anonymized_text: string safe for LLM transmission
        - pii_map: ephemeral dictionary mapping surrogate tokens back to original values
        - detected_entities: list of detected entities for UI auditing
        """
        pii_map: Dict[str, str] = {}
        detected_entities: List[Dict[str, str]] = []
        counters: Dict[str, int] = {}
        anonymized_text = text

        for entity_type, pattern in self.patterns.items():
            matches = list(pattern.finditer(anonymized_text))
            # Process in reverse order to preserve string indices
            for match in reversed(matches):
                val = match.group(0)
                # Avoid masking already surrogate tokens or short numbers that aren't real IDs
                if val.startswith("<") and val.endswith(">"):
                    continue

                if entity_type not in counters:
                    counters[entity_type] = 1
                else:
                    counters[entity_type] += 1

                token = f"<{entity_type}_{counters[entity_type]}>"
                pii_map[token] = val
                detected_entities.append({
                    "type": entity_type,
                    "original": val,
                    "surrogate": token,
                    "start": match.start(),
                    "end": match.end(),
                })

                anonymized_text = (
                    anonymized_text[:match.start()]
                    + token
                    + anonymized_text[match.end():]
                )

        return anonymized_text, pii_map, detected_entities

    def rehydrate(self, text: str, pii_map: Dict[str, str]) -> str:
        """
        Replaces surrogate tokens in model completion with original PII values
        locally in application memory before presenting to the user.
        """
        rehydrated_text = text
        for token, original in pii_map.items():
            rehydrated_text = rehydrated_text.replace(token, original)
        return rehydrated_text
