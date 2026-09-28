"""FastAPI security dependencies validating Supabase JWTs."""
import ssl
from typing import Annotated, Optional
import certifi
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.config import settings

security_bearer = HTTPBearer(auto_error=False)

_jwks_client: Optional[PyJWKClient] = None

def _get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and settings.SUPABASE_URL:
        try:
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            _jwks_client = PyJWKClient(jwks_url, ssl_context=ssl_ctx)
        except Exception:
            _jwks_client = None
    return _jwks_client


class CurrentUser(BaseModel):
    id: str
    email: str
    org_id: str
    role: str = "member"
    token: Optional[str] = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> CurrentUser:
    """Validates Supabase JWT (ES256 via JWKS or HS256) and resolves current user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = None

    # 1. Try decoding with unverified header inspection to check alg
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        
        if alg == "ES256":
            jwks = _get_jwks_client()
            if jwks:
                signing_key = jwks.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256"],
                    options={"verify_aud": False},
                )
    except Exception:
        payload = None

    # 2. Fallback to HS256 verification using SUPABASE_JWT_SECRET
    if payload is None:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired JWT: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
    user_id = payload.get("sub")
    email = payload.get("email")
    app_metadata = payload.get("app_metadata", {})
    user_metadata = payload.get("user_metadata", {})
    
    org_id = (
        payload.get("org_id")
        or app_metadata.get("org_id")
        or user_metadata.get("org_id")
        or "a0000000-0000-0000-0000-000000000001"
    )
    role = (
        payload.get("role")
        or app_metadata.get("role")
        or user_metadata.get("role")
        or "member"
    )
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub or email",
        )
        
    return CurrentUser(
        id=str(user_id),
        email=str(email),
        org_id=str(org_id),
        role=str(role),
        token=token,
    )


def require_role(allowed_roles: list[str]):
    """Enforces specific role membership."""
    async def role_checker(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized. Required: {allowed_roles}",
            )
        return current_user
    return role_checker
