"""Consent API router for data sharing management."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.consent import CONSENT_INFO_TEXT, ConsentResponse, ConsentUpdate

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/", response_model=ConsentResponse)
def get_consent(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get the current data sharing consent status for the authenticated coach."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    result = (
        client.table("coach_consents")
        .select("*")
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not result.data:
        return ConsentResponse(
            data_sharing_enabled=False,
            info_text=CONSENT_INFO_TEXT,
        )

    consent = result.data[0]
    return ConsentResponse(
        data_sharing_enabled=consent["data_sharing_enabled"],
        consented_at=consent.get("consented_at"),
        revoked_at=consent.get("revoked_at"),
        info_text=CONSENT_INFO_TEXT,
    )


@router.put("/", response_model=ConsentResponse)
def update_consent(
    body: ConsentUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update data sharing consent for the authenticated coach."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    now = datetime.now(timezone.utc).isoformat()

    # Check if consent record exists
    existing = (
        client.table("coach_consents")
        .select("id")
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if existing.data:
        # Update existing record
        update_data = {
            "data_sharing_enabled": body.data_sharing_enabled,
            "updated_at": now,
        }
        if body.data_sharing_enabled:
            update_data["consented_at"] = now
            update_data["revoked_at"] = None
        else:
            update_data["revoked_at"] = now

        result = (
            client.table("coach_consents")
            .update(update_data)
            .eq("coach_id", str(current_user.id))
            .execute()
        )
    else:
        # Create new record
        insert_data = {
            "coach_id": str(current_user.id),
            "data_sharing_enabled": body.data_sharing_enabled,
            "created_at": now,
            "updated_at": now,
        }
        if body.data_sharing_enabled:
            insert_data["consented_at"] = now

        result = (
            client.table("coach_consents")
            .insert(insert_data)
            .execute()
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update consent",
        )

    consent = result.data[0]
    return ConsentResponse(
        data_sharing_enabled=consent["data_sharing_enabled"],
        consented_at=consent.get("consented_at"),
        revoked_at=consent.get("revoked_at"),
        info_text=CONSENT_INFO_TEXT,
    )
