import logging
import time
from typing import Dict, Any, Optional
import httpx
import jwt
from fastapi import Header, HTTPException, status
from config import settings

logger = logging.getLogger("workkbot.auth")

GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
_cached_certs: Dict[str, str] = {}
_certs_expiry: float = 0


async def get_google_public_keys() -> Dict[str, str]:
    global _cached_certs, _certs_expiry
    now = time.time()
    if _cached_certs and now < _certs_expiry:
        return _cached_certs

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(GOOGLE_CERTS_URL)
            resp.raise_for_status()
            _cached_certs = resp.json()
            # Cache for max-age or default 1 hour
            cache_control = resp.headers.get("Cache-Control", "")
            max_age = 3600
            for part in cache_control.split(","):
                if "max-age=" in part:
                    try:
                        max_age = int(part.split("=")[1].strip())
                    except ValueError:
                        pass
            _certs_expiry = now + max_age
            return _cached_certs
    except Exception as e:
        logger.error("Failed to fetch Google public keys: %s", e)
        if _cached_certs:
            return _cached_certs
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )


async def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verifies Google Cloud Identity Platform (GCIP) / Firebase Auth OIDC JWT token.
    Returns authenticated user ID.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    # In test mode or when running automated unit tests with test keys
    if settings.TEST_MODE and token.startswith("test_user_"):
        return token.replace("test_user_", "")

    try:
        # Decode header without verification to obtain kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header missing key identifier (kid)"
            )

        public_keys = await get_google_public_keys()
        cert_pem = public_keys.get(kid)
        if not cert_pem:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token key identifier"
            )

        expected_issuer = f"https://securetoken.google.com/{settings.PROJECT_ID}"
        decoded = jwt.decode(
            token,
            cert_pem,
            algorithms=["RS256"],
            audience=settings.PROJECT_ID,
            issuer=expected_issuer,
        )
        user_id = decoded.get("user_id") or decoded.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user subject"
            )
        return user_id

    except jwt.PyJWTError as e:
        logger.warning("Token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
