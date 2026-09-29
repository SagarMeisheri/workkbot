"""Unit and live tests for CERT-In Compliant Structured Security Logging (VAL-03.8)."""
import json
import pytest
from unittest.mock import MagicMock
from src.compliance.cert_in_logger import CertInLogger, cert_in_logger


def test_cert_in_structured_payload_format():
    """Validates that CERT-In logger emits the exact statutory JSON fields."""
    logger_instance = CertInLogger(log_name="test-security-sink")

    payload = logger_instance.log_security_event(
        event_type="PII_REDACTION_APPLIED",
        user_id="user_test_99",
        org_id="org_test_99",
        session_id="sess_123",
        details={"detected_count": 3, "entities": ["INDIA_PAN", "INDIA_AADHAAR"]},
        severity="WARNING",
    )

    assert payload["cert_in_version"] == "2026.04"
    assert "CERT-In Directions 2022" in payload["regulatory_framework"]
    assert "DPDP Act 2023 Rule 6" in payload["regulatory_framework"]
    assert payload["event_type"] == "PII_REDACTION_APPLIED"
    assert payload["severity"] == "WARNING"
    assert payload["user_id"] == "user_test_99"
    assert payload["org_id"] == "org_test_99"
    assert payload["session_id"] == "sess_123"
    assert payload["details"]["detected_count"] == 3


def test_cert_in_gcp_cloud_logging_integration():
    """Validates dispatch to Google Cloud Logging logger.log_struct when client present."""
    logger_instance = CertInLogger(log_name="test-gcp-sink")
    mock_gcp_logger = MagicMock()
    logger_instance._gcp_logger = mock_gcp_logger

    logger_instance.log_security_event(
        event_type="DSR_ERASURE_EXECUTED",
        user_id="user_purge_1",
        org_id="org_purge_1",
        details={"purged_records": 12},
    )

    assert mock_gcp_logger.log_struct.called
    call_args, call_kwargs = mock_gcp_logger.log_struct.call_args
    struct_payload = call_args[0]
    assert struct_payload["event_type"] == "DSR_ERASURE_EXECUTED"
    assert call_kwargs.get("severity") == "INFO"
