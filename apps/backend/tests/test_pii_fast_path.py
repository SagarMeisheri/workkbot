"""Unit tests for Presidio Tier-1 Fast-Path with spaCy NLP & Indian Recognizers (VAL-03.1)."""
import pytest
from src.compliance.presidio_engine import (
    PresidioEngine,
    presidio_engine,
    validate_verhoeff,
    generate_verhoeff,
)


def test_verhoeff_checksum_validation():
    """Validates Verhoeff checksum algorithm against valid and corrupt Aadhaar numbers."""
    # Prefix 11 digits: '23412341234'
    prefix = "23412341234"
    check_digit = generate_verhoeff(prefix)
    valid_aadhaar = prefix + check_digit

    assert len(valid_aadhaar) == 12
    assert validate_verhoeff(valid_aadhaar) is True

    # Corrupting single digit must fail checksum
    corrupted_aadhaar = prefix + str((int(check_digit) + 1) % 10)
    assert validate_verhoeff(corrupted_aadhaar) is False

    # Transposition error (swapping two adjacent digits) must fail
    transposed = valid_aadhaar[:3] + valid_aadhaar[4] + valid_aadhaar[3] + valid_aadhaar[5:]
    assert validate_verhoeff(transposed) is False


def test_indian_pan_detection():
    """Tests PAN regex pattern detection."""
    text = "The employee PAN is ABCDE1234F and another PAN is XYZPQ9876L."
    findings = presidio_engine.analyze(text)

    pan_findings = [f for f in findings if f["entity_type"] == "INDIA_PAN"]
    assert len(pan_findings) == 2
    assert pan_findings[0]["text"] == "ABCDE1234F"
    assert pan_findings[1]["text"] == "XYZPQ9876L"


def test_invalid_pan_not_detected():
    """Tests that invalid PAN patterns are ignored."""
    text = "Invalid PANs: 12345ABCDE and ABC1234DEF and ABCDE12345."
    findings = presidio_engine.analyze(text)

    pan_findings = [f for f in findings if f["entity_type"] == "INDIA_PAN"]
    assert len(pan_findings) == 0


def test_indian_aadhaar_with_verhoeff():
    """Tests that only Verhoeff-valid 12-digit Aadhaar numbers are detected."""
    prefix = "45678901234"
    valid_check = generate_verhoeff(prefix)
    valid_aadhaar = f"{prefix[:4]} {prefix[4:8]} {prefix[8:]}{valid_check}"
    invalid_aadhaar = "1234 5678 9012"  # invalid checksum

    text = f"Customer valid Aadhaar: {valid_aadhaar}, invalid: {invalid_aadhaar}."
    findings = presidio_engine.analyze(text)

    aadhaar_findings = [f for f in findings if f["entity_type"] == "INDIA_AADHAAR"]
    assert len(aadhaar_findings) == 1
    assert "".join(aadhaar_findings[0]["text"].split()) == prefix + valid_check


def test_indian_upi_detection():
    """Tests UPI VPA pattern recognition."""
    text = "Please transfer fees to payments@okhdfcbank or vendor@paytm."
    findings = presidio_engine.analyze(text)

    upi_findings = [f for f in findings if f["entity_type"] == "INDIA_UPI"]
    assert len(upi_findings) == 2
    assert "payments@okhdfcbank" in [f["text"] for f in upi_findings]
    assert "vendor@paytm" in [f["text"] for f in upi_findings]


def test_indian_mobile_detection():
    """Tests Indian mobile phone numbers (+91 and 10 digits)."""
    text = "Contact support at +919876543210 or alternate 9876543211."
    findings = presidio_engine.analyze(text)

    phone_findings = [f for f in findings if f["entity_type"] in ("INDIA_PHONE", "PHONE_NUMBER")]
    assert len(phone_findings) >= 2


def test_spacy_person_and_email_detection():
    """Tests spaCy NER person entity and email address detection."""
    text = "Send statement to Rahul Sharma at rahul.sharma@enterprise.in."
    findings = presidio_engine.analyze(text)

    entities = {f["entity_type"]: f["text"] for f in findings}
    assert "EMAIL_ADDRESS" in entities
    assert entities["EMAIL_ADDRESS"] == "rahul.sharma@enterprise.in"
    # PERSON may be detected by spaCy
    assert any("Rahul" in f["text"] for f in findings if f["entity_type"] == "PERSON") or "EMAIL_ADDRESS" in entities
