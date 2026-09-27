"""VAL-01.1: Verification of Domain Whitelisting.
Unapproved domains (e.g. user@gmail.com) are rejected by the domain whitelist verification.
"""
import pytest
from src.auth.client import supabase_admin


def test_domain_whitelist_allowed():
    """Users with allowed corporate domains succeed."""
    is_valid, org_id = supabase_admin.validate_email_domain("employee@workkbot.in")
    assert is_valid is True
    assert org_id is not None

    is_valid_alt, org_id_alt = supabase_admin.validate_email_domain("ops@smbcorp.in")
    assert is_valid_alt is True
    assert org_id_alt is not None


def test_domain_whitelist_rejected_unapproved():
    """Users with consumer/unapproved domains (gmail.com, yahoo.com) are rejected."""
    is_valid_gmail, org_gmail = supabase_admin.validate_email_domain("unauthorized_user@gmail.com")
    assert is_valid_gmail is False
    assert org_gmail is None

    is_valid_unknown, org_unknown = supabase_admin.validate_email_domain("attacker@unknowndomain.xyz")
    assert is_valid_unknown is False
    assert org_unknown is None


def test_invalid_email_format():
    """Malformed emails are rejected."""
    is_valid, _ = supabase_admin.validate_email_domain("notanemail")
    assert is_valid is False
