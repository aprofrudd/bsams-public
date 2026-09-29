"""Wellness entries API router."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.access_control import verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.wellness import (
    WellnessEntryCreate,
    WellnessEntryResponse,
    WellnessEntryUpdate,
)

router = APIRouter(prefix="/wellness", tags=["wellness"])


@router.post(
    "/",
    response_model=WellnessEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_wellness_entry(
    entry: WellnessEntryCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new wellness entry for an athlete. One entry per athlete per day."""
    client = get_client_or_503()

    if not verify_athlete_access(client, entry.athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    data = {
        "athlete_id": str(entry.athlete_id),
        "entry_date": entry.entry_date.isoformat(),
        "sleep": entry.sleep,
        "fatigue": entry.fatigue,
        "stress": entry.stress,
        "doms": entry.doms,
        "notes": entry.notes,
    }

    try:
        response = client.table("wellness_entries").insert(data).execute()
    except Exception as e:
        raise_on_duplicate(e, "Wellness entry already exists for this date")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create wellness entry",
        )

    return response.data[0]


@router.get(
    "/athlete/{athlete_id}",
    response_model=List[WellnessEntryResponse],
)
def list_wellness_entries(
    athlete_id: UUID,
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List wellness entries for an athlete with optional pagination and date filtering."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    query = (
        client.table("wellness_entries")
        .select("*")
        .eq("athlete_id", str(athlete_id))
    )

    if start_date:
        query = query.gte("entry_date", start_date.isoformat())
    if end_date:
        query = query.lte("entry_date", end_date.isoformat())

    response = query.order("entry_date", desc=True).range(skip, skip + limit - 1).execute()

    return response.data


@router.get(
    "/{entry_id}",
    response_model=WellnessEntryResponse,
)
def get_wellness_entry(
    entry_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single wellness entry by ID."""
    client = get_client_or_503()

    response = (
        client.table("wellness_entries")
        .select("*")
        .eq("id", str(entry_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness entry not found",
        )

    entry = response.data[0]

    if not verify_athlete_access(client, UUID(entry["athlete_id"]), current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness entry not found",
        )

    return entry


@router.patch(
    "/{entry_id}",
    response_model=WellnessEntryResponse,
)
def update_wellness_entry(
    entry_id: UUID,
    entry: WellnessEntryUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update an existing wellness entry."""
    client = get_client_or_503()

    existing = (
        client.table("wellness_entries")
        .select("*")
        .eq("id", str(entry_id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness entry not found",
        )

    if not verify_athlete_access(
        client, UUID(existing.data[0]["athlete_id"]), current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness entry not found",
        )

    update_data = entry.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    if "entry_date" in update_data and update_data["entry_date"]:
        update_data["entry_date"] = update_data["entry_date"].isoformat()

    response = (
        client.table("wellness_entries")
        .update(update_data)
        .eq("id", str(entry_id))
        .execute()
    )

    return response.data[0]


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_wellness_entry(
    entry_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a wellness entry."""
    client = get_client_or_503()

    existing = (
        client.table("wellness_entries")
        .select("*")
        .eq("id", str(entry_id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness entry not found",
        )

    if not verify_athlete_access(
        client, UUID(existing.data[0]["athlete_id"]), current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wellness entry not found",
        )

    client.table("wellness_entries").delete().eq("id", str(entry_id)).execute()

    return None
