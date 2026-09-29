"""VBT load-velocity profile API router."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.vbt_profile import (
    VbtAnalysis,
    VbtPredictionRequest,
    VbtPredictionResponse,
    VbtProfileCreate,
    VbtProfileListItem,
    VbtProfileResponse,
    VbtProfileUpdate,
    VbtSetResponse,
)
from app.services.vbt_engine import (
    build_analysis,
    get_default_mvt,
    predict_load,
    predict_velocity,
)

router = APIRouter(prefix="/vbt", tags=["vbt"])


def _verify_profile_ownership(client, profile_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify profile exists and belongs to a user-accessible athlete. Returns profile data or None."""
    response = (
        client.table("vbt_profiles")
        .select("*, athletes!inner(coach_id, user_id)")
        .eq("id", str(profile_id))
        .execute()
    )
    if not response.data:
        return None
    profile = response.data[0]
    athlete_data = profile.get("athletes", {})
    if current_user.role in ("coach", "admin"):
        if str(athlete_data.get("coach_id")) != str(current_user.id):
            return None
    elif current_user.role == "athlete":
        if str(athlete_data.get("user_id")) != str(current_user.id):
            return None
    else:
        return None
    # Remove joined athletes data before returning
    profile.pop("athletes", None)
    return profile


def _build_analysis_for_sets(sets: list[dict], mvt_override: float | None, exercise_name: str) -> VbtAnalysis | None:
    """Build VbtAnalysis from a list of set dicts."""
    loads = []
    velocities = []
    for s in sets:
        v = s.get("mean_velocity_ms") or s.get("peak_velocity_ms")
        if v is not None:
            loads.append(float(s["load_kg"]))
            velocities.append(float(v))

    if len(loads) < 2:
        return None

    mvt = mvt_override if mvt_override is not None else get_default_mvt(exercise_name)
    result = build_analysis(loads, velocities, mvt)
    if result is None:
        return None

    return VbtAnalysis(
        slope=result.slope,
        intercept=result.intercept,
        r_squared=result.r_squared,
        estimated_1rm_kg=result.estimated_1rm_kg,
        v0_ms=result.v0_ms,
        mvt_used_ms=result.mvt_used_ms,
    )


@router.post(
    "/profiles",
    response_model=VbtProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    athlete_id: UUID,
    profile: VbtProfileCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a VBT profile with load-velocity sets."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    # Insert profile
    profile_data = {
        "athlete_id": str(athlete_id),
        "exercise_name": profile.exercise_name,
        "profile_date": str(profile.profile_date),
        "mvt_ms": profile.mvt_ms,
        "notes": profile.notes,
    }

    try:
        profile_response = client.table("vbt_profiles").insert(profile_data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A profile for this exercise on this date already exists")

    if not profile_response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile",
        )

    profile_row = profile_response.data[0]
    profile_id = profile_row["id"]

    # Insert sets
    sets_data = [
        {
            "profile_id": profile_id,
            "set_number": i + 1,
            "load_kg": s.load_kg,
            "mean_velocity_ms": s.mean_velocity_ms,
            "peak_velocity_ms": s.peak_velocity_ms,
            "reps": s.reps,
        }
        for i, s in enumerate(profile.sets)
    ]

    sets_response = client.table("vbt_sets").insert(sets_data).execute()
    sets_rows = sets_response.data or []

    # Build analysis
    analysis = _build_analysis_for_sets(
        sets_rows, profile.mvt_ms, profile.exercise_name
    )

    return VbtProfileResponse(
        id=profile_row["id"],
        athlete_id=profile_row["athlete_id"],
        exercise_name=profile_row["exercise_name"],
        profile_date=profile_row["profile_date"],
        mvt_ms=profile_row.get("mvt_ms"),
        notes=profile_row.get("notes"),
        sets=[VbtSetResponse(**s) for s in sets_rows],
        analysis=analysis,
        created_at=profile_row["created_at"],
        updated_at=profile_row["updated_at"],
    )


@router.get(
    "/profiles/athlete/{athlete_id}",
    response_model=List[VbtProfileListItem],
)
def list_profiles(
    athlete_id: UUID,
    exercise_name: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List VBT profiles for an athlete, optionally filtered by exercise."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    query = (
        client.table("vbt_profiles")
        .select("*")
        .eq("athlete_id", str(athlete_id))
        .order("profile_date", desc=True)
    )

    if exercise_name:
        query = query.eq("exercise_name", exercise_name)

    profiles_response = query.execute()
    profiles = profiles_response.data or []

    # Fetch all sets for these profiles in one query
    profile_ids = [p["id"] for p in profiles]
    sets_by_profile: dict[str, list[dict]] = {}

    if profile_ids:
        sets_response = (
            client.table("vbt_sets")
            .select("*")
            .in_("profile_id", profile_ids)
            .order("set_number")
            .execute()
        )
        for s in sets_response.data or []:
            pid = s["profile_id"]
            if pid not in sets_by_profile:
                sets_by_profile[pid] = []
            sets_by_profile[pid].append(s)

    result = []
    for p in profiles:
        sets = sets_by_profile.get(p["id"], [])
        analysis = _build_analysis_for_sets(sets, p.get("mvt_ms"), p["exercise_name"])
        result.append(
            VbtProfileListItem(
                id=p["id"],
                athlete_id=p["athlete_id"],
                exercise_name=p["exercise_name"],
                profile_date=p["profile_date"],
                mvt_ms=p.get("mvt_ms"),
                notes=p.get("notes"),
                set_count=len(sets),
                analysis=analysis,
                created_at=p["created_at"],
                updated_at=p["updated_at"],
            )
        )

    return result


@router.get(
    "/profiles/{profile_id}",
    response_model=VbtProfileResponse,
)
def get_profile(
    profile_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single VBT profile with sets and analysis."""
    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Fetch sets
    sets_response = (
        client.table("vbt_sets")
        .select("*")
        .eq("profile_id", str(profile_id))
        .order("set_number")
        .execute()
    )
    sets_rows = sets_response.data or []

    analysis = _build_analysis_for_sets(
        sets_rows, profile.get("mvt_ms"), profile["exercise_name"]
    )

    return VbtProfileResponse(
        id=profile["id"],
        athlete_id=profile["athlete_id"],
        exercise_name=profile["exercise_name"],
        profile_date=profile["profile_date"],
        mvt_ms=profile.get("mvt_ms"),
        notes=profile.get("notes"),
        sets=[VbtSetResponse(**s) for s in sets_rows],
        analysis=analysis,
        created_at=profile["created_at"],
        updated_at=profile["updated_at"],
    )


@router.patch(
    "/profiles/{profile_id}",
    response_model=VbtProfileResponse,
)
def update_profile(
    profile_id: UUID,
    update: VbtProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a VBT profile. If sets are provided, replaces all existing sets."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Update profile fields
    update_data = update.model_dump(exclude_unset=True, exclude={"sets"})
    if update_data:
        response = (
            client.table("vbt_profiles")
            .update(update_data)
            .eq("id", str(profile_id))
            .execute()
        )
        if response.data:
            profile = response.data[0]

    # Replace sets if provided (replace-all semantics)
    if update.sets is not None:
        client.table("vbt_sets").delete().eq("profile_id", str(profile_id)).execute()
        sets_data = [
            {
                "profile_id": str(profile_id),
                "set_number": i + 1,
                "load_kg": s.load_kg,
                "mean_velocity_ms": s.mean_velocity_ms,
                "peak_velocity_ms": s.peak_velocity_ms,
                "reps": s.reps,
            }
            for i, s in enumerate(update.sets)
        ]
        if sets_data:
            client.table("vbt_sets").insert(sets_data).execute()

    # Re-fetch for response
    return get_profile(profile_id, current_user)


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_profile(
    profile_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a VBT profile (CASCADE deletes sets)."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    client.table("vbt_profiles").delete().eq("id", str(profile_id)).execute()
    return None


@router.post(
    "/profiles/{profile_id}/predict",
    response_model=VbtPredictionResponse,
)
def predict(
    profile_id: UUID,
    request: VbtPredictionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Velocity threshold calculator.

    Provide either:
    - velocity_ms: predict the load at that velocity
    - percent_1rm: predict the velocity at that %1RM
    """
    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Fetch sets and build analysis
    sets_response = (
        client.table("vbt_sets")
        .select("*")
        .eq("profile_id", str(profile_id))
        .order("set_number")
        .execute()
    )
    sets_rows = sets_response.data or []

    analysis = _build_analysis_for_sets(
        sets_rows, profile.get("mvt_ms"), profile["exercise_name"]
    )
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient data for prediction (need at least 2 sets with mean velocity)",
        )

    if request.velocity_ms is not None:
        # Mode A: velocity → load
        load = predict_load(analysis.slope, analysis.intercept, request.velocity_ms)
        pct = None
        if load and analysis.estimated_1rm_kg:
            pct = round((load / analysis.estimated_1rm_kg) * 100, 1)
        return VbtPredictionResponse(
            predicted_load_kg=load,
            predicted_velocity_ms=request.velocity_ms,
            percent_1rm=pct,
        )

    elif request.percent_1rm is not None:
        # Mode B: %1RM → velocity
        if not analysis.estimated_1rm_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot calculate: no valid 1RM estimate",
            )
        target_load = analysis.estimated_1rm_kg * (request.percent_1rm / 100)
        vel = predict_velocity(analysis.slope, analysis.intercept, target_load)
        return VbtPredictionResponse(
            predicted_load_kg=round(target_load, 1),
            predicted_velocity_ms=round(vel, 3),
            percent_1rm=request.percent_1rm,
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide either velocity_ms or percent_1rm",
    )
