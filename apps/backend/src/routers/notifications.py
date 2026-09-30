"""User Notifications Router with Supabase Realtime & FCM support (Spec 05, R05.4)."""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.auth.dependencies import CurrentUser, get_current_user
from src.notifications.service import notification_service

logger = logging.getLogger("workkbot.notifications_router")

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    type: str
    title: str
    body: str
    action_url: Optional[str] = None
    read_at: Optional[str] = None
    created_at: str


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lists notifications for the current authenticated user."""
    items = notification_service.list_notifications(
        user_id=current_user.id,
        org_id=current_user.org_id,
        limit=limit,
        unread_only=unread_only,
    )
    return [NotificationResponse(**item) for item in items]


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Marks a notification as read."""
    success = notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return {"success": success, "notification_id": notification_id}
