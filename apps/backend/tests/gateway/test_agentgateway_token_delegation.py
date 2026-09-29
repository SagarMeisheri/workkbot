"""VAL-01.8: Agentgateway Token Delegation & CEL Policy Evaluation.
Verifies token delegation retrieves decrypted tokens and enforces CEL sub == owner.
"""
import pytest
from src.auth.delegation import token_delegator
from src.auth.client import supabase_admin, _local_db


@pytest.mark.asyncio
async def test_delegation_retrieves_headers_and_injects_token():
    """Delegation retrieves vault secret and constructs Agentgateway session headers."""
    user_id = "user_delegation_1"
    org_id = "a0000000-0000-0000-0000-000000000001"
    token = supabase_admin.generate_token_for_user(user_id=user_id, email="delegation@workkbot.in", org_id=org_id)

    # Store a secret in Vault
    secret_id = supabase_admin.store_vault_secret(
        user_id=user_id,
        provider="google_workspace",
        secret_data={"access_token": "ya29.live_google_workspace_access_token_xyz"},
    )

    # Register active connection
    _local_db["mcp_connections"].append({
        "id": "conn_delegation_1",
        "user_id": user_id,
        "org_id": org_id,
        "provider": "google_workspace",
        "scopes": ["drive.readonly"],
        "vault_secret_id": secret_id,
        "status": "active",
        "updated_at": "2026-09-27T10:00:00Z",
    })

    # Retrieve delegated headers
    headers = await token_delegator.get_delegated_headers(
        user_id=user_id,
        org_id=org_id,
        provider="google_workspace",
        user_jwt=token,
    )

    assert headers["Authorization"] == f"Bearer {token}"
    assert headers["X-Upstream-Authorization"] == "Bearer ya29.live_google_workspace_access_token_xyz"
    assert headers["X-Workkbot-User-Id"] == user_id
    assert headers["X-Workkbot-Org-Id"] == org_id


def test_agentgateway_cel_policy_evaluation():
    """Agentgateway CEL policy allows matching owner and denies cross-user access."""
    # 1. Matching owner -> ALLOW
    claims_valid = {"sub": "user_123", "org_id": "org_456"}
    resource_valid = {"owner": "user_123", "org_id": "org_456"}
    assert token_delegator.verify_cel_policy(claims_valid, resource_valid) is True

    # 2. Mismatched user sub -> DENY
    claims_spoofed = {"sub": "attacker_999", "org_id": "org_456"}
    assert token_delegator.verify_cel_policy(claims_spoofed, resource_valid) is False

    # 3. Mismatched tenant org_id -> DENY
    claims_cross_tenant = {"sub": "user_123", "org_id": "other_org_777"}
    assert token_delegator.verify_cel_policy(claims_cross_tenant, resource_valid) is False
