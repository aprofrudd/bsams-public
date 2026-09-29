"""Athletes API router."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import create_client

from app.core.access_control import require_coach_or_admin
from app.core.config import get_settings
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.athlete import AthleteCreate, AthleteResponse, AthleteUpdate
from app.services.audit import log_deletion, log_event

logger = logging.getLogger(__name__)


class MergeRequest(BaseModel):
    keep_id: UUID
    merge_id: UUID


class DeleteAllRequest(BaseModel):
    current_password: str

router = APIRouter(prefix="/athletes", tags=["athletes"])
limiter = Limiter(key_func=get_remote_address)


# Both combine foreign keys cascade from `athletes`: deleting an athlete takes their
# `combine_participants` row and, through it, every `combine_attempts` row logged
# against them at every station. Attempts are the log of record for a testing day
# (decision 112) — a re-sync rebuilds promoted rows from them, so once they are gone
# nothing brings the day's results back. Every path that deletes an athlete asks the
# roster first.
ROSTER_LOOKUP_CHUNK = 500


def _combine_roster_rows(client, athlete_ids: List[str]) -> List[dict]:
    """Roster rows belonging to any of these athletes.

    Chunked because a coach can hold hundreds of athletes and `.in_()` travels in
    the query string — the same 500-row chunking the block writer uses.
    """
    rows: List[dict] = []
    for start in range(0, len(athlete_ids), ROSTER_LOOKUP_CHUNK):
        chunk = athlete_ids[start : start + ROSTER_LOOKUP_CHUNK]
        result = (
            client.table("combine_participants")
            .select("id, athlete_id, combine_event_id")
            .in_("athlete_id", chunk)
            .execute()
        )
        rows.extend(result.data or [])
    return rows


def _name_combine_events(client, event_ids: List[str]) -> str:
    """Name the events blocking a deletion, so the 409 points somewhere real."""
    names: List[str] = []
    if event_ids:
        result = (
            client.table("combine_events")
            .select("id, event_name")
            .in_("id", event_ids)
            .execute()
        )
        names = [
            row.get("event_name") or "an unnamed combine" for row in (result.data or [])
        ]
    if not names:
        return "a combine event"
    if len(names) == 1:
        return f"'{names[0]}'"
    if len(names) == 2:
        return f"'{names[0]}' and '{names[1]}'"
    return f"'{names[0]}' and {len(names) - 1} other combine events"


def _blocking_event_names(client, roster_rows: List[dict]) -> str:
    return _name_combine_events(
        client, sorted({str(row["combine_event_id"]) for row in roster_rows})
    )


@router.get("/", response_model=List[AthleteResponse])
@limiter.limit("60/minute")
def list_athletes(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    List all athletes for the current coach.

    Returns a paginated list of athletes belonging to the authenticated coach.
    """
    client = get_client_or_503()

    if current_user.role == "athlete":
        response = (
            client.table("athletes")
            .select("*")
            .eq("user_id", str(current_user.id))
            .range(skip, skip + limit - 1)
            .execute()
        )
    else:
        response = (
            client.table("athletes")
            .select("*")
            .eq("coach_id", str(current_user.id))
            .range(skip, skip + limit - 1)
            .execute()
        )

    return response.data


@router.get("/{athlete_id}", response_model=AthleteResponse)
@limiter.limit("60/minute")
def get_athlete(
    request: Request,
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get a single athlete by ID.

    Returns the athlete if found and belongs to the current coach or athlete user.
    """
    client = get_client_or_503()

    if current_user.role == "athlete":
        response = (
            client.table("athletes")
            .select("*")
            .eq("id", str(athlete_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
    else:
        response = (
            client.table("athletes")
            .select("*")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    return response.data[0]


@router.post("/", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
def create_athlete(
    athlete: AthleteCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Create a new athlete.

    Creates an athlete record for the current coach.
    """
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    data = athlete.model_dump()
    data["coach_id"] = str(current_user.id)
    data["gender"] = data["gender"].value  # Convert enum to string

    # Convert date to ISO format string if present
    if data.get("date_of_birth"):
        data["date_of_birth"] = data["date_of_birth"].isoformat()

    response = client.table("athletes").insert(data).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create athlete",
        )

    return response.data[0]


@router.patch("/{athlete_id}", response_model=AthleteResponse)
def update_athlete(
    athlete_id: UUID,
    athlete: AthleteUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Update an existing athlete.

    Updates the athlete if found and belongs to the current coach.
    """
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # First check if athlete exists and belongs to coach
    existing = (
        client.table("athletes")
        .select("id")
        .eq("id", str(athlete_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    # Build update data, excluding unset fields
    update_data = athlete.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Convert enum to string if present
    if "gender" in update_data and update_data["gender"]:
        update_data["gender"] = update_data["gender"].value

    # Convert date to ISO format string if present
    if "date_of_birth" in update_data and update_data["date_of_birth"]:
        update_data["date_of_birth"] = update_data["date_of_birth"].isoformat()

    # Filter None values — the frontend sends all fields including unchanged nulls,
    # which can cause PostgREST errors with CHECK-constrained nullable columns.
    # Clearing a field to null requires the frontend to send only changed fields.
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    response = (
        client.table("athletes")
        .update(update_data)
        .eq("id", str(athlete_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Update returned no data",
        )

    return response.data[0]


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_athlete(
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Delete an athlete.

    Deletes the athlete if found and belongs to the current coach.
    """
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Check if athlete exists and belongs to coach
    existing = (
        client.table("athletes")
        .select("id, name, first_name, surname")
        .eq("id", str(athlete_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    # The cascade runs before anything is logged, so refuse first. "Remove them from
    # the roster" would be a dead end here — `delete_participant` itself refuses once
    # attempts exist — so the message points at withdrawal or at the event.
    roster_rows = _combine_roster_rows(client, [str(athlete_id)])
    if roster_rows:
        blocking = _blocking_event_names(client, roster_rows)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This athlete is on the roster for {blocking} — deleting them would "
                "take every attempt logged against them with it. Mark them withdrawn "
                "on the roster instead, or delete the combine event once it is done "
                "(promoted results survive that; the attempt log does not)."
            ),
        )

    # Count related records for audit summary
    events_count = len(
        client.table("performance_events")
        .select("id")
        .eq("athlete_id", str(athlete_id))
        .execute()
        .data or []
    )

    athlete_data = existing.data[0]
    athlete_name = athlete_data.get("name") or f"{athlete_data.get('first_name', '')} {athlete_data.get('surname', '')}".strip()

    # Log deletion for GDPR audit trail
    log_deletion(
        deleted_by=current_user.id,
        entity_type="athlete",
        entity_id=athlete_id,
        entity_summary={
            "name": athlete_name,
            "coach_id": str(current_user.id),
            "events_count": events_count,
            # Zero by construction — the guard above refuses otherwise — but the audit
            # row is the only trail there would be, so it states what was checked.
            "combine_participants_count": len(roster_rows),
        },
    )

    client.table("athletes").delete().eq("id", str(athlete_id)).eq(
        "coach_id", str(current_user.id)
    ).execute()

    return None


@router.post("/merge", status_code=status.HTTP_200_OK)
def merge_athletes(
    body: MergeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Merge two athletes by reassigning events from merge_id to keep_id,
    then deleting the merge_id athlete.
    """
    require_coach_or_admin(current_user)

    if body.keep_id == body.merge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="keep_id and merge_id must be different",
        )

    client = get_client_or_503()

    # Verify both athletes exist and belong to the current coach
    for athlete_id, label in [
        (body.keep_id, "keep_id"),
        (body.merge_id, "merge_id"),
    ]:
        result = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Athlete not found for {label}",
            )

    # A combine roster references the athlete by id, and deleting the merged-away
    # athlete cascades their participant row and every attempt logged against it —
    # a whole testing day's results. Refuse before anything is written.
    if _combine_roster_rows(client, [str(body.merge_id)]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "One of these athletes is on a combine roster — "
                "remove them from the roster first"
            ),
        )

    # Count events to reassign
    events = (
        client.table("performance_events")
        .select("id")
        .eq("athlete_id", str(body.merge_id))
        .execute()
    )
    merged_events = len(events.data)

    # Reassign events from merge_id to keep_id
    if merged_events > 0:
        (
            client.table("performance_events")
            .update({"athlete_id": str(body.keep_id)})
            .eq("athlete_id", str(body.merge_id))
            .execute()
        )

    # Delete the duplicate athlete
    (
        client.table("athletes")
        .delete()
        .eq("id", str(body.merge_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    return {
        "kept_athlete_id": str(body.keep_id),
        "merged_events": merged_events,
        "deleted_athlete_id": str(body.merge_id),
    }


@router.delete("/", status_code=status.HTTP_200_OK)
@limiter.limit("1/minute")
def delete_all_data(
    request: Request,
    body: DeleteAllRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Delete all athletes and their events for the current coach.

    Requires password re-entry for safety. Rate limited to 1/minute.
    Events are cascade-deleted via foreign key when athletes are removed.
    """
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Verify password before proceeding
    profile = (
        client.table("profiles")
        .select("email")
        .eq("id", str(current_user.id))
        .execute()
    )
    if not profile.data or not profile.data[0].get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find user profile",
        )
    email = profile.data[0]["email"]

    try:
        settings = get_settings()
        verify_client = create_client(settings.supabase_url, settings.supabase_key)
        verify_client.auth.sign_in_with_password(
            {"email": email, "password": body.current_password}
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Get all athlete IDs for this coach
    athletes = (
        client.table("athletes")
        .select("id")
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not athletes.data:
        return {"deleted_athletes": 0, "deleted_events": 0}

    athlete_ids = [str(a["id"]) for a in athletes.data]

    # The same cascade as the single delete, in bulk. Refused rather than silently
    # taking the day's attempt log with it — and the message names the order that
    # unblocks it, because the coach cannot clear the roster first (removing a boxer
    # with attempts is refused too).
    roster_rows = _combine_roster_rows(client, athlete_ids)
    if roster_rows:
        blocking = _blocking_event_names(client, roster_rows)
        subject = (
            "that combine event"
            if len({str(row["combine_event_id"]) for row in roster_rows}) == 1
            else "those combine events"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{len(roster_rows)} of these athletes are on the roster for "
                f"{blocking} — delete {subject} first (the attempt log goes with it), "
                "then retry this deletion."
            ),
        )

    # Audit log before deletion
    try:
        log_event(
            current_user.id,
            "delete_all_data",
            details={
                "athlete_count": len(athlete_ids),
                # Zero by construction, as above: the guard refuses otherwise.
                "combine_participants_count": len(roster_rows),
            },
            request=request,
        )
    except Exception:
        pass

    # Delete all events for these athletes first
    events_deleted = 0
    for aid in athlete_ids:
        events = (
            client.table("performance_events")
            .select("id")
            .eq("athlete_id", aid)
            .execute()
        )
        events_deleted += len(events.data)
        if events.data:
            client.table("performance_events").delete().eq("athlete_id", aid).execute()

    # Delete all athletes for this coach
    client.table("athletes").delete().eq("coach_id", str(current_user.id)).execute()

    return {
        "deleted_athletes": len(athlete_ids),
        "deleted_events": events_deleted,
    }
