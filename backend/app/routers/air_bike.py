"""Air bike sprint test and BLE recording API router."""

from statistics import mean
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.air_bike import (
    DEFAULT_SPLIT_SCHEME,
    AirBikeSprintResponse,
    AirBikeTestCreate,
    AirBikeTestListItem,
    AirBikeTestResponse,
    AirBikeTestUpdate,
)
from app.schemas.air_bike_recording import (
    AirBikeRecordingCreate,
    AirBikeRecordingListItem,
    AirBikeRecordingResponse,
)

router = APIRouter(prefix="/air-bike", tags=["air-bike"])


def _verify_test_ownership(client, test_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify test exists and belongs to a user-accessible athlete. Returns test data or None."""
    response = (
        client.table("air_bike_tests")
        .select("*, athletes!inner(coach_id, user_id)")
        .eq("id", str(test_id))
        .execute()
    )
    if not response.data:
        return None
    test = response.data[0]
    athlete_data = test.get("athletes", {})
    if current_user.role in ("coach", "admin"):
        if str(athlete_data.get("coach_id")) != str(current_user.id):
            return None
    elif current_user.role == "athlete":
        if str(athlete_data.get("user_id")) != str(current_user.id):
            return None
    else:
        return None
    test.pop("athletes", None)
    return test


@router.post(
    "/tests",
    response_model=AirBikeTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test(
    athlete_id: UUID,
    test: AirBikeTestCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create an air bike test with nested sprints."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    test_data = {
        "athlete_id": str(athlete_id),
        "test_date": str(test.test_date),
        "body_mass_kg": test.body_mass_kg,
        "split_scheme": test.split_scheme,
        "notes": test.notes,
    }

    try:
        test_response = client.table("air_bike_tests").insert(test_data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A test on this date already exists for this athlete")

    if not test_response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test",
        )

    test_row = test_response.data[0]
    test_id = test_row["id"]

    sprints_data = [
        {
            "test_id": test_id,
            "sprint_number": s.sprint_number,
            "power_7s": s.power_7s,
            "power_14s": s.power_14s,
            "power_17s": s.power_17s,
            "power_27s": s.power_27s,
            "blood_lactate_mmol": s.blood_lactate_mmol,
        }
        for s in test.sprints
    ]

    sprints_response = client.table("air_bike_sprints").insert(sprints_data).execute()
    sprints_rows = sprints_response.data or []

    return AirBikeTestResponse(
        id=test_row["id"],
        athlete_id=test_row["athlete_id"],
        test_date=test_row["test_date"],
        body_mass_kg=float(test_row["body_mass_kg"]),
        split_scheme=test_row.get("split_scheme") or DEFAULT_SPLIT_SCHEME,
        notes=test_row.get("notes"),
        sprints=[AirBikeSprintResponse(**s) for s in sprints_rows],
        created_at=test_row["created_at"],
        updated_at=test_row["updated_at"],
    )


@router.get(
    "/tests/athlete/{athlete_id}",
    response_model=List[AirBikeTestListItem],
)
def list_tests(
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List air bike tests for an athlete."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    query = (
        client.table("air_bike_tests")
        .select("*")
        .eq("athlete_id", str(athlete_id))
        .order("test_date", desc=True)
    )

    tests_response = query.execute()
    tests = tests_response.data or []

    # Fetch all sprints for these tests in one query (N+1 prevention)
    test_ids = [t["id"] for t in tests]
    sprints_by_test: dict[str, list[dict]] = {}

    if test_ids:
        sprints_response = (
            client.table("air_bike_sprints")
            .select("*")
            .in_("test_id", test_ids)
            .order("sprint_number")
            .execute()
        )
        for s in sprints_response.data or []:
            tid = s["test_id"]
            if tid not in sprints_by_test:
                sprints_by_test[tid] = []
            sprints_by_test[tid].append(s)

    result = []
    for t in tests:
        sprints = sprints_by_test.get(t["id"], [])
        max_power = None
        if sprints:
            # Only one mid split is populated per protocol, so skip NULLs.
            all_powers = [
                float(v)
                for s in sprints
                for v in (
                    s.get("power_7s"),
                    s.get("power_14s"),
                    s.get("power_17s"),
                    s.get("power_27s"),
                )
                if v is not None
            ]
            max_power = max(all_powers) if all_powers else None

        result.append(
            AirBikeTestListItem(
                id=t["id"],
                athlete_id=t["athlete_id"],
                test_date=t["test_date"],
                body_mass_kg=float(t["body_mass_kg"]),
                split_scheme=t.get("split_scheme") or DEFAULT_SPLIT_SCHEME,
                notes=t.get("notes"),
                sprint_count=len(sprints),
                max_power_w=max_power,
                created_at=t["created_at"],
                updated_at=t["updated_at"],
            )
        )

    return result


@router.get(
    "/tests/{test_id}",
    response_model=AirBikeTestResponse,
)
def get_test(
    test_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single air bike test with sprints."""
    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    sprints_response = (
        client.table("air_bike_sprints")
        .select("*")
        .eq("test_id", str(test_id))
        .order("sprint_number")
        .execute()
    )
    sprints_rows = sprints_response.data or []

    return AirBikeTestResponse(
        id=test["id"],
        athlete_id=test["athlete_id"],
        test_date=test["test_date"],
        body_mass_kg=float(test["body_mass_kg"]),
        split_scheme=test.get("split_scheme") or DEFAULT_SPLIT_SCHEME,
        notes=test.get("notes"),
        sprints=[AirBikeSprintResponse(**s) for s in sprints_rows],
        created_at=test["created_at"],
        updated_at=test["updated_at"],
    )


@router.patch(
    "/tests/{test_id}",
    response_model=AirBikeTestResponse,
)
def update_test(
    test_id: UUID,
    update: AirBikeTestUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update an air bike test. If sprints are provided, replaces all existing sprints."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    update_data = update.model_dump(exclude_unset=True, exclude={"sprints"})
    # Replacing the sprints can change the protocol, so keep split_scheme in step.
    if update.sprints is not None:
        update_data["split_scheme"] = update.split_scheme
    if update_data:
        if "test_date" in update_data and update_data["test_date"] is not None:
            update_data["test_date"] = str(update_data["test_date"])
        response = (
            client.table("air_bike_tests")
            .update(update_data)
            .eq("id", str(test_id))
            .execute()
        )
        if response.data:
            test = response.data[0]

    # Replace sprints if provided (replace-all semantics)
    if update.sprints is not None:
        client.table("air_bike_sprints").delete().eq("test_id", str(test_id)).execute()
        sprints_data = [
            {
                "test_id": str(test_id),
                "sprint_number": s.sprint_number,
                "power_7s": s.power_7s,
                "power_14s": s.power_14s,
                "power_17s": s.power_17s,
                "power_27s": s.power_27s,
                "blood_lactate_mmol": s.blood_lactate_mmol,
            }
            for s in update.sprints
        ]
        if sprints_data:
            client.table("air_bike_sprints").insert(sprints_data).execute()

    # Re-fetch for response
    return get_test(test_id, current_user)


@router.delete(
    "/tests/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_test(
    test_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an air bike test (CASCADE deletes sprints)."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    client.table("air_bike_tests").delete().eq("id", str(test_id)).execute()
    return None


# --- BLE Recording Endpoints ---


def _verify_recording_ownership(client, recording_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify recording exists and belongs to a user-accessible athlete."""
    response = (
        client.table("air_bike_recordings")
        .select("*, athletes!inner(coach_id, user_id)")
        .eq("id", str(recording_id))
        .execute()
    )
    if not response.data:
        return None
    recording = response.data[0]
    athlete_data = recording.get("athletes", {})
    if current_user.role in ("coach", "admin"):
        if str(athlete_data.get("coach_id")) != str(current_user.id):
            return None
    elif current_user.role == "athlete":
        if str(athlete_data.get("user_id")) != str(current_user.id):
            return None
    else:
        return None
    recording.pop("athletes", None)
    return recording


def _compute_recording_stats(samples: list[dict]) -> dict:
    """Compute summary statistics from BLE samples."""
    watts_vals = [s.get("watts", 0) for s in samples if s.get("watts") is not None]
    cadence_vals = [s.get("cadence_rpm", 0) for s in samples if s.get("cadence_rpm") is not None]
    speed_vals = [s.get("speed_kmh", 0) for s in samples if s.get("speed_kmh") is not None]
    distance_vals = [s.get("distance_m", 0) for s in samples if s.get("distance_m") is not None]
    calorie_vals = [s.get("calories_kcal", 0) for s in samples if s.get("calories_kcal") is not None]

    # Power integration for total work
    total_work = 0.0
    sorted_samples = sorted(samples, key=lambda s: s.get("elapsed_ms", 0))
    for i, sample in enumerate(sorted_samples):
        w = sample.get("watts", 0) or 0
        if i == 0:
            if len(sorted_samples) > 1:
                dt = (sorted_samples[1].get("elapsed_ms", 0) - sorted_samples[0].get("elapsed_ms", 0)) / 1000
            else:
                dt = 1.0
        else:
            dt = (sorted_samples[i].get("elapsed_ms", 0) - sorted_samples[i - 1].get("elapsed_ms", 0)) / 1000
        dt = max(0.1, min(3.0, dt))
        total_work += w * dt

    return {
        "avg_power_w": round(mean(watts_vals), 1) if watts_vals else None,
        "peak_power_w": round(max(watts_vals), 1) if watts_vals else None,
        "total_work_j": round(total_work, 1),
        "avg_cadence_rpm": round(mean(cadence_vals), 1) if cadence_vals else None,
        "peak_cadence_rpm": round(max(cadence_vals), 1) if cadence_vals else None,
        "avg_speed_kmh": round(mean(speed_vals), 2) if speed_vals else None,
        "total_distance_m": round(max(distance_vals), 1) if distance_vals else None,
        "total_calories_kcal": round(max(calorie_vals), 1) if calorie_vals else None,
    }


@router.post(
    "/recordings",
    response_model=AirBikeRecordingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recording(
    athlete_id: UUID,
    recording: AirBikeRecordingCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create an air bike BLE recording with computed summary stats."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    stats = _compute_recording_stats(recording.samples)

    recording_data = {
        "athlete_id": str(athlete_id),
        "test_date": str(recording.test_date),
        "duration_s": recording.duration_s,
        "samples": recording.samples,
        "notes": recording.notes,
        **stats,
    }

    response = client.table("air_bike_recordings").insert(recording_data).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create recording",
        )

    row = response.data[0]
    return _build_recording_response(row)


@router.get(
    "/recordings/athlete/{athlete_id}",
    response_model=List[AirBikeRecordingListItem],
)
def list_recordings(
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List air bike recordings for an athlete (compact, no samples)."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    response = (
        client.table("air_bike_recordings")
        .select("id, athlete_id, test_date, duration_s, avg_power_w, peak_power_w, total_work_j, notes, created_at, updated_at")
        .eq("athlete_id", str(athlete_id))
        .order("test_date", desc=True)
        .execute()
    )

    return [
        AirBikeRecordingListItem(
            id=r["id"],
            athlete_id=r["athlete_id"],
            test_date=r["test_date"],
            duration_s=int(r["duration_s"]),
            avg_power_w=float(r["avg_power_w"]) if r.get("avg_power_w") is not None else None,
            peak_power_w=float(r["peak_power_w"]) if r.get("peak_power_w") is not None else None,
            total_work_j=float(r["total_work_j"]) if r.get("total_work_j") is not None else None,
            notes=r.get("notes"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in (response.data or [])
    ]


@router.get(
    "/recordings/{recording_id}",
    response_model=AirBikeRecordingResponse,
)
def get_recording(
    recording_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single air bike recording with full samples."""
    client = get_client_or_503()

    recording = _verify_recording_ownership(client, recording_id, current_user)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )

    return _build_recording_response(recording)


@router.delete(
    "/recordings/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recording(
    recording_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an air bike recording."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    recording = _verify_recording_ownership(client, recording_id, current_user)
    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )

    client.table("air_bike_recordings").delete().eq("id", str(recording_id)).execute()
    return None


def _build_recording_response(row: dict) -> AirBikeRecordingResponse:
    """Build an AirBikeRecordingResponse from a DB row."""
    def _float(val):
        return float(val) if val is not None else None

    return AirBikeRecordingResponse(
        id=row["id"],
        athlete_id=row["athlete_id"],
        test_date=row["test_date"],
        duration_s=int(row["duration_s"]),
        avg_power_w=_float(row.get("avg_power_w")),
        peak_power_w=_float(row.get("peak_power_w")),
        total_work_j=_float(row.get("total_work_j")),
        avg_cadence_rpm=_float(row.get("avg_cadence_rpm")),
        peak_cadence_rpm=_float(row.get("peak_cadence_rpm")),
        avg_speed_kmh=_float(row.get("avg_speed_kmh")),
        total_distance_m=_float(row.get("total_distance_m")),
        total_calories_kcal=_float(row.get("total_calories_kcal")),
        samples=row.get("samples"),
        notes=row.get("notes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
