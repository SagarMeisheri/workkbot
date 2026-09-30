"""Firebase Cloud Messaging (FCM) Client for Mobile Push Notifications (Spec 05, R05.4).

Dispatches background push alerts to Android and iOS Expo devices:
- Includes deep links (e.g. workkbot://chat/:conversation_id?approval_id=:id)
- Respects mobile power management (priority=high for HITL approvals)
- Logs structured telemetry to Google Cloud Logging
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from src.config import settings

logger = logging.getLogger("workkbot.notifications.fcm")

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FCM_SDK_AVAILABLE = True
except ImportError:
    FCM_SDK_AVAILABLE = False


class FcmNotificationService:
    """Dispatches FCM push alerts to mobile clients."""

    def __init__(self):
        self._initialized = False
        self._dispatched_messages: List[Dict[str, Any]] = []
        self._init_firebase()

    def _init_firebase(self):
        if not FCM_SDK_AVAILABLE:
            logger.debug("Firebase Admin SDK not installed, using mock FCM dispatcher")
            return

        try:
            if not firebase_admin._apps:
                cred_path = getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", None)
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    self._initialized = True
                else:
                    # Initialize default credentials if in Cloud Run environment
                    firebase_admin.initialize_app()
                    self._initialized = True
        except Exception as e:
            logger.debug("FCM initialization skipped: %s", e)

    def dispatch_push_notification(
        self,
        fcm_token: str,
        title: str,
        body: str,
        deep_link: Optional[str] = None,
        data: Optional[Dict[str, str]] = None,
        is_high_priority: bool = True,
    ) -> Dict[str, Any]:
        """
        Dispatches FCM push message to a device.
        """
        payload_data = dict(data or {})
        if deep_link:
            payload_data["deep_link"] = deep_link

        message_record = {
            "token": fcm_token,
            "title": title,
            "body": body,
            "data": payload_data,
            "priority": "high" if is_high_priority else "normal",
        }
        self._dispatched_messages.append(message_record)

        if self._initialized and FCM_SDK_AVAILABLE:
            try:
                android_config = messaging.AndroidConfig(
                    priority="high" if is_high_priority else "normal",
                    notification=messaging.AndroidNotification(click_action=deep_link),
                )
                apns_config = messaging.APNSConfig(
                    headers={"apns-priority": "10" if is_high_priority else "5"},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", category="HITL_APPROVAL")
                    ),
                )
                msg = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in payload_data.items()},
                    token=fcm_token,
                    android=android_config,
                    apns=apns_config,
                )
                response = messaging.send(msg)
                logger.info("Successfully sent FCM message: %s", response)
                return {"status": "sent", "message_id": response}
            except Exception as e:
                logger.warning("FCM live dispatch failed: %s; recorded in mock buffer", e)

        return {"status": "mock_sent", "record": message_record}

    def get_dispatched_messages(self) -> List[Dict[str, Any]]:
        """Returns dispatched messages for test inspection."""
        return list(self._dispatched_messages)

    def clear_dispatched_messages(self) -> None:
        self._dispatched_messages.clear()


fcm_service = FcmNotificationService()
