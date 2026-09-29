"""Account and Data Erasure Router (Apple App Store Guideline 5.1.1 & DPDP Act 2023 Compliance)."""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.auth.dependencies import CurrentUser, get_current_user
from src.compliance.dsr_service import dsr_service

router = APIRouter(prefix="/api/v1/account", tags=["account"])


class DeleteAccountResponse(BaseModel):
    success: bool
    user_id: str
    purged_vault_secrets: int
    status: str
    message: str


@router.delete("/delete", response_model=DeleteAccountResponse)
async def delete_account_in_app(current_user: CurrentUser = Depends(get_current_user)):
    """
    Mandatory In-App Account & Data Deletion (Apple Guideline 5.1.1 & DPDP Section 13).
    Cascades complete atomic erasure across Supabase Auth, profiles, consent records,
    conversations, episodic ADK sessions, connected MCP integrations, and hardware-encrypted Vault secrets.
    """
    try:
        result = dsr_service.execute_dsr_erasure(current_user.id, current_user.org_id)
        return DeleteAccountResponse(
            success=True,
            user_id=current_user.id,
            purged_vault_secrets=result.get("purged_vault_secrets", 0),
            status="account_and_memory_purged",
            message="Your account, connected tools, and memory have been completely purged.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute complete account deletion: {str(e)}",
        )


@router.get("/export")
async def export_account_data(current_user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Right to Data Portability (India DPDP Act 2023 Section 12).
    Generates a structured JSON archive of all past conversations, consents, and connected providers.
    """
    try:
        return dsr_service.export_user_data(current_user.id, current_user.org_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export account data: {str(e)}",
        )
