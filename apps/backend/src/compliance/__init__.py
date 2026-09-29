"""Workkbot DPDP Compliance & PII Redaction Module (Spec 03).

Provides:
- PresidioEngine: Microsoft Presidio AnalyzerEngine with spaCy NLP and Indian recognizers
- DlpEngine: Google Cloud Sensitive Data Protection (asia-south1)
- SessionPiiVault: Ephemeral in-session tokenization & argument rehydration
- ADK Callbacks: before_model, before_tool, after_tool
- DsrService: Right to Erasure & Data Portability under DPDP Act 2023 & Apple Guideline 5.1.1
- CertInLogger: Statutory CERT-In incident logging to Google Cloud Logging
"""
from src.compliance.presidio_engine import PresidioEngine, presidio_engine
from src.compliance.dlp_engine import DlpEngine, dlp_engine
from src.compliance.session_pii_vault import SessionPiiVault, session_pii_vault
from src.compliance.dsr_service import DsrService, dsr_service
from src.compliance.cert_in_logger import CertInLogger, cert_in_logger

__all__ = [
    "PresidioEngine",
    "presidio_engine",
    "DlpEngine",
    "dlp_engine",
    "SessionPiiVault",
    "session_pii_vault",
    "DsrService",
    "dsr_service",
    "CertInLogger",
    "cert_in_logger",
]
