"""Unit tests for Reversible Tokenization & Session PII Vault Lifecycle (VAL-03.2)."""
import pytest
from src.compliance.session_pii_vault import SessionPiiVault
from src.compliance.callbacks.pii_anonymize_callback import anonymize_text


def test_session_pii_vault_basic_lifecycle():
    """Validates token creation, rehydration, and session purging."""
    vault = SessionPiiVault()
    session_id = "test_sess_01"

    # 1. Assign tokens
    token1 = vault.get_or_create_token(session_id, "rahul@acme.in", "EMAIL_ADDRESS")
    token2 = vault.get_or_create_token(session_id, "ABCDE1234F", "INDIA_PAN")

    assert token1.startswith("<EMAIL_")
    assert token2.startswith("<IN_PAN_")

    # 2. Idempotency within same session
    token1_dup = vault.get_or_create_token(session_id, "rahul@acme.in", "EMAIL_ADDRESS")
    assert token1 == token1_dup

    # 3. Rehydrate text
    raw_prompt = f"Invoice for {token1} with PAN {token2}"
    restored = vault.rehydrate_text(session_id, raw_prompt)
    assert restored == "Invoice for rahul@acme.in with PAN ABCDE1234F"

    # 4. Rehydrate dictionary
    tool_args = {"recipient": token1, "tax_id": token2, "amount": 5000}
    rehydrated_args = vault.rehydrate_dict(session_id, tool_args)
    assert rehydrated_args["recipient"] == "rahul@acme.in"
    assert rehydrated_args["tax_id"] == "ABCDE1234F"
    assert rehydrated_args["amount"] == 5000

    # 5. Purge session
    vault.purge_session(session_id)
    assert vault.get_session_tokens(session_id) == {}


def test_session_isolation():
    """Validates that different sessions maintain isolated token namespaces."""
    vault = SessionPiiVault()
    sess_a = "sess_a"
    sess_b = "sess_b"

    token_a = vault.get_or_create_token(sess_a, "alice@work.in", "EMAIL_ADDRESS")
    token_b = vault.get_or_create_token(sess_b, "bob@work.in", "EMAIL_ADDRESS")

    # Both are first email in their session
    assert token_a == "<EMAIL_1>"
    assert token_b == "<EMAIL_1>"

    # Rehydration in sess_a produces Alice, in sess_b produces Bob
    assert vault.rehydrate_text(sess_a, "Email <EMAIL_1>") == "Email alice@work.in"
    assert vault.rehydrate_text(sess_b, "Email <EMAIL_1>") == "Email bob@work.in"


def test_end_to_end_anonymize_text():
    """Tests the full text anonymization pipeline returning sanitized text and mapping."""
    session_id = "turn_session_100"
    raw_text = "Send tax clearance to rahul@acme.in with PAN ABCDE1234F."

    sanitized, token_map = anonymize_text(session_id, raw_text)

    # Raw PII must NOT appear in sanitized text
    assert "rahul@acme.in" not in sanitized
    assert "ABCDE1234F" not in sanitized

    # Surrogate tokens must be present
    assert "<EMAIL_1>" in sanitized
    assert "<IN_PAN_1>" in sanitized
    assert token_map["<EMAIL_1>"] == "rahul@acme.in"
    assert token_map["<IN_PAN_1>"] == "ABCDE1234F"
