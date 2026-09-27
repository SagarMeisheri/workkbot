"""
Workkbot Local PoC: Background FastAPI Webhook Server
Listens on http://localhost:8000 for external event triggers from Google Workspace
(Cloud Pub/Sub push) and Zoho Suite (CRM, Books, Desk webhooks).
"""
import datetime
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

logger = logging.getLogger("workkbot.webhooks")
app = FastAPI(
    title="Workkbot Inbound Webhook Listener",
    description="Captures external Google & Zoho trigger events for Google ADK 2.0 dispatch.",
    version="1.0.0",
)

# In-memory webhook event log for Streamlit auditing
WEBHOOK_EVENTS_LOG: List[Dict[str, Any]] = []


class WebhookStatus(BaseModel):
    status: str
    total_received: int
    latest_event: Optional[Dict[str, Any]] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "workkbot_webhook_server", "port": 8000}


@app.get("/webhooks/events", response_model=List[Dict[str, Any]])
def get_webhook_events():
    return WEBHOOK_EVENTS_LOG[-50:]


@app.post("/webhooks/zoho/{module}")
async def handle_zoho_webhook(module: str, request: Request):
    """
    Receives inbound Zoho CRM, Books, or Desk webhook payloads.
    """
    try:
        payload = await request.json()
    except Exception:
        body = await request.body()
        payload = {"raw_payload": body.decode("utf-8", errors="replace")}

    event_record = {
        "id": f"evt_zh_{len(WEBHOOK_EVENTS_LOG) + 1}",
        "source": "zoho",
        "module": module,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "payload": payload,
        "status": "dispatched_to_adk",
    }
    WEBHOOK_EVENTS_LOG.append(event_record)
    logger.info(f"Received Zoho webhook for module '{module}': {event_record['id']}")
    return {"status": "accepted", "event_id": event_record["id"], "module": module}


@app.post("/webhooks/google/gmail")
async def handle_gmail_pubsub(request: Request):
    """
    Receives Google Cloud Pub/Sub push notifications for Gmail mailbox updates.
    """
    try:
        payload = await request.json()
    except Exception:
        body = await request.body()
        payload = {"raw_payload": body.decode("utf-8", errors="replace")}

    event_record = {
        "id": f"evt_gm_{len(WEBHOOK_EVENTS_LOG) + 1}",
        "source": "google_workspace",
        "service": "gmail",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "payload": payload,
        "status": "dispatched_to_adk",
    }
    WEBHOOK_EVENTS_LOG.append(event_record)
    logger.info(f"Received Gmail push notification: {event_record['id']}")
    return {"status": "accepted", "event_id": event_record["id"]}
