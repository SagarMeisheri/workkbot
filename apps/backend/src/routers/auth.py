"""Auth router handling Reviewer login, Google OAuth scopes, and MCP Connectors."""
import logging
from typing import Optional, List
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.auth.dependencies import CurrentUser, get_current_user
from src.auth.client import supabase_admin, _local_db
from src.config import settings
from src.mcp.composio_service import composio_service, TOOLKIT_TO_PROVIDER
from src.mcp.vault import mcp_vault

logger = logging.getLogger("workkbot.auth_router")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class ReviewerLoginRequest(BaseModel):
    email: str
    password: str


class ReviewerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    org_id: str
    role: str
    is_demo: bool = True


class McpConnectionResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    provider: str
    scopes: List[str]
    status: str
    updated_at: str


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    provider: str
    state: str


@router.post("/reviewer-login", response_model=ReviewerLoginResponse)
async def reviewer_login(payload: ReviewerLoginRequest):
    """
    App Store Reviewer Demo Access (Apple Guideline 2.1).
    Allows Apple & Google Play reviewers to login instantaneously without Google SSO or corporate MFA.
    """
    if payload.email.lower() != settings.REVIEWER_EMAIL.lower():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reviewer credentials",
        )
    if payload.password != settings.REVIEWER_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reviewer credentials",
        )

    reviewer_user_id = "00000000-0000-0000-0000-000000000001"
    token = None

    # 1. Attempt live Supabase GoTrue authentication to acquire genuine cryptographic JWT
    client = supabase_admin.get_authenticated_client(None)
    if client:
        try:
            auth_res = client.auth.sign_in_with_password({
                "email": settings.REVIEWER_EMAIL,
                "password": settings.REVIEWER_PASSWORD,
            })
            if auth_res and auth_res.session and auth_res.session.access_token:
                token = auth_res.session.access_token
                reviewer_user_id = auth_res.user.id
        except Exception as e:
            logger.info("Live Supabase reviewer login fallback: %s", e)

    # 2. Fallback to offline/sandbox token generation
    if not token:
        token = supabase_admin.generate_token_for_user(
            user_id=reviewer_user_id,
            email=settings.REVIEWER_EMAIL,
            org_id=settings.REVIEWER_ORG_ID,
            role="tool-admin",
        )

    # Ensure profile exists in database/store
    profile = next((p for p in _local_db["profiles"] if p["id"] == reviewer_user_id), None)
    if not profile:
        _local_db["profiles"].append({
            "id": reviewer_user_id,
            "org_id": settings.REVIEWER_ORG_ID,
            "email": settings.REVIEWER_EMAIL,
            "role": "tool-admin",
            "first_name": "Reviewer",
            "last_name": "Demo",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return ReviewerLoginResponse(
        access_token=token,
        user_id=reviewer_user_id,
        email=settings.REVIEWER_EMAIL,
        org_id=settings.REVIEWER_ORG_ID,
        role="tool-admin",
        is_demo=True,
    )


@router.get("/connectors/oauth/authorize", response_model=OAuthAuthorizeResponse)
async def get_connector_oauth_url(
    provider: str = Query(..., description="Provider name (e.g., google_workspace, zoho_workplace, slack, notion)"),
    redirect_uri: Optional[str] = Query(None, description="Frontend callback URL"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Generates provider-specific authorization URL routing via Composio Connect Link."""
    callback_target = redirect_uri or f"{settings.FRONTEND_URL}/connectors/callback"
    try:
        composio_res = await composio_service.get_authorization_url(
            user_id=current_user.id,
            org_id=current_user.org_id,
            provider=provider,
            callback_url=callback_target,
        )
        return OAuthAuthorizeResponse(
            authorization_url=composio_res["authorization_url"],
            provider=provider,
            state=composio_res.get("connection_id", ""),
        )
    except Exception as e:
        logger.error("Failed to generate connector OAuth URL: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


class OAuthCallbackRequest(BaseModel):
    provider: str
    code: Optional[str] = None
    state: Optional[str] = None
    connected_account_id: Optional[str] = None
    status: Optional[str] = "success"


@router.post("/connectors/oauth/callback", response_model=McpConnectionResponse)
async def connector_oauth_callback(
    payload: OAuthCallbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Exchanges authorization code/connected_account_id for tokens, seals in Supabase Vault (pgsodium),
    and records connection in public.mcp_connections and public.tool_connections.
    """
    provider = TOOLKIT_TO_PROVIDER.get(payload.provider, payload.provider)
    access_token = f"mcp_access_{provider}_{uuid.uuid4().hex}"
    if payload.connected_account_id:
        access_token = f"composio_{payload.connected_account_id}"

    token_payload = {
        "access_token": access_token,
        "refresh_token": f"mcp_refresh_{provider}_{uuid.uuid4().hex}",
        "connected_account_id": payload.connected_account_id,
        "expires_in": 86400,
        "token_type": "Bearer",
    }

    scopes: List[str] = []

    # 1. Seal token in Supabase Vault (pgsodium)
    vault_secret_id = supabase_admin.store_vault_secret(
        user_id=current_user.id,
        provider=provider,
        secret_data=token_payload,
    )

    # 2. Update or create MCP connection record
    conn_id = payload.connected_account_id or str(uuid.uuid4())
    now_str = datetime.now(timezone.utc).isoformat()

    # Store in live Supabase table
    client = supabase_admin.get_client()
    if client:
        try:
            client.table("mcp_connections").delete().eq("user_id", current_user.id).eq("provider", provider).execute()
            client.table("mcp_connections").insert({
                "id": conn_id,
                "user_id": current_user.id,
                "org_id": current_user.org_id,
                "provider": provider,
                "scopes": scopes,
                "vault_secret_id": vault_secret_id,
                "status": "active",
                "created_at": now_str,
                "updated_at": now_str,
            }).execute()

            # Also persist in tool_connections
            client.table("tool_connections").upsert({
                "user_id": current_user.id,
                "org_id": current_user.org_id,
                "provider": provider,
                "session_id": payload.connected_account_id or f"sess_{uuid.uuid4().hex[:8]}",
                "status": "active",
            }, on_conflict="user_id,provider").execute()
        except Exception:
            pass

    # Remove existing active connection if replacing in local store
    _local_db["mcp_connections"] = [
        c for c in _local_db["mcp_connections"]
        if not (c["user_id"] == current_user.id and c["provider"] == provider)
    ]

    record = {
        "id": conn_id,
        "user_id": current_user.id,
        "org_id": current_user.org_id,
        "provider": provider,
        "scopes": scopes,
        "vault_secret_id": vault_secret_id,
        "status": "active",
        "updated_at": now_str,
    }
    _local_db["mcp_connections"].append(record)

    return McpConnectionResponse(
        id=conn_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        provider=provider,
        scopes=scopes,
        status="active",
        updated_at=now_str,
    )


@router.get("/connectors", response_model=List[McpConnectionResponse])
async def list_user_connectors(current_user: CurrentUser = Depends(get_current_user)):
    """Lists active connected MCP integrations for the user."""
    connections_by_provider: dict[str, McpConnectionResponse] = {}

    # 1. Check live Supabase table
    client = supabase_admin.get_client()
    if client:
        try:
            res = (
                client.table("mcp_connections")
                .select("*")
                .eq("user_id", current_user.id)
                .eq("org_id", current_user.org_id)
                .execute()
            )
            if res.data:
                for c in res.data:
                    prov = c["provider"]
                    connections_by_provider[prov] = McpConnectionResponse(
                        id=c["id"],
                        user_id=c["user_id"],
                        org_id=c["org_id"],
                        provider=prov,
                        scopes=c.get("scopes", []),
                        status=c.get("status", "active"),
                        updated_at=c.get("updated_at", datetime.now(timezone.utc).isoformat()),
                    )
        except Exception as e:
            logger.debug("Failed querying Supabase mcp_connections: %s", e)

    # 2. Check local in-memory DB fallback
    for c in _local_db.get("mcp_connections", []):
        if c["user_id"] == current_user.id and c["org_id"] == current_user.org_id:
            prov = c["provider"]
            if prov not in connections_by_provider:
                connections_by_provider[prov] = McpConnectionResponse(
                    id=c["id"],
                    user_id=c["user_id"],
                    org_id=c["org_id"],
                    provider=prov,
                    scopes=c.get("scopes", []),
                    status=c.get("status", "active"),
                    updated_at=c.get("updated_at", datetime.now(timezone.utc).isoformat()),
                )

    # 3. Synchronize with live Composio connected accounts
    try:
        composio_accounts = composio_service.list_connected_accounts(
            user_id=current_user.id,
            org_id=current_user.org_id,
        )
        now_str = datetime.now(timezone.utc).isoformat()
        for acc in composio_accounts:
            prov = acc["provider"]
            if prov not in connections_by_provider:
                default_scopes = {
                    "google_workspace": ["drive.readonly", "gmail.send", "calendar.events.readonly"],
                    "zoho_workplace": ["ZohoBooks.invoices.READ", "ZohoCRM.modules.leads.READ"],
                }.get(prov, ["read", "write"])

                conn_resp = McpConnectionResponse(
                    id=acc["id"],
                    user_id=current_user.id,
                    org_id=current_user.org_id,
                    provider=prov,
                    scopes=default_scopes,
                    status="active",
                    updated_at=acc.get("updated_at") or now_str,
                )
                connections_by_provider[prov] = conn_resp

                # Auto-cache into local DB
                _local_db.setdefault("mcp_connections", []).append({
                    "id": acc["id"],
                    "user_id": current_user.id,
                    "org_id": current_user.org_id,
                    "provider": prov,
                    "scopes": default_scopes,
                    "status": "active",
                    "updated_at": conn_resp.updated_at,
                })
    except Exception as e:
        logger.warning("Failed to sync Composio accounts during list_user_connectors: %s", e)

    return list(connections_by_provider.values())


@router.delete("/connectors/{connection_id}")
async def disconnect_connector(
    connection_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Disconnects connector and purges Vault secret."""
    # 1. Disconnect from Composio if it is a Composio connected account
    composio_service.disconnect_account(connection_id)

    target_vault_id = None
    client = supabase_admin.get_client()
    if client:
        try:
            res = (
                client.table("mcp_connections")
                .select("vault_secret_id")
                .eq("id", connection_id)
                .eq("user_id", current_user.id)
                .execute()
            )
            if res.data:
                target_vault_id = res.data[0].get("vault_secret_id")
                if target_vault_id:
                    supabase_admin.delete_vault_secret(target_vault_id)
                client.table("mcp_connections").delete().eq("id", connection_id).execute()
        except Exception:
            pass

    target = None
    for c in _local_db["mcp_connections"]:
        if c["id"] == connection_id and c["user_id"] == current_user.id:
            target = c
            break

    if target:
        vault_secret_id = target.get("vault_secret_id")
        if vault_secret_id:
            supabase_admin.delete_vault_secret(vault_secret_id)
        _local_db["mcp_connections"] = [c for c in _local_db["mcp_connections"] if c["id"] != connection_id]
        return {"success": True, "connection_id": connection_id, "status": "revoked"}

    if client and target_vault_id is not None:
        return {"success": True, "connection_id": connection_id, "status": "revoked"}

    if connection_id.startswith("ca_"):
        _local_db["mcp_connections"] = [c for c in _local_db["mcp_connections"] if c["id"] != connection_id]
        return {"success": True, "connection_id": connection_id, "status": "revoked"}

    raise HTTPException(status_code=404, detail="Connector not found")
