"""Exercise prescriptions API router (nested under training sessions)."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.exercise_prescription import (
    ExercisePrescriptionCreate,
    ExercisePrescriptionResponse,
    ExercisePrescriptionUpdate,
)

router = APIRouter(prefix="/training/sessions", tags=["exercises"])


def _verify_session_ownership(client, session_id: UUID, current_user: AuthenticatedUser) -> bool:
    """Verify that the training session belongs to an athlete accessible by the user."""
    response = (
        client.table("training_sessions")
        .select("athlete_id")
        .eq("id", str(session_id))
        .execute()
    )
    if not response.data:
        return False

    athlete_id = response.data[0]["athlete_id"]
    return verify_athlete_access(client, UUID(athlete_id), current_user)


def _get_session_details(client, session_id: UUID, current_user: AuthenticatedUser) -> dict:
    """Fetch session details and verify access. Returns session dict or raises 404."""
    response = (
        client.table("training_sessions")
        .select("athlete_id, status, created_by")
        .eq("id", str(session_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )
    session = response.data[0]
    if not verify_athlete_access(client, UUID(session["athlete_id"]), current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )
    return session


def _athlete_owns_session(session: dict, current_user: AuthenticatedUser) -> bool:
    """Return True if athlete created this session themselves (status=null, created_by=self)."""
    return (
        current_user.role == "athlete"
        and session.get("status") is None
        and session.get("created_by") == str(current_user.id)
    )


@router.post(
    "/{session_id}/exercises/",
    response_model=ExercisePrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exercise(
    session_id: UUID,
    exercise: ExercisePrescriptionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new exercise prescription for a training session."""
    client = get_client_or_503()

    session = _get_session_details(client, session_id, current_user)
    if current_user.role == "athlete" and not _athlete_owns_session(session, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Athletes can only add exercises to their own sessions",
        )

    data = {
        "session_id": str(session_id),
        **{k: v for k, v in exercise.model_dump(exclude_unset=False).items() if v is not None},
    }

    try:
        response = client.table("exercise_prescriptions").insert(data).execute()
    except Exception as e:
        logger.error("Exercise insert failed. Data: %s\nError: %s", data, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create exercise: {str(e)}",
        )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create exercise",
        )

    return response.data[0]


@router.get(
    "/{session_id}/exercises/",
    response_model=List[ExercisePrescriptionResponse],
)
def list_exercises(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all exercises for a training session."""
    client = get_client_or_503()

    if not _verify_session_ownership(client, session_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    response = (
        client.table("exercise_prescriptions")
        .select("*")
        .eq("session_id", str(session_id))
        .order("set_number")
        .execute()
    )

    return response.data


@router.patch(
    "/{session_id}/exercises/{exercise_id}",
    response_model=ExercisePrescriptionResponse,
)
def update_exercise(
    session_id: UUID,
    exercise_id: UUID,
    exercise: ExercisePrescriptionUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update an exercise prescription."""
    client = get_client_or_503()

    session = _get_session_details(client, session_id, current_user)

    # Verify exercise exists and belongs to this session
    existing = (
        client.table("exercise_prescriptions")
        .select("*")
        .eq("id", str(exercise_id))
        .eq("session_id", str(session_id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    update_data = exercise.model_dump(exclude_unset=True)

    # Athletes on coach-assigned sessions can only update reps and weight_kg
    if current_user.role == "athlete" and not _athlete_owns_session(session, current_user):
        allowed = {"reps", "weight_kg"}
        update_data = {k: v for k, v in update_data.items() if k in allowed}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Clear stale rep_durations if reps changed without updating rep_durations
    if "reps" in update_data and "rep_durations" not in update_data:
        existing_rep_durations = existing.data[0].get("rep_durations")
        if existing_rep_durations and len(existing_rep_durations) != update_data["reps"]:
            update_data["rep_durations"] = None

    # Clear stale rest_between_reps if reps changed without updating rest_between_reps
    if "reps" in update_data and "rest_between_reps" not in update_data:
        existing_rest = existing.data[0].get("rest_between_reps")
        if existing_rest and len(existing_rest) != update_data["reps"] - 1:
            update_data["rest_between_reps"] = None

    # Clear stale rep_intensity_values if reps changed without updating rep_intensity_values
    if "reps" in update_data and "rep_intensity_values" not in update_data:
        existing_riv = existing.data[0].get("rep_intensity_values")
        if existing_riv and len(existing_riv) != update_data["reps"]:
            update_data["rep_intensity_values"] = None

    response = (
        client.table("exercise_prescriptions")
        .update(update_data)
        .eq("id", str(exercise_id))
        .execute()
    )

    return response.data[0]


@router.delete(
    "/{session_id}/exercises/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_exercise(
    session_id: UUID,
    exercise_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an exercise prescription."""
    client = get_client_or_503()

    session = _get_session_details(client, session_id, current_user)
    if current_user.role == "athlete" and not _athlete_owns_session(session, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Athletes can only delete exercises from their own sessions",
        )

    existing = (
        client.table("exercise_prescriptions")
        .select("*")
        .eq("id", str(exercise_id))
        .eq("session_id", str(session_id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found",
        )

    client.table("exercise_prescriptions").delete().eq("id", str(exercise_id)).execute()

    return None
