"""CERT-In Incident Reporting & Structured Audit Logger (Spec 03, VAL-03.8).

Emits structured JSON security events to Google Cloud Logging complying with:
1. CERT-In Cyber Security Directions (6-hour mandatory reporting window)
2. DPDP Act 2023 Rule 6 (Security safeguards & audit logs)
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("workkbot.compliance.cert_in")

try:
    from google.cloud import logging as gcp_logging
    HAS_GCP_LOGGING = True
except ImportError:
    HAS_GCP_LOGGING = False


class CertInLogger:
    """Structured security and compliance event logger for CERT-In & DPDP audits."""

    def __init__(self, log_name: str = "workkbot-security-events"):
        self.log_name = log_name
        self._gcp_client: Optional[Any] = None
        self._gcp_logger: Optional[Any] = None
        self.enabled = os.getenv("ENABLE_LIVE_GCP_LOGGING", "false").lower() in ("true", "1")
        self._init_client()

    def _init_client(self) -> None:
        if not HAS_GCP_LOGGING or not self.enabled:
            return

        try:
            self._gcp_client = gcp_logging.Client()
            self._gcp_logger = self._gcp_client.logger(self.log_name)
            logger.info("Google Cloud Logging CERT-In sink initialized: %s", self.log_name)
        except Exception as e:
            logger.warning("Google Cloud Logging client initialization skipped (no ADC / offline): %s", e)
            self._gcp_client = None
            self._gcp_logger = None

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO",
    ) -> Dict[str, Any]:
        """
        Emits an immutable structured JSON log entry for CERT-In incident auditing.
        """
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cert_in_version": "2026.04",
            "regulatory_framework": ["CERT-In Directions 2022", "DPDP Act 2023 Rule 6"],
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id or "anonymous",
            "org_id": org_id or "system",
            "session_id": session_id,
            "details": details or {},
        }

        # 1. Dispatch to live Google Cloud Logging if client is connected
        if self._gcp_logger:
            try:
                self._gcp_logger.log_struct(payload, severity=severity)
            except Exception as e:
                logger.warning("Failed to emit log to Google Cloud Logging: %s", e)

        # 2. Always output JSON log to application logger for Cloud Run stdout capture
        logger.info("CERT-In Audit Event: %s", json.dumps(payload))
        return payload


# Global singleton
cert_in_logger = CertInLogger()
