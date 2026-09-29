"""Google Cloud Sensitive Data Protection (Cloud DLP API) Client (Spec 03, R03.2).

Performs Tier-2 deep PII inspection in Mumbai (asia-south1) for:
- INDIA_AADHAAR_NUMBER
- INDIA_PAN_NUMBER
- INDIA_GST_NUMBER
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger("workkbot.compliance.dlp")

try:
    from google.cloud import dlp_v2
    HAS_DLP = True
except ImportError:
    HAS_DLP = False


class DlpEngine:
    """Google Cloud Sensitive Data Protection (DLP) API in asia-south1."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "asia-south1",
    ):
        self.project_id = project_id or getattr(settings, "GCP_PROJECT_ID", None) or os.getenv("GOOGLE_CLOUD_PROJECT", "workkbot-dev")
        self.location = location
        self.enabled = os.getenv("ENABLE_LIVE_DLP", "false").lower() in ("true", "1")
        self._client: Optional[Any] = None
        self._init_client()

    def _init_client(self) -> None:
        if not HAS_DLP:
            logger.warning("google-cloud-dlp not installed or import error.")
            return

        try:
            self._client = dlp_v2.DlpServiceClient()
            logger.info("Google Cloud DLP client initialized for location: %s", self.location)
        except Exception as e:
            logger.warning("Google Cloud DLP client initialization skipped (no ADC / offline): %s", e)
            self._client = None

    def inspect_text(
        self,
        text: str,
        info_types: Optional[List[str]] = None,
        timeout: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """
        Calls Google Cloud DLP API inspect_content in asia-south1.
        Returns a list of findings matching start/end/entity_type.
        """
        if not self.enabled or not self._client or not text:
            return []

        target_info_types = info_types or [
            "INDIA_AADHAAR_NUMBER",
            "INDIA_PAN_NUMBER",
            "INDIA_GST_NUMBER",
        ]

        parent = f"projects/{self.project_id}/locations/{self.location}"
        inspect_config = {
            "info_types": [{"name": it} for it in target_info_types],
            "include_quote": True,
            "min_likelihood": dlp_v2.Likelihood.LIKELY,
        }
        item = {"value": text}

        try:
            response = self._client.inspect_content(
                request={
                    "parent": parent,
                    "inspect_config": inspect_config,
                    "item": item,
                },
                timeout=timeout,
            )

            findings: List[Dict[str, Any]] = []
            if response.result and response.result.findings:
                for finding in response.result.findings:
                    quote = finding.quote or ""
                    # Locate position in text
                    start_pos = text.find(quote) if quote else 0
                    end_pos = start_pos + len(quote) if start_pos != -1 else 0

                    findings.append({
                        "start": start_pos,
                        "end": end_pos,
                        "entity_type": finding.info_type.name,
                        "text": quote,
                        "score": 0.95,
                    })
            return findings

        except Exception as e:
            logger.warning("Cloud DLP inspection API error (%s); falling back to Presidio", e)
            return []


# Global singleton
dlp_engine = DlpEngine()
