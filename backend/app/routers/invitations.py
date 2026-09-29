"""Invitation API router for coach-athlete linking."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, get_supabase_client
from app.schemas.invitation import (
    InvitationCreate,
    InvitationResponse,
    InvitationValidateResponse,
)

router = APIRouter(prefix="/invitations", tags=["invitations"])
limiter = Limiter(key_func=get_remote_address)

INVITE_EXPIRY_DAYS = 7
MAX_CODE_RETRIES = 3


def _generate_invite_code() -> str:
    """Generate a short, unique invitation code."""
    return secrets.token_urlsafe(6)[:8].upper()


@router.post("/", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    body: InvitationCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create an invitation for an athlete to sign up."""
    if current_user.role == "athlete":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Athletes cannot create invitations",
        )

    client = get_client_or_503()

    # Verify athlete exists and belongs to coach
    athlete_response = (
        client.table("athletes")
        .select("id, user_id, coach_id")
        .eq("id", str(body.athlete_id))
        .execute()
    )

    if not athlete_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    athlete = athlete_response.data[0]
    if str(athlete["coach_id"]) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    if athlete.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Athlete already has a linked account",
        )

    # Check for existing active invitation
    now_iso = datetime.now(timezone.utc).isoformat()
    active_invites = (
        client.table("athlete_invitations")
        .select("id")
        .eq("athlete_id", str(body.athlete_id))
        .is_("used_at", "null")
        .gt("expires_at", now_iso)
        .execute()
    )

    if active_invites.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active invitation already exists for this athlete",
        )

    # Generate unique code with retry
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)

    for attempt in range(MAX_CODE_RETRIES):
        code = _generate_invite_code()
        try:
            invite_data = {
                "athlete_id": str(body.athlete_id),
                "coach_id": str(current_user.id),
                "invite_code": code,
                "expires_at": expires_at.isoformat(),
            }
            result = client.table("athlete_invitations").insert(invite_data).execute()
            if result.data:
                return InvitationResponse(**result.data[0])
        except Exception as e:
            if "unique" in str(e).lower() and attempt < MAX_CODE_RETRIES - 1:
                continue
            raise

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate unique invitation code",
    )


@router.get("/", response_model=List[InvitationResponse])
def list_invitations(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all invitations created by the current coach."""
    if current_user.role == "athlete":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Athletes cannot list invitations",
        )

    client = get_client_or_503()

    result = (
        client.table("athlete_invitations")
        .select("*")
        .eq("coach_id", str(current_user.id))
        .order("created_at", desc=True)
        .execute()
    )

    return [InvitationResponse(**r) for r in (result.data or [])]


@router.get("/validate/{code}", response_model=InvitationValidateResponse)
@limiter.limit("3/minute")
async def validate_invitation(request: Request, code: str):
    """Validate an invitation code. Public endpoint (no auth required)."""
    client = get_supabase_client()
    if not client:
        return InvitationValidateResponse(valid=False)

    # Look up invitation by code
    result = (
        client.table("athlete_invitations")
        .select("*")
        .eq("invite_code", code)
        .execute()
    )

    if not result.data:
        return InvitationValidateResponse(valid=False)

    invite = result.data[0]

    # Check if used
    if invite.get("used_at") is not None:
        return InvitationValidateResponse(valid=False)

    # Check if expired
    expires_at = datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        return InvitationValidateResponse(valid=False)

    # Look up athlete first name only (no coach email to avoid information leak)
    athlete_first_name = None
    athlete_result = (
        client.table("athletes")
        .select("name")
        .eq("id", invite["athlete_id"])
        .execute()
    )
    if athlete_result.data:
        full_name = athlete_result.data[0].get("name", "")
        athlete_first_name = full_name.split()[0] if full_name else None

    return InvitationValidateResponse(
        valid=True,
        athlete_first_name=athlete_first_name,
        expires_at=expires_at,
    )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Revoke (delete) an unused invitation."""
    if current_user.role == "athlete":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Athletes cannot manage invitations",
        )

    client = get_client_or_503()

    # Look up invitation
    result = (
        client.table("athlete_invitations")
        .select("*")
        .eq("id", str(invitation_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    invite = result.data[0]

    if str(invite["coach_id"]) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invite.get("used_at") is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke a used invitation",
        )

    client.table("athlete_invitations").delete().eq("id", str(invitation_id)).execute()
    return None
