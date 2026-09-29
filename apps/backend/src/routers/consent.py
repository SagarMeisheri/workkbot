"""DPDP Act 2023 Statutory Consent & AI Disclosure Router."""
from datetime import datetime, timezone
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.auth.dependencies import CurrentUser, get_current_user
from src.auth.client import supabase_admin, _local_db
from src.config import settings

logger = logging.getLogger("workkbot.consent")
router = APIRouter(prefix="/api/v1/consent", tags=["consent"])

DPDP_DISCLOSURES_EN = [
    "Conversations and tool calls will be processed by AI models to assist with your daily workflows.",
    "Connected workspace tools (Google, Zoho, ERPs) will be queried based on your explicit instructions.",
    "Derived facts and work preferences will be stored in semantic memory to personalize responses.",
    "You retain the statutory Right to Access, Correct, and Erase your personal data at any time.",
]

DPDP_DISCLOSURES_HI = [
    "आपकी बातचीत और टूल कॉल्स को दैनिक कार्यप्रवाह में सहायता के लिए AI मॉडल द्वारा प्रोसेस किया जाएगा।",
    "आपके कार्यक्षेत्र के कनेक्टेड टूल्स (गूगल, ज़ोहो, ERP) को आपके स्पष्ट निर्देशानुसार एक्सेस किया जाएगा।",
    "व्यक्तिगत अनुभव के लिए महत्वपूर्ण तथ्य और प्राथमिकताएं मेमोरी में सुरक्षित रखी जाएंगी।",
    "आपको किसी भी समय अपने व्यक्तिगत डेटा को देखने, सुधारने और पूरी तरह मिटाने का कानूनी अधिकार प्राप्त है।",
]


class ConsentStatusResponse(BaseModel):
    has_consented: bool
    consent_version: str
    consented_at: Optional[str] = None
    language: Optional[str] = None


class RecordConsentRequest(BaseModel):
    consent_version: str = Field(default=settings.CURRENT_CONSENT_VERSION)
    language: str = Field(default="en", pattern="^(en|hi)$")
    accepted_disclosures: List[str]


class RecordConsentResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    consent_version: str
    language: str
    consented_at: str
    status: str = "active"


@router.get("/status", response_model=ConsentStatusResponse)
async def get_consent_status(current_user: CurrentUser = Depends(get_current_user)):
    """Checks whether the authenticated user has active statutory consent."""
    client = supabase_admin.get_client()
    if client:
        try:
            res = (
                client.table("user_consents")
                .select("*")
                .eq("user_id", current_user.id)
                .eq("status", "active")
                .order("consented_at", desc=True)
                .limit(1)
                .execute()
            )
            if res.data:
                latest = res.data[0]
                return ConsentStatusResponse(
                    has_consented=True,
                    consent_version=latest.get("consent_version", settings.CURRENT_CONSENT_VERSION),
                    consented_at=latest.get("consented_at"),
                    language=latest.get("language", "en"),
                )
            return ConsentStatusResponse(
                has_consented=False,
                consent_version=settings.CURRENT_CONSENT_VERSION,
            )
        except Exception:
            pass

    consent = next(
        (c for c in _local_db["user_consents"]
         if c["user_id"] == current_user.id and c["status"] == "active"),
        None
    )
    if not consent:
        return ConsentStatusResponse(
            has_consented=False,
            consent_version=settings.CURRENT_CONSENT_VERSION,
        )
    return ConsentStatusResponse(
        has_consented=True,
        consent_version=consent["consent_version"],
        consented_at=consent["consented_at"],
        language=consent.get("language", "en"),
    )


@router.post("", response_model=RecordConsentResponse)
async def record_user_consent(
    payload: RecordConsentRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Records statutory consent in public.user_consents.
    Requires acceptance of all itemized disclosures.
    """
    if len(payload.accepted_disclosures) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All 4 statutory disclosures must be accepted to proceed",
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    now_str = datetime.now(timezone.utc).isoformat()
    record_id = str(uuid.uuid4())

    record = {
        "id": record_id,
        "user_id": current_user.id,
        "org_id": current_user.org_id,
        "consent_version": payload.consent_version,
        "language": payload.language,
        "ip_address": client_ip,
        "status": "active",
        "consented_at": now_str,
    }
    
    # Store in live Supabase table
    client = supabase_admin.get_authenticated_client(current_user.token)
    if client:
        try:
            client.table("user_consents").insert(record).execute()
        except Exception as e:
            logger.warning("Live Supabase insert user_consents error: %s", e)

    # Store in local mirror
    _local_db["user_consents"].append(record)

    return RecordConsentResponse(
        id=record_id,
        user_id=current_user.id,
        org_id=current_user.org_id,
        consent_version=payload.consent_version,
        language=payload.language,
        consented_at=now_str,
        status="active",
    )


@router.get("/notice")
async def get_statutory_notice():
    """Returns bilingual statutory disclosure text (English and Hindi)."""
    return {
        "version": settings.CURRENT_CONSENT_VERSION,
        "languages": {
            "en": {
                "title": "DPDP Act 2023 Statutory Consent & AI Disclosure",
                "items": DPDP_DISCLOSURES_EN,
            },
            "hi": {
                "title": "डिजिटल व्यक्तिगत डेटा संरक्षण (DPDP) अधिनियम 2023 वैधानिक सहमति",
                "items": DPDP_DISCLOSURES_HI,
            }
        }
    }
