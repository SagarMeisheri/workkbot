import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from db import init_db_pool, close_db_pool, get_connection
from auth import verify_token
from session.cloud_sql_session_service import CloudSqlSessionService, Session, Event

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("workkbot.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Workkbot Sovereign Backend in region: %s", settings.REGION)
    # Ensure region invariant
    if settings.REGION != "asia-south1":
        raise RuntimeError(f"Sovereignty violation: Region must be asia-south1, got {settings.REGION}")
    
    # Initialize DB connection pool
    try:
        await init_db_pool()
    except Exception as e:
        logger.warning("Database connection pool initialization deferred: %s", e)
    
    yield
    
    # Clean shutdown
    await close_db_pool()
    logger.info("Workkbot Backend shutdown complete.")


app = FastAPI(
    title="Workkbot Sovereign Enterprise AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restricted in production through Cloud Armor / API Gateway
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = CloudSqlSessionService()


# Pydantic Request Models
class CreateSessionRequest(BaseModel):
    app_name: str = "workkbot"
    initial_state: Optional[Dict[str, Any]] = None


class UpdateSessionStateRequest(BaseModel):
    state_delta: Dict[str, Any]


class AppendEventRequest(BaseModel):
    event_type: str
    content: Dict[str, Any]


class ConsentLogRequest(BaseModel):
    consent_type: str  # 'CORE_CHAT', 'WORKSPACE_INTEGRATION', 'ZOHO_INTEGRATION'
    status: str        # 'GRANTED', 'REVOKED'
    notice_version: str
    ip_address_hash: Optional[str] = None
    user_agent: Optional[str] = None


# --- Health & Sovereign Status Endpoint ---
@app.get("/health", tags=["Health"])
async def get_health():
    """
    Sovereign Region Health Endpoint
    Explicitly affirms execution within asia-south1 (Mumbai) per B1-G3 gate.
    """
    return {
        "status": "healthy",
        "region": settings.REGION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Session Management Endpoints ---
@app.post("/sessions", response_model=Session, tags=["Sessions"])
async def create_session(
    req: CreateSessionRequest,
    user_id: str = Depends(verify_token)
):
    try:
        session = await session_service.create_session(
            user_id=user_id,
            app_name=req.app_name,
            initial_state=req.initial_state
        )
        return session
    except Exception as e:
        logger.error("Failed to create session: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}", response_model=Session, tags=["Sessions"])
async def get_session(
    session_id: str,
    user_id: str = Depends(verify_token)
):
    session = await session_service.get_session(session_id=session_id, user_id=user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found or expired"
        )
    return session


@app.patch("/sessions/{session_id}/state", response_model=Session, tags=["Sessions"])
async def update_session_state(
    session_id: str,
    req: UpdateSessionStateRequest,
    user_id: str = Depends(verify_token)
):
    try:
        session = await session_service.update_session_state(
            session_id=session_id,
            user_id=user_id,
            state_delta=req.state_delta
        )
        return session
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error("Failed to update session state: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/events", response_model=Event, tags=["Events"])
async def append_event(
    session_id: str,
    req: AppendEventRequest,
    user_id: str = Depends(verify_token)
):
    try:
        event = await session_service.append_event(
            session_id=session_id,
            user_id=user_id,
            event_type=req.event_type,
            content=req.content
        )
        return event
    except Exception as e:
        logger.error("Failed to append event: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/events", response_model=List[Event], tags=["Events"])
async def list_events(
    session_id: str,
    user_id: str = Depends(verify_token)
):
    try:
        return await session_service.list_events(session_id=session_id, user_id=user_id)
    except Exception as e:
        logger.error("Failed to list events: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- Consent Logging (DPDP Act Compliance) ---
@app.post("/consent", status_code=status.HTTP_201_CREATED, tags=["Consent"])
async def record_consent(
    req: ConsentLogRequest,
    user_id: str = Depends(verify_token)
):
    query = """
        INSERT INTO public.consent_logs (
            user_id, consent_type, status, notice_version, ip_address_hash, user_agent, created_at
        )
        VALUES ($1::uuid, $2, $3, $4, $5, $6, timezone('utc', now()))
        RETURNING id, user_id, consent_type, status, notice_version, created_at;
    """
    async with get_connection(user_id=user_id) as conn:
        row = await conn.fetchrow(
            query,
            user_id,
            req.consent_type,
            req.status,
            req.notice_version,
            req.ip_address_hash,
            req.user_agent,
        )
    return dict(row)
