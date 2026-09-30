"""Microsoft Presidio AnalyzerEngine with Full spaCy NLP & Custom Indian Recognizers (Spec 03, R03.2).

Detects:
1. Indian Aadhaar numbers (12 digits validated with Verhoeff checksum algorithm)
2. Indian PAN cards (5 alpha, 4 numeric, 1 alpha)
3. Indian UPI Virtual Payment Addresses (VPA)
4. Indian Mobile phone numbers
5. Personal names, locations, and organizations via spaCy en_core_web_sm
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("workkbot.compliance.presidio")

# Verhoeff algorithm multiplication, permutation, and inverse tables
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)

# Statutory identifiers, government IDs, and financial tokens (DPDP Act 2023 & Aadhaar Act 2016)
# Deliberately excludes LOCATION, ORGANIZATION, DATE_TIME, NRP, AGE, and general PERSON
# to prevent over-masking common nouns, countries, cities, and companies.
DEFAULT_PII_ENTITIES: List[str] = [
    # Indian Statutory Identifiers
    "INDIA_PAN",
    "INDIA_AADHAAR",
    "INDIA_GST",
    "INDIA_GST_NUMBER",
    "INDIA_UPI",
    "INDIA_PHONE",
    # Statutory / Financial IDs
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
]


def validate_verhoeff(num_str: str) -> bool:
    """Validates an Indian Aadhaar number against the Verhoeff checksum algorithm."""
    clean_digits = [int(c) for c in num_str if c.isdigit()]
    if len(clean_digits) != 12:
        return False
    # Aadhaar first digit cannot be 0 or 1
    if clean_digits[0] in (0, 1):
        return False
    c = 0
    for i, digit in enumerate(reversed(clean_digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
    return c == 0


def generate_verhoeff(num_str: str) -> str:
    """Generates the 12th Verhoeff check digit for an 11-digit prefix."""
    clean_digits = [int(c) for c in num_str if c.isdigit()]
    c = 0
    for i, digit in enumerate(reversed(clean_digits), start=1):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
    return str(_VERHOEFF_INV[c])


try:
    from presidio_analyzer import (
        AnalyzerEngine,
        Pattern,
        PatternRecognizer,
        RecognizerResult,
    )
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    HAS_PRESIDIO = True
except ImportError:
    HAS_PRESIDIO = False


class AadhaarRecognizer:
    """Custom PatternRecognizer for Indian Aadhaar with Verhoeff validation."""

    ENTITY_TYPE = "INDIA_AADHAAR"

    def __init__(self):
        self.regex = re.compile(r"\b[2-9]\d{3}[-\s]?\d{4}[-\s]?\d{4}\b")

    def analyze(self, text: str) -> List[Tuple[int, int, str, float]]:
        """Finds valid 12-digit Aadhaar numbers that pass the Verhoeff checksum."""
        results = []
        for match in self.regex.finditer(text):
            candidate = match.group()
            digits = re.sub(r"[-\s]", "", candidate)
            if len(digits) == 12 and validate_verhoeff(digits):
                results.append((match.start(), match.end(), self.ENTITY_TYPE, 0.95))
        return results


class PresidioEngine:
    """
    Microsoft Presidio Analyzer with targeted statutory entity filtering.
    """

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.spacy_model = spacy_model
        self.analyzer: Optional[AnalyzerEngine] = None
        self._init_analyzer()

    def _init_analyzer(self) -> None:
        if not HAS_PRESIDIO:
            logger.warning("presidio_analyzer not installed; operating in pure-python fallback mode.")
            return

        try:
            # Initialize with canonical spaCy NLP engine
            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": self.spacy_model}],
                }
            )
            nlp_engine = provider.create_engine()
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
            self._register_indian_recognizers()
            logger.info("Presidio Analyzer initialized with spaCy %s & Indian recognizers", self.spacy_model)
        except Exception as e:
            logger.warning("Error initializing spaCy Presidio engine (%s); falling back to default AnalyzerEngine", e)
            try:
                self.analyzer = AnalyzerEngine()
                self._register_indian_recognizers()
            except Exception as e2:
                logger.error("Failed to initialize Presidio: %s", e2)
                self.analyzer = None

    def _register_indian_recognizers(self) -> None:
        if not self.analyzer:
            return

        # 1. Indian PAN: [A-Z]{5}[0-9]{4}[A-Z]
        pan_pattern = Pattern(
            name="india_pan_pattern",
            regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            score=0.9,
        )
        pan_recognizer = PatternRecognizer(
            supported_entity="INDIA_PAN",
            patterns=[pan_pattern],
            context=["pan", "tax", "income tax", "permanent account number"],
        )
        self.analyzer.registry.add_recognizer(pan_recognizer)

        # 2. Indian UPI: [a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}
        upi_pattern = Pattern(
            name="india_upi_pattern",
            regex=r"\b[a-zA-Z0-9.\-_]{2,256}@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|ibl|axl|upi|postbank|jupiteraxis)\b",
            score=0.95,
        )
        upi_recognizer = PatternRecognizer(
            supported_entity="INDIA_UPI",
            patterns=[upi_pattern],
            context=["upi", "pay", "vpa", "gpay", "phonepe", "transfer"],
        )
        self.analyzer.registry.add_recognizer(upi_recognizer)

        # 3. Indian Mobile: (+91|91|0)?[6-9]\d{9}
        phone_pattern = Pattern(
            name="india_mobile_pattern",
            regex=r"\b(?:\+91|91|0)?[6-9]\d{9}\b",
            score=0.85,
        )
        phone_recognizer = PatternRecognizer(
            supported_entity="INDIA_PHONE",
            patterns=[phone_pattern],
            context=["mobile", "phone", "call", "whatsapp", "contact", "+91"],
        )
        self.analyzer.registry.add_recognizer(phone_recognizer)

        # 4. Indian GSTIN: 2 digits state code, 10 char PAN, 1 entity code, 'Z', 1 checksum digit
        gst_pattern = Pattern(
            name="india_gst_pattern",
            regex=r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b",
            score=0.95,
        )
        gst_recognizer = PatternRecognizer(
            supported_entity="INDIA_GST",
            patterns=[gst_pattern],
            context=["gst", "gstin", "goods and services tax", "tax invoice"],
        )
        self.analyzer.registry.add_recognizer(gst_recognizer)

    def analyze(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Analyzes text and returns structured findings.
        By default, limits detection to DEFAULT_PII_ENTITIES (statutory IDs, PAN, Aadhaar, GSTIN, UPI, phone, email).
        Excludes broad entities such as LOCATION (countries/cities) and ORGANIZATION.
        """
        target_entities = entities if entities is not None else DEFAULT_PII_ENTITIES
        findings: List[Dict[str, Any]] = []

        # 1. Custom Verhoeff Aadhaar Scan
        if "INDIA_AADHAAR" in target_entities or "INDIA_AADHAAR_NUMBER" in target_entities:
            aadhaar_scanner = AadhaarRecognizer()
            for start, end, entity_type, score in aadhaar_scanner.analyze(text):
                findings.append({
                    "start": start,
                    "end": end,
                    "entity_type": entity_type,
                    "text": text[start:end],
                    "score": score,
                })

        # 2. Presidio Analyzer Execution with filtered entities
        if self.analyzer:
            try:
                res = self.analyzer.analyze(text=text, entities=target_entities, language=language)
                for r in res:
                    # Skip if overlapping with Aadhaar
                    overlap = any(
                        not (r.end <= f["start"] or r.start >= f["end"])
                        for f in findings
                    )
                    if not overlap:
                        findings.append({
                            "start": r.start,
                            "end": r.end,
                            "entity_type": r.entity_type,
                            "text": text[r.start:r.end],
                            "score": r.score,
                        })
            except Exception as e:
                logger.error("Presidio analyze error: %s", e)
        else:
            # Pure Python fallback for regex matches
            findings.extend(self._fallback_scan(text, target_entities))

        # Sort findings by start position ascending
        findings.sort(key=lambda x: x["start"])
        return findings

    def _fallback_scan(self, text: str, entities: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Pure-python regex scanner for PAN, GST, UPI, Mobile, Email when Presidio isn't loaded."""
        target = entities if entities is not None else DEFAULT_PII_ENTITIES
        res: List[Dict[str, Any]] = []

        patterns = [
            ("INDIA_PAN", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0.9),
            ("INDIA_GST", r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b", 0.95),
            ("INDIA_UPI", r"\b[a-zA-Z0-9.\-_]{2,256}@(okaxis|okhdfcbank|okicici|oksbi|paytm|ybl|ibl|axl|upi)\b", 0.9),
            ("INDIA_PHONE", r"\b(?:\+91|91|0)?[6-9]\d{9}\b", 0.85),
            ("EMAIL_ADDRESS", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", 0.9),
        ]

        for entity_type, pattern_str, score in patterns:
            if entity_type not in target:
                continue
            for m in re.finditer(pattern_str, text):
                res.append({
                    "start": m.start(),
                    "end": m.end(),
                    "entity_type": entity_type,
                    "text": m.group(),
                    "score": score,
                })
        return res


# Global singleton
presidio_engine = PresidioEngine()
