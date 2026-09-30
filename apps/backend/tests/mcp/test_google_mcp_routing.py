"""Test VAL-04.4: Agentgateway Google Workspace MCP Routing & CEL Isolation (Spec 04)."""
import pytest
from src.auth.delegation import token_delegator
from src.auth.client import _local_db, _local_vault


@pytest.mark.asyncio
async def test_delegated_headers_with_tenant_isolation():
    """Validates that token delegation succeeds only when user and tenant IDs match."""
    user_id = "user-gw-001"
    org_id = "org-gw-001"
    secret_id = "vault-sec-001"

    # Setup local test fixtures
    _local_vault[secret_id] = {
        "id": secret_id,
        "data": {
            "access_token": "ya29.sample_valid_google_token",
            "refresh_token": "1//sample_refresh_token",
            "expires_in": 3600,
        },
    }
    _local_db["mcp_connections"].append({
        "id": "conn-gw-001",
        "user_id": user_id,
        "org_id": org_id,
        "provider": "google_workspace",
        "vault_secret_id": secret_id,
        "status": "active",
        "scopes": ["gmail.readonly", "calendar.events"],
    })

    user_jwt = "header.payload.signature"
    headers = await token_delegator.get_delegated_headers(
        user_id=user_id,
        org_id=org_id,
        provider="google_workspace",
        user_jwt=user_jwt,
    )

    assert headers["Authorization"] == f"Bearer {user_jwt}"
    assert headers["X-Upstream-Authorization"] == "Bearer ya29.sample_valid_google_token"
    assert headers["X-Workkbot-User-Id"] == user_id
    assert headers["X-Workkbot-Org-Id"] == org_id
    assert headers["X-Workkbot-Provider"] == "google_workspace"


@pytest.mark.asyncio
async def test_cross_tenant_delegation_prohibited():
    """Cross-tenant tool delegation must be strictly blocked by RLS policy."""
    user_id = "user-gw-002"
    legit_org = "org-gw-002"
    attacker_org = "org-gw-evil"
    secret_id = "vault-sec-002"

    _local_vault[secret_id] = {"id": secret_id, "data": {"access_token": "secret_token"}}
    _local_db["mcp_connections"].append({
        "id": "conn-gw-002",
        "user_id": user_id,
        "org_id": legit_org,
        "provider": "google_workspace",
        "vault_secret_id": secret_id,
        "status": "active",
    })

    with pytest.raises(PermissionError) as exc_info:
        await token_delegator.get_delegated_headers(
            user_id=user_id,
            org_id=attacker_org,  # Mismatched tenant
            provider="google_workspace",
            user_jwt="attacker_token",
        )
    assert "Cross-tenant" in str(exc_info.value)


def test_agentgateway_cel_policy_verification():
    """Simulates Agentgateway 1.5.x CEL rule verification: sub == owner && org_id == res.org_id."""
    claims = {"sub": "u123", "org_id": "o456"}
    matching_res = {"owner": "u123", "org_id": "o456"}
    mismatched_owner = {"owner": "u999", "org_id": "o456"}
    mismatched_org = {"owner": "u123", "org_id": "o999"}

    assert token_delegator.verify_cel_policy(claims, matching_res) is True
    assert token_delegator.verify_cel_policy(claims, mismatched_owner) is False
    assert token_delegator.verify_cel_policy(claims, mismatched_org) is False
