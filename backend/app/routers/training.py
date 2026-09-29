"""Training sessions API router."""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.training_session import (
    BatchSessionAssign,
    BatchSessionResponse,
    TrainingSessionCreate,
    TrainingSessionResponse,
    TrainingSessionUpdate,
)
from app.services.training_load import TrainingLoadEngine

router = APIRouter(prefix="/training", tags=["training"])


@router.post(
    "/sessions/",
    response_model=TrainingSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_training_session(
    session: TrainingSessionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new training session for an athlete."""
    client = get_client_or_503()

    if not verify_athlete_access(client, session.athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    # Role-based validation
    if session.status == "assigned":
        # Only coaches/admins can create assigned sessions
        require_coach_or_admin(current_user)
        # rpe and duration_minutes are optional for assigned sessions
    elif current_user.role == "athlete":
        # Athletes can self-log with optional RPE/duration
        if session.status is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Athletes cannot set session status",
            )
    # else: Coach/admin regular logging — RPE and duration are optional
    # (can be added later via edit)

    data = {
        "athlete_id": str(session.athlete_id),
        "session_date": session.session_date.isoformat(),
        "training_type": session.training_type,
        "duration_minutes": session.duration_minutes,
        "rpe": session.rpe,
        "description": session.description,
        "notes": session.notes,
        "metrics": session.metrics,
        "created_by": str(current_user.id),
    }

    if session.status:
        data["status"] = session.status

    response = client.table("training_sessions").insert(data).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create training session",
        )

    return response.data[0]


@router.post(
    "/sessions/batch",
    response_model=BatchSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def batch_assign_sessions(
    payload: BatchSessionAssign,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Batch-assign a template to multiple athletes. Coach/admin only."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # 1. Verify template ownership
    template_resp = (
        client.table("session_templates")
        .select("*")
        .eq("id", str(payload.template_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )
    if not template_resp.data:
        raise HTTPException(404, detail="Template not found")
    template = template_resp.data[0]

    # 2. Bulk-verify all athletes belong to coach
    athlete_id_strs = [str(aid) for aid in payload.athlete_ids]
    athletes_resp = (
        client.table("athletes")
        .select("id")
        .eq("coach_id", str(current_user.id))
        .in_("id", athlete_id_strs)
        .execute()
    )
    found_ids = {row["id"] for row in athletes_resp.data}
    missing = [aid for aid in athlete_id_strs if aid not in found_ids]
    if missing:
        raise HTTPException(400, detail=f"Athletes not found or not owned: {missing}")

    # 3. Load template exercises
    exercises_resp = (
        client.table("template_exercises")
        .select("*")
        .eq("template_id", str(payload.template_id))
        .order("order_index")
        .execute()
    )
    template_exercises = exercises_resp.data

    # 4. Bulk-insert sessions
    session_rows = [
        {
            "athlete_id": aid,
            "session_date": payload.session_date.isoformat(),
            "training_type": template["training_type"],
            "notes": payload.notes,
            "status": "assigned",
            "created_by": str(current_user.id),
        }
        for aid in athlete_id_strs
    ]
    sessions_resp = client.table("training_sessions").insert(session_rows).execute()
    if not sessions_resp.data:
        raise HTTPException(500, detail="Failed to create training sessions")
    created_sessions = sessions_resp.data

    # 5. Bulk-insert exercise prescriptions (set expansion)
    if template_exercises:
        prescriptions = []
        for session in created_sessions:
            for ex in template_exercises:
                for set_num in range(1, (ex.get("sets", 1) or 1) + 1):
                    p = {
                        "session_id": session["id"],
                        "exercise_name": ex["exercise_name"],
                        "exercise_category": ex.get("exercise_category"),
                        "set_number": set_num,
                        "reps": ex.get("reps"),
                        "weight_kg": ex.get("weight_kg"),
                        "tempo": ex.get("tempo"),
                        "rest_seconds": ex.get("rest_seconds"),
                        "duration_seconds": ex.get("duration_seconds"),
                        "distance_meters": ex.get("distance_meters"),
                        "intensity_type": ex.get("intensity_type"),
                        "intensity_value": ex.get("intensity_value"),
                        "rest_between_reps_seconds": ex.get("rest_between_reps_seconds"),
                        "rep_durations": ex.get("rep_durations"),
                        "rest_between_reps": ex.get("rest_between_reps"),
                        "rep_intensity_values": ex.get("rep_intensity_values"),
                        "notes": ex.get("notes"),
                    }
                    prescriptions.append({k: v for k, v in p.items() if v is not None})
        if prescriptions:
            client.table("exercise_prescriptions").insert(prescriptions).execute()

    return BatchSessionResponse(
        created_count=len(created_sessions),
        sessions=created_sessions,
    )


@router.get(
    "/sessions/athlete/{athlete_id}",
    response_model=List[TrainingSessionResponse],
)
def list_training_sessions(
    athlete_id: UUID,
    start_date: Optional[date] = Query(None, description="Filter from this date"),
    end_date: Optional[date] = Query(None, description="Filter until this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List training sessions for an athlete with optional pagination and date filtering."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    query = (
        client.table("training_sessions")
        .select("*")
        .eq("athlete_id", str(athlete_id))
    )

    if start_date:
        query = query.gte("session_date", start_date.isoformat())
    if end_date:
        query = query.lte("session_date", end_date.isoformat())

    response = query.order("session_date", desc=True).range(skip, skip + limit - 1).execute()

    return response.data


@router.get(
    "/sessions/{session_id}",
    response_model=TrainingSessionResponse,
)
def get_training_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single training session by ID."""
    client = get_client_or_503()

    response = (
        client.table("training_sessions")
        .select("*")
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


@router.patch(
    "/sessions/{session_id}",
    response_model=TrainingSessionResponse,
)
def update_training_session(
    session_id: UUID,
    session: TrainingSessionUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update an existing training session."""
    client = get_client_or_503()

    existing = (
        client.table("training_sessions")
        .select("*")
        .eq("id", str(session_id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    existing_session = existing.data[0]

    if not verify_athlete_access(
        client, UUID(existing_session["athlete_id"]), current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    update_data = session.model_dump(exclude_unset=True)

    # Athlete-specific restrictions
    if current_user.role == "athlete":
        existing_status = existing_session.get("status")
        # If this is a coach-created session (assigned or completed), strip session_date and training_type
        if existing_status in ("assigned", "completed"):
            update_data.pop("session_date", None)
            update_data.pop("training_type", None)
        # If athlete provides rpe on an assigned session, auto-complete it
        if existing_status == "assigned" and "rpe" in update_data:
            update_data["status"] = "completed"

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    if "session_date" in update_data and update_data["session_date"]:
        update_data["session_date"] = update_data["session_date"].isoformat()

    response = (
        client.table("training_sessions")
        .update(update_data)
        .eq("id", str(session_id))
        .execute()
    )

    return response.data[0]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_training_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a training session."""
    client = get_client_or_503()

    existing = (
        client.table("training_sessions")
        .select("*")
        .eq("id", str(session_id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    existing_session = existing.data[0]

    if not verify_athlete_access(
        client, UUID(existing_session["athlete_id"]), current_user
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found",
        )

    # Athletes can only delete their own self-logged sessions (status IS NULL, created_by matches)
    if current_user.role == "athlete":
        if existing_session.get("status") is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete coach-assigned sessions",
            )
        if existing_session.get("created_by") != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete sessions created by others",
            )

    client.table("training_sessions").delete().eq("id", str(session_id)).execute()

    return None


@router.get(
    "/analysis/load/{athlete_id}",
    response_model=Dict[str, Any],
)
def get_training_load(
    athlete_id: UUID,
    days: int = Query(28, ge=7, le=90, description="Number of days to analyze"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get training load analysis for an athlete."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    target_date = date.today()
    start_date = target_date - timedelta(days=days - 1)

    response = (
        client.table("training_sessions")
        .select("*")
        .eq("athlete_id", str(athlete_id))
        .gte("session_date", start_date.isoformat())
        .lte("session_date", target_date.isoformat())
        .execute()
    )

    analysis = TrainingLoadEngine.analyze(
        sessions=response.data,
        days=days,
        target_date=target_date,
    )

    return {
        "daily_loads": [
            {
                "date": dl.date.isoformat(),
                "total_srpe": dl.total_srpe,
                "session_count": dl.session_count,
            }
            for dl in analysis.daily_loads
        ],
        "weekly_load": analysis.weekly_load,
        "monotony": analysis.monotony,
        "strain": analysis.strain,
        "acwr": analysis.acwr,
        "acute_load": analysis.acute_load,
        "chronic_load": analysis.chronic_load,
    }
