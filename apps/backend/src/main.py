"""Workkbot Cloud Run Backend Entrypoint."""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.auth.dependencies import CurrentUser, get_current_user
from src.auth.client import _MOCK_DB
from src.routers.auth import router as auth_router
from src.routers.consent import router as consent_router
from src.routers.account import router as account_router

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Enterprise Identity, Connectors Hub & DPDP Consent API",
)

# CORS Configuration for apps/web and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(consent_router)
app.include_router(account_router)


@app.get("/healthz", tags=["health"])
async def health_check():
    """Liveness probe for Cloud Run container."""
    return {
        "status": "healthy",
        "service": "workkbot-backend",
        "region": "asia-south1",
        "environment": settings.ENVIRONMENT,
    }


class ChatRequest(BaseModel):
    message: str


@app.post("/api/v1/chat", tags=["chat"])
async def chat_endpoint(
    payload: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Core conversational endpoint gated by DPDP statutory consent (VAL-01.4).
    If the user has not signed statutory consent, aborts with HTTP 403.
    """
    consent = next(
        (c for c in _MOCK_DB["user_consents"]
         if c["user_id"] == current_user.id and c["status"] == "active"),
        None
    )
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DPDP statutory consent required before initiating conversation",
        )

    return {
        "reply": f"Hello {current_user.email}! Received: {payload.message}",
        "user_id": current_user.id,
        "org_id": current_user.org_id,
    }
