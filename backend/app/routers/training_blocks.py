"""Training blocks router.

CRUD for training blocks, block sessions, athlete maxes,
plus apply/preview endpoints for bulk session creation.
"""

from datetime import timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.training_block import (
    AthleteMaxResponse,
    AthleteMaxUpsert,
    BlockApplyRequest,
    BlockApplyResponse,
    BlockPreviewRequest,
    BlockPreviewResponse,
    BlockSessionCreate,
    BlockSessionResponse,
    BlockSessionUpdate,
    TrainingBlockCreate,
    TrainingBlockDetailResponse,
    TrainingBlockResponse,
    TrainingBlockUpdate,
    UnresolvedExercise,
    WeightResolution,
)
from app.services.block_engine import (
    filter_none,
    format_athlete_name,
    get_athlete_1rm,
    resolve_percent_1rm,
    round_to_plate,
    serialize_exercises,
)

router = APIRouter(prefix="/training-blocks", tags=["training-blocks"])


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _verify_block_ownership(client, block_id: UUID, current_user: AuthenticatedUser):
    """Return block row if owned by current user, else None."""
    resp = (
        client.table("training_blocks")
        .select("*")
        .eq("id", str(block_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )
    return resp.data[0] if resp.data else None


def _verify_block_session(client, block_id: UUID, session_id: UUID, current_user: AuthenticatedUser):
    """Return block session if block is owned by current user, else None."""
    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        return None, None
    resp = (
        client.table("block_sessions")
        .select("*")
        .eq("id", str(session_id))
        .eq("block_id", str(block_id))
        .execute()
    )
    session = resp.data[0] if resp.data else None
    return block, session


# ──────────────────────────────────────────────────────────
# Block CRUD
# ──────────────────────────────────────────────────────────


@router.post("/", response_model=TrainingBlockResponse, status_code=status.HTTP_201_CREATED)
def create_block(
    payload: TrainingBlockCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new training block."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    row = {
        "coach_id": str(current_user.id),
        "block_name": payload.block_name,
        "description": payload.description,
        "num_weeks": payload.num_weeks,
        "category": payload.category,
    }
    try:
        resp = client.table("training_blocks").insert(row).execute()
    except Exception as e:
        raise_on_duplicate(e, "A block with this name already exists")
        raise

    if not resp.data:
        raise HTTPException(500, detail="Failed to create training block")
    return resp.data[0]


@router.get("/", response_model=List[TrainingBlockResponse])
def list_blocks(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List training blocks for the current coach."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    resp = (
        client.table("training_blocks")
        .select("*")
        .eq("coach_id", str(current_user.id))
        .order("block_name")
        .execute()
    )
    return resp.data


@router.get("/{block_id}", response_model=TrainingBlockDetailResponse)
def get_block(
    block_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a training block with all sessions."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        raise HTTPException(404, detail="Block not found")

    sessions_resp = (
        client.table("block_sessions")
        .select("*")
        .eq("block_id", str(block_id))
        .order("week_number")
        .order("day_of_week")
        .execute()
    )

    return {**block, "sessions": sessions_resp.data}


@router.patch("/{block_id}", response_model=TrainingBlockResponse)
def update_block(
    block_id: UUID,
    payload: TrainingBlockUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a training block's metadata."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        raise HTTPException(404, detail="Block not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return block

    try:
        resp = (
            client.table("training_blocks")
            .update(updates)
            .eq("id", str(block_id))
            .execute()
        )
    except Exception as e:
        raise_on_duplicate(e, "A block with this name already exists")
        raise

    return resp.data[0]


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(
    block_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a training block (cascades to sessions)."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        raise HTTPException(404, detail="Block not found")

    client.table("training_blocks").delete().eq("id", str(block_id)).execute()


# ──────────────────────────────────────────────────────────
# Block Session CRUD
# ──────────────────────────────────────────────────────────


@router.post(
    "/{block_id}/sessions",
    response_model=BlockSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_block_session(
    block_id: UUID,
    payload: BlockSessionCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Add a session to a training block."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        raise HTTPException(404, detail="Block not found")

    if payload.week_number > block["num_weeks"]:
        raise HTTPException(
            400, detail=f"week_number {payload.week_number} exceeds block num_weeks {block['num_weeks']}"
        )

    row = filter_none({
        "block_id": str(block_id),
        "week_number": payload.week_number,
        "day_of_week": payload.day_of_week,
        "session_name": payload.session_name,
        "training_type": payload.training_type,
        "notes": payload.notes,
        "exercises": serialize_exercises(payload.exercises),
    })

    try:
        resp = client.table("block_sessions").insert(row).execute()
    except Exception as e:
        raise_on_duplicate(e, "A session already exists for this week/day/name")
        raise

    if not resp.data:
        raise HTTPException(500, detail="Failed to create block session")
    return resp.data[0]


@router.patch(
    "/{block_id}/sessions/{session_id}",
    response_model=BlockSessionResponse,
)
def update_block_session(
    block_id: UUID,
    session_id: UUID,
    payload: BlockSessionUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a block session."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block, session = _verify_block_session(client, block_id, session_id, current_user)
    if not block or not session:
        raise HTTPException(404, detail="Block or session not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return session

    # Validate week_number against block
    if "week_number" in updates and updates["week_number"] > block["num_weeks"]:
        raise HTTPException(
            400, detail=f"week_number {updates['week_number']} exceeds block num_weeks {block['num_weeks']}"
        )

    # Serialize exercises JSONB
    if "exercises" in updates and updates["exercises"] is not None:
        updates["exercises"] = serialize_exercises(payload.exercises)

    try:
        resp = (
            client.table("block_sessions")
            .update(updates)
            .eq("id", str(session_id))
            .execute()
        )
    except Exception as e:
        raise_on_duplicate(e, "Cannot update: a session with this week/day/name already exists")
        raise

    return resp.data[0]


@router.delete(
    "/{block_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_block_session(
    block_id: UUID,
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a session from a training block."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block, session = _verify_block_session(client, block_id, session_id, current_user)
    if not block or not session:
        raise HTTPException(404, detail="Block or session not found")

    client.table("block_sessions").delete().eq("id", str(session_id)).execute()


@router.post(
    "/{block_id}/sessions/{session_id}/duplicate",
    response_model=BlockSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_block_session(
    block_id: UUID,
    session_id: UUID,
    target_week: int = Query(..., ge=1, le=16),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Duplicate a block session to another week."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block, session = _verify_block_session(client, block_id, session_id, current_user)
    if not block or not session:
        raise HTTPException(404, detail="Block or session not found")

    if target_week > block["num_weeks"]:
        raise HTTPException(
            400, detail=f"target_week {target_week} exceeds block num_weeks {block['num_weeks']}"
        )

    row = filter_none({
        "block_id": str(block_id),
        "week_number": target_week,
        "day_of_week": session["day_of_week"],
        "session_name": session["session_name"],
        "training_type": session["training_type"],
        "notes": session["notes"],
        "exercises": session["exercises"],
    })

    try:
        resp = client.table("block_sessions").insert(row).execute()
    except Exception as e:
        raise_on_duplicate(e, "Cannot duplicate: session already exists in target week")
        raise

    if not resp.data:
        raise HTTPException(500, detail="Failed to duplicate session")
    return resp.data[0]


# ──────────────────────────────────────────────────────────
# Athlete Maxes CRUD
# ──────────────────────────────────────────────────────────


@router.get("/athlete-maxes/{athlete_id}", response_model=List[AthleteMaxResponse])
def list_athlete_maxes(
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all maxes for an athlete."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(404, detail="Athlete not found")

    resp = (
        client.table("athlete_maxes")
        .select("*")
        .eq("athlete_id", str(athlete_id))
        .order("exercise_name")
        .execute()
    )
    return resp.data


@router.put("/athlete-maxes/{athlete_id}", response_model=AthleteMaxResponse)
def upsert_athlete_max(
    athlete_id: UUID,
    payload: AthleteMaxUpsert,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create or update an athlete max for a given exercise."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(404, detail="Athlete not found")

    row = {
        "athlete_id": str(athlete_id),
        "exercise_name": payload.exercise_name,
        "max_kg": float(payload.max_kg),
        "source": payload.source,
    }

    resp = (
        client.table("athlete_maxes")
        .upsert(row, on_conflict="athlete_id,exercise_name")
        .execute()
    )

    if not resp.data:
        raise HTTPException(500, detail="Failed to save athlete max")
    return resp.data[0]


@router.delete(
    "/athlete-maxes/{athlete_id}/{exercise_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_athlete_max(
    athlete_id: UUID,
    exercise_name: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an athlete max for a given exercise."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(404, detail="Athlete not found")

    resp = (
        client.table("athlete_maxes")
        .select("id")
        .eq("athlete_id", str(athlete_id))
        .ilike("exercise_name", exercise_name)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, detail="Max not found")

    client.table("athlete_maxes").delete().eq("id", resp.data[0]["id"]).execute()


# ──────────────────────────────────────────────────────────
# Apply + Preview
# ──────────────────────────────────────────────────────────


@router.post("/{block_id}/preview", response_model=BlockPreviewResponse)
def preview_block_application(
    block_id: UUID,
    payload: BlockPreviewRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Preview weight resolution for a block application (read-only)."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        raise HTTPException(404, detail="Block not found")

    # Verify athletes
    athlete_id_strs = [str(aid) for aid in payload.athlete_ids]
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

    athlete_map = {row["id"]: row for row in athletes_resp.data}

    # Load block sessions
    sessions_resp = (
        client.table("block_sessions")
        .select("*")
        .eq("block_id", str(block_id))
        .execute()
    )

    # Pre-build percent_1rm cache: exercise_name -> first percent_1rm found
    pct_exercises: set[str] = set()
    pct_cache: dict[str, float] = {}
    for session in sessions_resp.data:
        for ex in session.get("exercises", []):
            name = ex["exercise_name"]
            if ex.get("percent_1rm") is not None and ex.get("weight_kg") is None:
                pct_exercises.add(name)
                if name not in pct_cache:
                    pct_cache[name] = ex["percent_1rm"]

    # Resolve for each athlete × exercise
    resolutions: list[dict] = []
    for athlete_id_str in athlete_id_strs:
        athlete_name = format_athlete_name(athlete_map[athlete_id_str])
        for exercise_name in sorted(pct_exercises):
            pct = pct_cache.get(exercise_name)

            max_1rm, source = get_athlete_1rm(client, athlete_id_str, exercise_name)
            resolved_weight = round_to_plate(max_1rm * pct / 100) if max_1rm is not None and pct else None

            resolutions.append(
                WeightResolution(
                    athlete_id=athlete_id_str,
                    athlete_name=athlete_name,
                    exercise_name=exercise_name,
                    percent_1rm=pct or 0,
                    max_1rm_kg=max_1rm,
                    resolved_weight_kg=resolved_weight,
                    source=source,
                ).model_dump()
            )

    sessions_per_athlete = len(sessions_resp.data)
    total_sessions = sessions_per_athlete * len(athlete_id_strs)

    return BlockPreviewResponse(
        resolutions=[WeightResolution(**r) for r in resolutions],
        total_sessions=total_sessions,
        sessions_per_athlete=sessions_per_athlete,
    )


@router.post("/{block_id}/apply", response_model=BlockApplyResponse)
def apply_block(
    block_id: UUID,
    payload: BlockApplyRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Apply a training block to athletes, creating all sessions."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    block = _verify_block_ownership(client, block_id, current_user)
    if not block:
        raise HTTPException(404, detail="Block not found")

    # Verify athletes
    athlete_id_strs = [str(aid) for aid in payload.athlete_ids]
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

    athlete_map = {row["id"]: row for row in athletes_resp.data}

    # Load block sessions
    sessions_resp = (
        client.table("block_sessions")
        .select("*")
        .eq("block_id", str(block_id))
        .order("week_number")
        .order("day_of_week")
        .execute()
    )
    block_sessions = sessions_resp.data
    if not block_sessions:
        raise HTTPException(400, detail="Block has no sessions to apply")

    # Build session rows for all athletes × block sessions
    session_rows = []
    # Track mapping: (athlete_id, block_session_id) -> session_index for prescription linking
    session_mapping: list[tuple[str, dict]] = []

    for athlete_id_str in athlete_id_strs:
        for bs in block_sessions:
            session_date = payload.start_date + timedelta(
                weeks=bs["week_number"] - 1,
                days=bs["day_of_week"] - 1,
            )
            row = {
                "athlete_id": athlete_id_str,
                "session_date": session_date.isoformat(),
                "training_type": bs["training_type"],
                "notes": bs.get("notes"),
                "status": "assigned",
                "created_by": str(current_user.id),
            }
            session_rows.append(filter_none(row))
            session_mapping.append((athlete_id_str, bs))

    # Bulk-insert sessions
    created_sessions_resp = client.table("training_sessions").insert(session_rows).execute()
    if not created_sessions_resp.data:
        raise HTTPException(500, detail="Failed to create training sessions")
    created_sessions = created_sessions_resp.data

    # Build prescriptions with set expansion and percent resolution
    prescriptions = []
    unresolved: list[UnresolvedExercise] = []
    unresolved_seen: set[tuple[str, str]] = set()

    for idx, session in enumerate(created_sessions):
        athlete_id_str, block_session = session_mapping[idx]
        exercises = block_session.get("exercises", [])

        # Separate circuit vs non-circuit
        circuit_exs = [ex for ex in exercises if ex.get("exercise_category") == "Circuit"]
        non_circuit_exs = [ex for ex in exercises if ex.get("exercise_category") != "Circuit"]

        set_counter = 1

        # Non-circuit: standard set expansion
        for ex in non_circuit_exs:
            num_sets = ex.get("sets", 1) or 1

            # Resolve percentage if needed
            weight_kg = ex.get("weight_kg")
            if ex.get("percent_1rm") is not None and weight_kg is None:
                resolved_weight, source = resolve_percent_1rm(
                    client, athlete_id_str, ex["exercise_name"], ex["percent_1rm"]
                )
                if resolved_weight is not None:
                    weight_kg = resolved_weight
                else:
                    key = (athlete_id_str, ex["exercise_name"])
                    if key not in unresolved_seen:
                        unresolved_seen.add(key)
                        unresolved.append(
                            UnresolvedExercise(
                                athlete_id=athlete_id_str,
                                athlete_name=format_athlete_name(athlete_map.get(athlete_id_str, {})),
                                exercise_name=ex["exercise_name"],
                            )
                        )

            for set_num in range(1, num_sets + 1):
                prescriptions.append(filter_none({
                    "session_id": session["id"],
                    "exercise_name": ex["exercise_name"],
                    "exercise_category": ex.get("exercise_category"),
                    "set_number": set_counter,
                    "reps": ex.get("reps"),
                    "weight_kg": weight_kg,
                    "rest_seconds": ex.get("rest_seconds"),
                    "duration_seconds": ex.get("duration_seconds"),
                    "distance_meters": ex.get("distance_meters"),
                    "intensity_type": ex.get("intensity_type"),
                    "intensity_value": ex.get("intensity_value"),
                    "intensity_min": ex.get("intensity_min"),
                    "intensity_max": ex.get("intensity_max"),
                    "rest_between_reps_seconds": ex.get("rest_between_reps_seconds"),
                    "rep_durations": ex.get("rep_durations"),
                    "rest_between_reps": ex.get("rest_between_reps"),
                    "rep_intensity_values": ex.get("rep_intensity_values"),
                    "notes": ex.get("notes"),
                }))
                set_counter += 1

        # Circuit: interleaved rounds
        if circuit_exs:
            num_rounds = circuit_exs[0].get("sets", 1) or 1
            for _round in range(num_rounds):
                for i, ex in enumerate(circuit_exs):
                    prescriptions.append(filter_none({
                        "session_id": session["id"],
                        "exercise_name": ex["exercise_name"],
                        "exercise_category": "Circuit",
                        "set_number": set_counter,
                        "reps": ex.get("reps"),
                        "duration_seconds": ex.get("duration_seconds"),
                        "rest_seconds": ex.get("rest_seconds"),
                        "notes": ex.get("notes"),
                    }))
                    set_counter += 1

    # Bulk-insert prescriptions in chunks
    if prescriptions:
        chunk_size = 500
        for i in range(0, len(prescriptions), chunk_size):
            chunk = prescriptions[i : i + chunk_size]
            client.table("exercise_prescriptions").insert(chunk).execute()

    # Record application audit
    application_row = {
        "block_id": str(block_id),
        "coach_id": str(current_user.id),
        "athlete_ids": athlete_id_strs,
        "start_date": payload.start_date.isoformat(),
        "sessions_created": len(created_sessions),
    }
    app_resp = client.table("block_applications").insert(application_row).execute()
    application_id = app_resp.data[0]["id"] if app_resp.data else None

    sessions_per_athlete = len(block_sessions)

    return BlockApplyResponse(
        created_count=len(created_sessions),
        sessions_per_athlete=sessions_per_athlete,
        unresolved_exercises=unresolved,
        application_id=application_id,
    )
