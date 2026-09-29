"""Admin API router for viewing shared anonymised athlete data."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503

router = APIRouter(prefix="/admin", tags=["admin"])
limiter = Limiter(key_func=get_remote_address)


class AnonymisedAthlete(BaseModel):
    """Anonymised athlete for admin view."""

    id: str
    anonymous_name: str
    gender: str
    coach_id: str


class SharedEvent(BaseModel):
    """Performance event for shared athlete view."""

    id: str
    athlete_id: str
    event_date: str
    metrics: dict


def _require_admin(current_user: AuthenticatedUser) -> None:
    """Raise 403 if user is not admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("/shared-athletes", response_model=List[AnonymisedAthlete])
@limiter.limit("30/minute")
def list_shared_athletes(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    List anonymised athletes from coaches who opted in to data sharing.

    Admin-only endpoint. Athlete names are replaced with sequential
    anonymous IDs (e.g., "Athlete 001").
    """
    _require_admin(current_user)

    client = get_client_or_503()

    # Find coaches who opted in to data sharing
    consents = (
        client.table("coach_consents")
        .select("coach_id, data_sharing_enabled")
        .execute()
    )

    opted_in = [c for c in (consents.data or []) if c.get("data_sharing_enabled") is True]
    if not opted_in:
        return []

    # Exclude admin users — only show external coaches' data
    admin_profiles = (
        client.table("profiles")
        .select("id")
        .eq("role", "admin")
        .execute()
    )
    admin_ids = {p["id"] for p in (admin_profiles.data or [])}
    opted_in_coach_ids = [c["coach_id"] for c in opted_in if c["coach_id"] not in admin_ids]

    if not opted_in_coach_ids:
        return []

    # Get athletes from opted-in coaches in a single query
    athletes_result = (
        client.table("athletes")
        .select("id, gender, coach_id")
        .in_("coach_id", opted_in_coach_ids)
        .execute()
    )
    all_athletes = athletes_result.data or []

    # Apply pagination
    paginated = all_athletes[skip : skip + limit]

    # Anonymise names
    result = []
    for i, athlete in enumerate(paginated):
        result.append(
            AnonymisedAthlete(
                id=athlete["id"],
                anonymous_name=f"Athlete {skip + i + 1:03d}",
                gender=athlete["gender"],
                coach_id=athlete["coach_id"],
            )
        )

    return result


@router.get("/shared-athletes/{athlete_id}/events", response_model=List[SharedEvent])
@limiter.limit("30/minute")
def get_shared_athlete_events(
    request: Request,
    athlete_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get performance events for a shared athlete.

    Admin-only endpoint. Only returns events if the athlete belongs
    to an opted-in coach.
    """
    _require_admin(current_user)

    client = get_client_or_503()

    # Verify the athlete belongs to an opted-in coach
    athlete = (
        client.table("athletes")
        .select("coach_id")
        .eq("id", str(athlete_id))
        .execute()
    )

    if not athlete.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    coach_id = athlete.data[0]["coach_id"]

    # Check consent (filter in Python — .eq() on booleans unreliable with supabase-py)
    consent = (
        client.table("coach_consents")
        .select("data_sharing_enabled")
        .eq("coach_id", coach_id)
        .execute()
    )

    opted_in = any(
        c.get("data_sharing_enabled") is True for c in (consent.data or [])
    )
    if not opted_in:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coach has not opted in to data sharing",
        )

    # Get events
    events = (
        client.table("performance_events")
        .select("id, athlete_id, event_date, metrics")
        .eq("athlete_id", str(athlete_id))
        .order("event_date", desc=True)
        .range(skip, skip + limit - 1)
        .execute()
    )

    return [
        SharedEvent(
            id=e["id"],
            athlete_id=e["athlete_id"],
            event_date=e["event_date"],
            metrics=e["metrics"],
        )
        for e in events.data
    ]
