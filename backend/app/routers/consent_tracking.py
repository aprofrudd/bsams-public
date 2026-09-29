"""User consent tracking for GDPR compliance."""

import logging
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-consents", tags=["user-consents"])


class ConsentResponse(BaseModel):
    """Response for a single consent record."""
    id: str
    user_id: str
    consent_type: str
    granted: bool
    granted_at: Optional[str] = None
    revoked_at: Optional[str] = None
    version: str
    created_at: str


class ConsentUpdate(BaseModel):
    """Request to grant or revoke consent."""
    granted: bool


@router.get("/", response_model=List[ConsentResponse])
def get_consents(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get all consent records for the current user."""
    client = get_client_or_503()

    result = (
        client.table("user_consents")
        .select("*")
        .eq("user_id", str(current_user.id))
        .execute()
    )

    return [ConsentResponse(**r) for r in (result.data or [])]


@router.put("/{consent_type}", response_model=ConsentResponse)
def update_consent(
    consent_type: str,
    body: ConsentUpdate,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Grant or revoke a specific consent type."""
    valid_types = ("data_processing", "data_sharing", "marketing")
    if consent_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent type. Must be one of: {', '.join(valid_types)}",
        )

    client = get_client_or_503()

    now = datetime.now(timezone.utc).isoformat()
    ip_address = request.client.host if request.client else None

    # Check if consent record exists
    existing = (
        client.table("user_consents")
        .select("id")
        .eq("user_id", str(current_user.id))
        .eq("consent_type", consent_type)
        .execute()
    )

    if existing.data:
        # Update existing
        update_data = {"granted": body.granted}
        if body.granted:
            update_data["granted_at"] = now
            update_data["revoked_at"] = None
        else:
            update_data["revoked_at"] = now

        if ip_address:
            update_data["ip_address"] = ip_address

        result = (
            client.table("user_consents")
            .update(update_data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        # Create new
        insert_data = {
            "user_id": str(current_user.id),
            "consent_type": consent_type,
            "granted": body.granted,
            "ip_address": ip_address,
        }
        if body.granted:
            insert_data["granted_at"] = now

        result = (
            client.table("user_consents")
            .insert(insert_data)
            .execute()
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update consent",
        )

    return ConsentResponse(**result.data[0])
