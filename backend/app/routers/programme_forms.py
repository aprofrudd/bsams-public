"""Programme forms router.

CRUD for programme forms plus apply endpoint
for bulk session creation from form_data JSONB.
"""

import re
from datetime import timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.programme_form import (
    ProgrammeFormApply,
    ProgrammeFormApplyResponse,
    ProgrammeFormCreate,
    ProgrammeFormResponse,
    ProgrammeFormUpdate,
)
from app.services.block_engine import filter_none

router = APIRouter(prefix="/programme-forms", tags=["programme-forms"])


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _verify_form_ownership(client, form_id: UUID, current_user: AuthenticatedUser):
    """Return form row if owned by current user, else None."""
    resp = (
        client.table("programme_forms")
        .select("*")
        .eq("id", str(form_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )
    return resp.data[0] if resp.data else None


def _parse_reps_int(reps_text: str):
    """Try to parse an integer from reps_text (e.g. '4' -> 4, '4+4' -> None)."""
    if reps_text and re.fullmatch(r"\d+", reps_text.strip()):
        return int(reps_text.strip())
    return None


# ──────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────


@router.post("/", response_model=ProgrammeFormResponse, status_code=status.HTTP_201_CREATED)
def create_form(
    payload: ProgrammeFormCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new programme form."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    row = {
        "coach_id": str(current_user.id),
        "form_name": payload.form_name,
        "description": payload.description,
        "num_weeks": payload.num_weeks,
        "sessions_per_week": payload.sessions_per_week,
        "form_data": payload.form_data,
    }
    try:
        resp = client.table("programme_forms").insert(filter_none(row)).execute()
    except Exception as e:
        raise_on_duplicate(e, "A programme form with this name already exists")
        raise

    if not resp.data:
        raise HTTPException(500, detail="Failed to create programme form")
    return resp.data[0]


@router.get("/", response_model=List[ProgrammeFormResponse])
def list_forms(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List programme forms for the current coach."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    resp = (
        client.table("programme_forms")
        .select("*")
        .eq("coach_id", str(current_user.id))
        .order("form_name")
        .execute()
    )
    return resp.data


@router.get("/{form_id}", response_model=ProgrammeFormResponse)
def get_form(
    form_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single programme form."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    form = _verify_form_ownership(client, form_id, current_user)
    if not form:
        raise HTTPException(404, detail="Programme form not found")
    return form


@router.patch("/{form_id}", response_model=ProgrammeFormResponse)
def update_form(
    form_id: UUID,
    payload: ProgrammeFormUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a programme form."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    form = _verify_form_ownership(client, form_id, current_user)
    if not form:
        raise HTTPException(404, detail="Programme form not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return form

    try:
        resp = (
            client.table("programme_forms")
            .update(updates)
            .eq("id", str(form_id))
            .execute()
        )
    except Exception as e:
        raise_on_duplicate(e, "A programme form with this name already exists")
        raise

    return resp.data[0]


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(
    form_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a programme form."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    form = _verify_form_ownership(client, form_id, current_user)
    if not form:
        raise HTTPException(404, detail="Programme form not found")

    client.table("programme_forms").delete().eq("id", str(form_id)).execute()


# ──────────────────────────────────────────────────────────
# Apply
# ──────────────────────────────────────────────────────────


@router.post("/{form_id}/apply", response_model=ProgrammeFormApplyResponse)
def apply_form(
    form_id: UUID,
    payload: ProgrammeFormApply,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Apply a programme form to athletes, creating training sessions."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    form = _verify_form_ownership(client, form_id, current_user)
    if not form:
        raise HTTPException(404, detail="Programme form not found")

    form_data = form.get("form_data", {})
    sessions_def = form_data.get("sessions", [])
    if not sessions_def:
        raise HTTPException(400, detail="Form has no sessions to apply")

    # Verify athletes
    athlete_id_strs = payload.athlete_ids
    athletes_resp = (
        client.table("athletes")
        .select("id, first_name, surname")
        .eq("coach_id", str(current_user.id))
        .in_("id", athlete_id_strs)
        .execute()
    )
    found_ids = {row["id"] for row in athletes_resp.data}
    missing = [aid for aid in athlete_id_strs if aid not in found_ids]
    if missing:
        raise HTTPException(400, detail=f"Athletes not found or not owned: {missing}")

    num_weeks = form.get("num_weeks", 4)

    # Build session rows and prescription rows for all athletes × weeks × sessions
    session_rows = []
    # Track (athlete_id, week, session_index) -> list of prescription dicts
    session_prescription_map: list[list[dict]] = []

    for athlete_id_str in athlete_id_strs:
        for week in range(1, num_weeks + 1):
            for sess_idx, session_def in enumerate(sessions_def):
                session_date = payload.start_date + timedelta(
                    weeks=week - 1,
                    days=sess_idx,
                )
                row = {
                    "athlete_id": athlete_id_str,
                    "session_date": session_date.isoformat(),
                    "training_type": "Programme",
                    "status": "assigned",
                    "created_by": str(current_user.id),
                }
                session_rows.append(filter_none(row))

                # Build prescriptions for this session
                prescriptions = _build_prescriptions_for_session(session_def, week)
                session_prescription_map.append(prescriptions)

    # Bulk-insert sessions
    created_sessions_resp = client.table("training_sessions").insert(session_rows).execute()
    if not created_sessions_resp.data:
        raise HTTPException(500, detail="Failed to create training sessions")
    created_sessions = created_sessions_resp.data

    # Link prescriptions to created sessions
    all_prescriptions = []
    for idx, session in enumerate(created_sessions):
        for p in session_prescription_map[idx]:
            p["session_id"] = session["id"]
            all_prescriptions.append(p)

    # Bulk-insert prescriptions in chunks
    if all_prescriptions:
        chunk_size = 500
        for i in range(0, len(all_prescriptions), chunk_size):
            chunk = all_prescriptions[i : i + chunk_size]
            client.table("exercise_prescriptions").insert(chunk).execute()

    sessions_per_athlete = len(created_sessions) // len(athlete_id_strs) if athlete_id_strs else 0

    return ProgrammeFormApplyResponse(
        created_count=len(created_sessions),
        sessions_per_athlete=sessions_per_athlete,
    )


def _build_prescriptions_for_session(session_def: dict, week: int) -> list[dict]:
    """Build prescription rows for a single session definition and week number.

    Args:
        session_def: Session definition from form_data.
        week: Current week number (1-indexed).

    Returns:
        List of prescription dicts (without session_id - added later).
    """
    prescriptions: list[dict] = []
    set_counter = 1
    sections = session_def.get("sections", [])

    for section in sections:
        section_type = section.get("type", "")
        exercises = section.get("exercises", [])

        if section_type == "core_circuit":
            # Circuit expansion: interleave exercises × circuit_sets rounds
            circuit_sets = section.get("circuit_sets", 1)
            for _round in range(circuit_sets):
                for ex in exercises:
                    reps_text = ex.get("description", "")
                    prescriptions.append(filter_none({
                        "exercise_name": ex.get("exercise_name", "Unknown"),
                        "exercise_category": "Circuit",
                        "set_number": set_counter,
                        "reps": _parse_reps_int(reps_text),
                        "reps_text": reps_text or None,
                        "section_type": section_type,
                    }))
                    set_counter += 1
        else:
            # Regular section with exercises
            for ex in exercises:
                progressive = ex.get("progressive", False)

                if progressive and ex.get("weeks"):
                    # Progressive exercise: use week-specific data
                    weeks_data = ex.get("weeks", [])
                    week_idx = week - 1
                    if week_idx < len(weeks_data):
                        week_entry = weeks_data[week_idx]
                    else:
                        # Fall back to last available week
                        week_entry = weeks_data[-1] if weeks_data else {}

                    num_sets = week_entry.get("sets", 1)
                    reps_text = week_entry.get("reps", "")
                    recommended_weight = week_entry.get("weight_kg")

                    for _set_num in range(1, num_sets + 1):
                        prescriptions.append(filter_none({
                            "exercise_name": ex.get("exercise_name", "Unknown"),
                            "exercise_category": ex.get("exercise_category"),
                            "set_number": set_counter,
                            "reps": _parse_reps_int(str(reps_text)) if reps_text else None,
                            "reps_text": str(reps_text) if reps_text else None,
                            "recommended_weight_kg": recommended_weight,
                            "section_type": section_type,
                            "rest_seconds": ex.get("rest_seconds"),
                        }))
                        set_counter += 1
                else:
                    # Simple (non-progressive) exercise with description
                    description = ex.get("description", "")
                    prescriptions.append(filter_none({
                        "exercise_name": ex.get("exercise_name", "Unknown"),
                        "exercise_category": ex.get("exercise_category"),
                        "set_number": set_counter,
                        "reps": _parse_reps_int(description),
                        "reps_text": description or None,
                        "section_type": section_type,
                    }))
                    set_counter += 1

    return prescriptions
