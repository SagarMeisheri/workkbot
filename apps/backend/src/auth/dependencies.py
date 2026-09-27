"""FastAPI security dependencies validating Supabase JWTs."""
from typing import Annotated, Optional
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.config import settings

security_bearer = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    id: str
    email: str
    org_id: str
    role: str = "member"


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> CurrentUser:
    """Validates Supabase JWT and resolves current authenticated user context."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    try:
        # Decode and verify Supabase JWT
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        # In Supabase JWT, custom app_metadata or user_metadata holds org_id and role
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
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired JWT: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
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
