"""Metabolic profiling API router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.metabolic_profile import (
    MetabolicProfileCreate,
    MetabolicProfileListItem,
    MetabolicProfileResponse,
    MetabolicProfileUpdate,
)
from app.services.metabolic_engine import (
    calculate_metabolic_profile,
    generate_insights,
    sum_watts,
)

router = APIRouter(prefix="/metabolic", tags=["metabolic"])


def _verify_profile_ownership(client, profile_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify profile exists and belongs to a user-accessible athlete. Returns profile data or None."""
    response = (
        client.table("metabolic_profiles")
        .select("*, athletes!inner(coach_id, user_id)")
        .eq("id", str(profile_id))
        .execute()
    )
    if not response.data:
        return None
    row = response.data[0]
    athlete_data = row.get("athletes", {})
    if current_user.role in ("coach", "admin"):
        if str(athlete_data.get("coach_id")) != str(current_user.id):
            return None
    elif current_user.role == "athlete":
        if str(athlete_data.get("user_id")) != str(current_user.id):
            return None
    else:
        return None
    profile = {k: v for k, v in row.items() if k != "athletes"}
    return profile


def _compute_and_store(
    client,
    profile_data: dict,
    body_mass_kg: float,
    resting_lactate: float,
    la_peaks: list[float],
    mech_work: list[float],
) -> dict:
    """Run engine, merge computed fields into profile_data, and return the stored row."""
    result = calculate_metabolic_profile(body_mass_kg, resting_lactate, la_peaks, mech_work)
    insights = generate_insights(result, body_mass_kg)

    profile_data["alactic_capacity_j"] = round(result.alactic_capacity, 1)
    profile_data["max_glycolytic_power_w"] = round(result.max_glycolytic_power, 1) if result.max_glycolytic_power is not None else None
    profile_data["anaerobic_cost"] = round(result.anaerobic_cost, 4) if result.anaerobic_cost is not None else None
    profile_data["fatigue_slope_w"] = round(result.fatigue_slope, 1) if result.fatigue_slope is not None else None
    profile_data["mech_work_sprint_1_j"] = round(mech_work[0], 1)
    profile_data["mech_work_sprint_2_j"] = round(mech_work[1], 1)
    profile_data["mech_work_sprint_3_j"] = round(mech_work[2], 1)
    profile_data["alactic_1_j"] = round(result.alactic[0], 1)
    profile_data["alactic_2_j"] = round(result.alactic[1], 1)
    profile_data["alactic_3_j"] = round(result.alactic[2], 1)
    profile_data["glycolytic_1_j"] = round(result.glycolytic[0], 1)
    profile_data["glycolytic_2_j"] = round(result.glycolytic[1], 1)
    profile_data["glycolytic_3_j"] = round(result.glycolytic[2], 1)

    return profile_data, insights, result.warnings


@router.post(
    "/profiles",
    response_model=MetabolicProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    athlete_id: UUID,
    profile: MetabolicProfileCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a metabolic profile with computed results."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    la_peaks = [profile.la_peak_1_mmol, profile.la_peak_2_mmol, profile.la_peak_3_mmol]
    trim_1 = profile.trim_1_s or 0
    trim_2 = profile.trim_2_s or 0
    trim_3 = profile.trim_3_s or 0

    # Compute mechanical work
    if profile.data_source == "ble" and profile.sprint_1_samples:
        mech_work = [
            sum_watts(profile.sprint_1_samples or [], 0, 10, trim_1),
            sum_watts(profile.sprint_2_samples or [], 10, 20, trim_2),
            sum_watts(profile.sprint_3_samples or [], 20, 30, trim_3),
        ]
        # Compute avg power from samples
        sprint_1_avg = mech_work[0] / max(10 - trim_1, 0.1)
        sprint_2_avg = mech_work[1] / max(10 - trim_2, 0.1)
        sprint_3_avg = mech_work[2] / max(10 - trim_3, 0.1)
    else:
        # Manual mode: avg_power * 10 = mech_work
        sprint_1_avg = profile.sprint_1_avg_power_w or 0
        sprint_2_avg = profile.sprint_2_avg_power_w or 0
        sprint_3_avg = profile.sprint_3_avg_power_w or 0
        mech_work = [sprint_1_avg * 10, sprint_2_avg * 10, sprint_3_avg * 10]

    profile_data = {
        "athlete_id": str(athlete_id),
        "test_date": str(profile.test_date),
        "body_mass_kg": profile.body_mass_kg,
        "data_source": profile.data_source,
        "resting_lactate_mmol": profile.resting_lactate_mmol,
        "la_peak_1_mmol": profile.la_peak_1_mmol,
        "la_peak_2_mmol": profile.la_peak_2_mmol,
        "la_peak_3_mmol": profile.la_peak_3_mmol,
        "sprint_1_avg_power_w": round(sprint_1_avg, 1),
        "sprint_2_avg_power_w": round(sprint_2_avg, 1),
        "sprint_3_avg_power_w": round(sprint_3_avg, 1),
        "trim_1_s": trim_1,
        "trim_2_s": trim_2,
        "trim_3_s": trim_3,
        "notes": profile.notes,
    }

    # Store samples for BLE
    if profile.data_source == "ble":
        profile_data["sprint_1_samples"] = profile.sprint_1_samples
        profile_data["sprint_2_samples"] = profile.sprint_2_samples
        profile_data["sprint_3_samples"] = profile.sprint_3_samples

    # Compute and merge engine results
    profile_data, insights, warnings = _compute_and_store(
        client, profile_data,
        profile.body_mass_kg,
        profile.resting_lactate_mmol,
        la_peaks, mech_work,
    )

    try:
        response = client.table("metabolic_profiles").insert(profile_data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A metabolic profile on this date already exists for this athlete")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile",
        )

    row = response.data[0]
    return _build_response(row, insights, warnings)


@router.get(
    "/profiles/athlete/{athlete_id}",
    response_model=List[MetabolicProfileListItem],
)
def list_profiles(
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List metabolic profiles for an athlete (compact, no samples)."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    response = (
        client.table("metabolic_profiles")
        .select("id, athlete_id, test_date, body_mass_kg, data_source, alactic_capacity_j, max_glycolytic_power_w, created_at, updated_at")
        .eq("athlete_id", str(athlete_id))
        .order("test_date", desc=True)
        .execute()
    )

    return [
        MetabolicProfileListItem(
            id=p["id"],
            athlete_id=p["athlete_id"],
            test_date=p["test_date"],
            body_mass_kg=float(p["body_mass_kg"]),
            data_source=p["data_source"],
            alactic_capacity_j=float(p["alactic_capacity_j"]) if p.get("alactic_capacity_j") is not None else None,
            max_glycolytic_power_w=float(p["max_glycolytic_power_w"]) if p.get("max_glycolytic_power_w") is not None else None,
            created_at=p["created_at"],
            updated_at=p["updated_at"],
        )
        for p in (response.data or [])
    ]


@router.get(
    "/profiles/{profile_id}",
    response_model=MetabolicProfileResponse,
)
def get_profile(
    profile_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single metabolic profile with full detail."""
    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Re-compute insights from stored values
    la_peaks = [
        float(profile["la_peak_1_mmol"]),
        float(profile["la_peak_2_mmol"]),
        float(profile["la_peak_3_mmol"]),
    ]
    mech_work = [
        float(profile["mech_work_sprint_1_j"]) if profile.get("mech_work_sprint_1_j") else 0,
        float(profile["mech_work_sprint_2_j"]) if profile.get("mech_work_sprint_2_j") else 0,
        float(profile["mech_work_sprint_3_j"]) if profile.get("mech_work_sprint_3_j") else 0,
    ]
    body_mass = float(profile["body_mass_kg"])

    result = calculate_metabolic_profile(
        body_mass, float(profile["resting_lactate_mmol"]), la_peaks, mech_work
    )
    insights = generate_insights(result, body_mass)

    return _build_response(profile, insights, result.warnings)


@router.patch(
    "/profiles/{profile_id}",
    response_model=MetabolicProfileResponse,
)
def update_profile(
    profile_id: UUID,
    update: MetabolicProfileUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a metabolic profile. Only trims (BLE) and notes allowed."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    update_data = update.model_dump(exclude_unset=True)
    trims_changed = any(k in update_data for k in ("trim_1_s", "trim_2_s", "trim_3_s"))

    # Manual profiles cannot have trims updated
    if trims_changed and profile["data_source"] == "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trim values cannot be updated for manual profiles",
        )

    if not update_data:
        # Nothing to update, return current
        return get_profile(profile_id, current_user)

    # Apply update
    client.table("metabolic_profiles").update(update_data).eq("id", str(profile_id)).execute()

    # If trims changed on BLE, recalculate
    if trims_changed and profile["data_source"] == "ble":
        # Re-fetch profile with updated trims
        refetch = client.table("metabolic_profiles").select("*").eq("id", str(profile_id)).execute()
        if refetch.data:
            profile = refetch.data[0]

        trim_1 = float(profile.get("trim_1_s") or 0)
        trim_2 = float(profile.get("trim_2_s") or 0)
        trim_3 = float(profile.get("trim_3_s") or 0)

        # Recalculate mech work from stored samples
        mech_work = [
            sum_watts(profile.get("sprint_1_samples") or [], 0, 10, trim_1),
            sum_watts(profile.get("sprint_2_samples") or [], 10, 20, trim_2),
            sum_watts(profile.get("sprint_3_samples") or [], 20, 30, trim_3),
        ]

        la_peaks = [
            float(profile["la_peak_1_mmol"]),
            float(profile["la_peak_2_mmol"]),
            float(profile["la_peak_3_mmol"]),
        ]
        body_mass = float(profile["body_mass_kg"])

        recalc_data = {}
        recalc_data, insights, warnings = _compute_and_store(
            client, recalc_data,
            body_mass,
            float(profile["resting_lactate_mmol"]),
            la_peaks, mech_work,
        )

        # Update avg power from recalculated work
        recalc_data["sprint_1_avg_power_w"] = round(mech_work[0] / max(10 - trim_1, 0.1), 1)
        recalc_data["sprint_2_avg_power_w"] = round(mech_work[1] / max(10 - trim_2, 0.1), 1)
        recalc_data["sprint_3_avg_power_w"] = round(mech_work[2] / max(10 - trim_3, 0.1), 1)

        client.table("metabolic_profiles").update(recalc_data).eq("id", str(profile_id)).execute()

    return get_profile(profile_id, current_user)


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_profile(
    profile_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a metabolic profile."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    profile = _verify_profile_ownership(client, profile_id, current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    client.table("metabolic_profiles").delete().eq("id", str(profile_id)).execute()
    return None


def _build_response(
    row: dict,
    insights: list[dict] | None = None,
    warnings: list[str] | None = None,
) -> MetabolicProfileResponse:
    """Build a MetabolicProfileResponse from a DB row."""
    def _float(val):
        return float(val) if val is not None else None

    return MetabolicProfileResponse(
        id=row["id"],
        athlete_id=row["athlete_id"],
        test_date=row["test_date"],
        body_mass_kg=float(row["body_mass_kg"]),
        data_source=row["data_source"],
        resting_lactate_mmol=float(row["resting_lactate_mmol"]),
        la_peak_1_mmol=float(row["la_peak_1_mmol"]),
        la_peak_2_mmol=float(row["la_peak_2_mmol"]),
        la_peak_3_mmol=float(row["la_peak_3_mmol"]),
        sprint_1_avg_power_w=_float(row.get("sprint_1_avg_power_w")),
        sprint_2_avg_power_w=_float(row.get("sprint_2_avg_power_w")),
        sprint_3_avg_power_w=_float(row.get("sprint_3_avg_power_w")),
        alactic_capacity_j=_float(row.get("alactic_capacity_j")),
        max_glycolytic_power_w=_float(row.get("max_glycolytic_power_w")),
        anaerobic_cost=_float(row.get("anaerobic_cost")),
        fatigue_slope_w=_float(row.get("fatigue_slope_w")),
        mech_work_sprint_1_j=_float(row.get("mech_work_sprint_1_j")),
        mech_work_sprint_2_j=_float(row.get("mech_work_sprint_2_j")),
        mech_work_sprint_3_j=_float(row.get("mech_work_sprint_3_j")),
        alactic_1_j=_float(row.get("alactic_1_j")),
        alactic_2_j=_float(row.get("alactic_2_j")),
        alactic_3_j=_float(row.get("alactic_3_j")),
        glycolytic_1_j=_float(row.get("glycolytic_1_j")),
        glycolytic_2_j=_float(row.get("glycolytic_2_j")),
        glycolytic_3_j=_float(row.get("glycolytic_3_j")),
        trim_1_s=_float(row.get("trim_1_s")) or 0,
        trim_2_s=_float(row.get("trim_2_s")) or 0,
        trim_3_s=_float(row.get("trim_3_s")) or 0,
        sprint_1_samples=row.get("sprint_1_samples"),
        sprint_2_samples=row.get("sprint_2_samples"),
        sprint_3_samples=row.get("sprint_3_samples"),
        notes=row.get("notes"),
        insights=insights,
        warnings=warnings,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
