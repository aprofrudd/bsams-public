"""Exercise library API router (coach-level exercise database)."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)

from app.core.access_control import get_athlete_coach_id, require_coach_or_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.exercise_library import (
    ExerciseLibraryCreate,
    ExerciseLibraryResponse,
    ExerciseLibraryUpdate,
)

router = APIRouter(prefix="/exercise-library", tags=["exercise-library"])


@router.post(
    "/",
    response_model=ExerciseLibraryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exercise(
    exercise: ExerciseLibraryCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new exercise in the coach's library."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    data = {
        "coach_id": str(current_user.id),
        **{k: v for k, v in exercise.model_dump(exclude_unset=False).items() if v is not None},
    }

    try:
        response = client.table("exercise_library").insert(data).execute()
    except Exception as e:
        raise_on_duplicate(e, "An exercise with this name already exists in your library")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create exercise",
        )

    return response.data[0]


@router.get(
    "/",
    response_model=List[ExerciseLibraryResponse],
)
def list_exercises(
    search: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = Query(None, max_length=50),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List exercises in the coach's library with optional search and category filter."""
    client = get_client_or_503()

    if current_user.role == "athlete":
        coach_id = get_athlete_coach_id(client, current_user)
    else:
        require_coach_or_admin(current_user)
        coach_id = str(current_user.id)

    query = (
        client.table("exercise_library")
        .select("*")
        .eq("coach_id", coach_id)
    )

    if search:
        query = query.ilike("exercise_name", f"%{search}%")

    if category:
        query = query.eq("exercise_category", category)

    response = query.order("exercise_name").execute()

    return response.data


@router.patch(
    "/{exercise_id}",
    response_model=ExerciseLibraryResponse,
)
def update_exercise(
    exercise_id: UUID,
    exercise: ExerciseLibraryUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update an exercise in the coach's library."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Verify ownership
    existing = (
        client.table("exercise_library")
        .select("*")
        .eq("id", str(exercise_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    update_data = exercise.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        response = (
            client.table("exercise_library")
            .update(update_data)
            .eq("id", str(exercise_id))
            .execute()
        )
    except Exception as e:
        raise_on_duplicate(e, "An exercise with this name already exists in your library")

    return response.data[0]


@router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_exercise(
    exercise_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an exercise from the coach's library."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Verify ownership
    existing = (
        client.table("exercise_library")
        .select("*")
        .eq("id", str(exercise_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    client.table("exercise_library").delete().eq("id", str(exercise_id)).execute()

    return None
