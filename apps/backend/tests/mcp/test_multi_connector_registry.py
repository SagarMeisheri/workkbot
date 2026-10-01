"""Tests for Multi-Connector Registry & BaseConnectorAdapter Framework (Spec 04 & Spec 05)."""
import pytest
import time
from unittest.mock import AsyncMock, patch

from src.mcp.registry import (
    connector_registry,
    BaseConnectorAdapter,
    GoogleWorkspaceAdapter,
    ZohoWorkplaceAdapter,
    GenericMcpAdapter,
)
from src.mcp.tools import get_active_provider_token
from src.auth.client import _local_db, _local_vault, supabase_admin


def test_registry_contains_default_providers():
    """Validates that registry contains Google, Zoho, and standard catalog seeds."""
    providers = connector_registry.list_providers()
    assert "google_workspace" in providers
    assert "zoho_workplace" in providers
    assert "slack" in providers
    assert "notion" in providers
    assert "atlassian" in providers


def test_registry_dynamic_fallback():
    """Unregistered provider dynamically gets a GenericMcpAdapter instance."""
    adapter = connector_registry.get("linear_workspace")
    assert isinstance(adapter, GenericMcpAdapter)
    assert adapter.provider_id == "linear_workspace"


def test_zoho_adapter_in_data_residency():
    """Verifies Zoho Workplace adapter targets Indian .in datacenter for DPDP Act 2023."""
    zoho = connector_registry.get("zoho_workplace")
    assert isinstance(zoho, ZohoWorkplaceAdapter)
    auth_url = zoho.build_authorize_url(state="test_state", redirect_uri="http://localhost:8000/cb")
    assert "accounts.zoho.in" in auth_url
    assert "ZohoBooks.invoices.READ" in auth_url
    assert "test_state" in auth_url


@pytest.mark.asyncio
async def test_zoho_adapter_exchange_and_revoke():
    """Verifies Zoho code exchange and token revocation contract."""
    zoho = connector_registry.get("zoho_workplace")
    tokens = await zoho.exchange_code("mock_zoho_code_123", "http://localhost:8000/cb")
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "Bearer"

    # Revoke
    revoked = await zoho.revoke_token(tokens["refresh_token"])
    assert revoked is True


@pytest.mark.asyncio
async def test_get_active_provider_token_multi_tenant():
    """Verifies get_active_provider_token correctly decrypts tokens for distinct providers."""
    user_id = "test-multi-user-1"
    google_secret_id = "sec-goog-1"
    zoho_secret_id = "sec-zoho-1"

    # Store secrets in Vault
    _local_vault[google_secret_id] = {
        "id": google_secret_id,
        "data": {
            "access_token": "ya29.google_live_token",
            "obtained_at": int(time.time()),
            "expires_in": 3600,
        },
    }
    _local_vault[zoho_secret_id] = {
        "id": zoho_secret_id,
        "data": {
            "access_token": "1000.zoho_live_token",
            "obtained_at": int(time.time()),
            "expires_in": 3600,
        },
    }

    _local_db["mcp_connections"].extend([
        {
            "id": "conn-g1",
            "user_id": user_id,
            "org_id": "test-org",
            "provider": "google_workspace",
            "vault_secret_id": google_secret_id,
            "status": "active",
        },
        {
            "id": "conn-z1",
            "user_id": user_id,
            "org_id": "test-org",
            "provider": "zoho_workplace",
            "vault_secret_id": zoho_secret_id,
            "status": "active",
        },
    ])

    # Fetch tokens
    g_tok = await get_active_provider_token("google_workspace", user_id)
    z_tok = await get_active_provider_token("zoho_workplace", user_id)
    missing_tok = await get_active_provider_token("slack", user_id)

    assert g_tok == "ya29.google_live_token"
    assert z_tok == "1000.zoho_live_token"
    assert missing_tok is None
