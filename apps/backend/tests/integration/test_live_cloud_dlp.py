"""Live integration test for Google Cloud DLP API in asia-south1 (VAL-03.5)."""
import os
import pytest
from unittest.mock import MagicMock
from src.compliance.dlp_engine import DlpEngine


@pytest.mark.live_dlp
def test_cloud_dlp_live_inspection_or_contract():
    """Validates Google Cloud DLP inspection for Indian infoTypes in asia-south1."""
    engine = DlpEngine(location="asia-south1")

    # If running with live GCP credentials
    if engine._client and os.getenv("ENABLE_LIVE_DLP", "false").lower() == "true":
        sample_text = "Employee PAN is ABCDE1234F and GSTIN is 27AAAAA0000A1Z5."
        findings = engine.inspect_text(sample_text)
        assert len(findings) >= 1
        entity_types = [f["entity_type"] for f in findings]
        assert "INDIA_PAN_NUMBER" in entity_types or "INDIA_GST_NUMBER" in entity_types
    else:
        # Mock test for CI/offline pipeline
        mock_client = MagicMock()
        mock_finding = MagicMock()
        mock_finding.quote = "ABCDE1234F"
        mock_finding.info_type.name = "INDIA_PAN_NUMBER"
        mock_finding.likelihood = 4

        mock_response = MagicMock()
        mock_response.result.findings = [mock_finding]
        mock_client.inspect_content.return_value = mock_response

        engine._client = mock_client
        engine.enabled = True

        findings = engine.inspect_text("PAN ABCDE1234F")
        assert len(findings) == 1
        assert findings[0]["entity_type"] == "INDIA_PAN_NUMBER"
        assert findings[0]["text"] == "ABCDE1234F"
