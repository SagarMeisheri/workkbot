"""Integration test for Supabase Atomic DSR Cascading Erasure (VAL-03.6)."""
import pytest
import uuid
from src.auth.client import supabase_admin, _local_db, _local_vault
from src.compliance.dsr_service import dsr_service
from src.compliance.session_pii_vault import session_pii_vault


def test_dsr_erasure_cascade_purges_all_user_data():
    """Validates that execute_dsr_erasure purges all tables, sessions, events, and vault secrets."""
    user_id = str(uuid.uuid4())
    org_id = str(uuid.uuid4())
    secret_id = f"sec_{uuid.uuid4().hex[:8]}"

    # 1. Populate test data across all stores
    _local_db.setdefault("profiles", []).append({"id": user_id, "org_id": org_id, "email": "delete_me@corp.in"})
    _local_db.setdefault("user_consents", []).append({"id": str(uuid.uuid4()), "user_id": user_id, "org_id": org_id})
    _local_db.setdefault("conversations", []).append({"id": str(uuid.uuid4()), "user_id": user_id, "org_id": org_id})
    _local_db.setdefault("adk_sessions", []).append({"id": f"sess_{user_id}", "user_id": user_id, "org_id": org_id})
    _local_db.setdefault("adk_events", []).append({"id": f"evt_{user_id}", "session_id": f"sess_{user_id}", "user_id": user_id})
    _local_db.setdefault("ai_content_reports", []).append({"id": str(uuid.uuid4()), "user_id": user_id, "org_id": org_id})
    _local_db.setdefault("mcp_connections", []).append({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "org_id": org_id,
        "vault_secret_id": secret_id,
    })
    _local_vault[secret_id] = {"secret": "oauth_token_abc", "user_id": user_id}

    # Setup session vault token
    session_pii_vault.get_or_create_token(user_id, "sensitive_data@corp.in", "EMAIL_ADDRESS")
    assert session_pii_vault.get_session_tokens(user_id) != {}

    # 2. Execute DSR Erasure
    result = dsr_service.execute_dsr_erasure(user_id, org_id)

    assert result["success"] is True
    assert result["status"] == "dsr_erasure_completed"

    # 3. Assert zero residual data in any local/Supabase store
    assert not any(p["id"] == user_id for p in _local_db["profiles"])
    assert not any(c["user_id"] == user_id for c in _local_db["user_consents"])
    assert not any(c["user_id"] == user_id for c in _local_db["conversations"])
    assert not any(s["user_id"] == user_id for s in _local_db["adk_sessions"])
    assert not any(e.get("user_id") == user_id for e in _local_db["adk_events"])
    assert not any(r["user_id"] == user_id for r in _local_db["ai_content_reports"])
    assert not any(m["user_id"] == user_id for m in _local_db["mcp_connections"])
    assert secret_id not in _local_vault

    # RAM vault must be purged
    assert session_pii_vault.get_session_tokens(user_id) == {}
