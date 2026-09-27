"""Account and Data Erasure Router (Apple App Store Guideline 5.1.1 Compliance)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.auth.dependencies import CurrentUser, get_current_user
from src.auth.client import supabase_admin

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
    Mandatory In-App Account & Data Deletion (Apple Guideline 5.1.1).
    Cascades complete atomic erasure across Supabase Auth, profiles, consent records,
    connected MCP integrations, and hardware-encrypted Supabase Vault secrets.
    """
    try:
        result = supabase_admin.delete_user_cascade(current_user.id)
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
