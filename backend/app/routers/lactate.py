"""Lactate test API router."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.gas_analysis import (
    GasAnalysisPreviewResponse,
    GasAnalysisResponse,
    GasAnalysisStageSummary,
)
from app.schemas.lactate_test import (
    GasSummary,
    LactateAnalysis,
    LactateAutoDetectResponse,
    LactateStageResponse,
    LactateTestCreate,
    LactateTestListItem,
    LactateTestResponse,
    LactateTestUpdate,
    PiecewiseSegment,
)
from app.services.cpet_engine import compute_fat_max
from app.services.cpet_parser import parse_cpet_file
from app.services.lactate_engine import build_lactate_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lactate", tags=["lactate"])


def _verify_test_ownership(client, test_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify test exists and belongs to a user-accessible athlete. Returns test data or None."""
    response = (
        client.table("lactate_tests")
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
    # Remove joined athletes data before returning
    test.pop("athletes", None)
    return test


def _fetch_gas_summary(client, test_id: str) -> tuple[bool, GasSummary | None]:
    """Fetch gas analysis summary for a test. Returns (has_gas, summary_or_none)."""
    resp = (
        client.table("gas_analysis_data")
        .select("max_fat_oxidation_gh, fat_max_intensity")
        .eq("test_id", test_id)
        .execute()
    )
    if not resp.data:
        return False, None
    row = resp.data[0]
    return True, GasSummary(
        max_fat_oxidation_gh=row.get("max_fat_oxidation_gh"),
        fat_max_intensity=row.get("fat_max_intensity"),
    )


def _fetch_gas_summaries_bulk(client, test_ids: list[str]) -> dict[str, tuple[bool, GasSummary | None]]:
    """Bulk fetch gas summaries for multiple tests."""
    if not test_ids:
        return {}
    resp = (
        client.table("gas_analysis_data")
        .select("test_id, max_fat_oxidation_gh, fat_max_intensity")
        .in_("test_id", test_ids)
        .execute()
    )
    result: dict[str, tuple[bool, GasSummary | None]] = {}
    for row in resp.data or []:
        result[row["test_id"]] = (
            True,
            GasSummary(
                max_fat_oxidation_gh=row.get("max_fat_oxidation_gh"),
                fat_max_intensity=row.get("fat_max_intensity"),
            ),
        )
    return result


def _build_analysis_for_stages(stages: list[dict]) -> LactateAnalysis | None:
    """Build LactateAnalysis from a list of stage dicts."""
    intensities = []
    lactates = []
    for s in stages:
        intensities.append(float(s["intensity_value"]))
        lactates.append(float(s["blood_lactate_mmol"]))

    if len(intensities) < 5:
        return None

    result = build_lactate_analysis(intensities, lactates)
    if result is None:
        return None

    return LactateAnalysis(
        suggested_lt1_value=result.lt1_x,
        suggested_lt1_lactate=result.lt1_lactate,
        suggested_lt2_value=result.lt2_x,
        suggested_lt2_lactate=result.lt2_lactate,
        segments=[
            PiecewiseSegment(
                start_x=seg.start_x,
                end_x=seg.end_x,
                slope=seg.slope,
                intercept=seg.intercept,
            )
            for seg in result.segments
        ],
        total_sse=result.total_sse,
        r_squared=result.r_squared,
    )


@router.post(
    "/tests",
    response_model=LactateTestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test(
    athlete_id: UUID,
    test: LactateTestCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a lactate test with nested stages."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    # Insert test
    test_data = {
        "athlete_id": str(athlete_id),
        "test_date": str(test.test_date),
        "test_type": test.test_type,
        "lt1_value": test.lt1_value,
        "lt1_lactate": test.lt1_lactate,
        "lt1_hr": test.lt1_hr,
        "lt2_value": test.lt2_value,
        "lt2_lactate": test.lt2_lactate,
        "lt2_hr": test.lt2_hr,
        "notes": test.notes,
    }

    try:
        test_response = client.table("lactate_tests").insert(test_data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A test for this type on this date already exists")

    if not test_response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test",
        )

    test_row = test_response.data[0]
    test_id = test_row["id"]

    # Insert stages
    stages_data = [
        {
            "test_id": test_id,
            "stage_number": i + 1,
            "intensity_value": s.intensity_value,
            "heart_rate_bpm": s.heart_rate_bpm,
            "blood_lactate_mmol": s.blood_lactate_mmol,
            "rpe": s.rpe,
        }
        for i, s in enumerate(test.stages)
    ]

    stages_response = client.table("lactate_stages").insert(stages_data).execute()
    stages_rows = stages_response.data or []

    # Build analysis
    analysis = _build_analysis_for_stages(stages_rows)

    return LactateTestResponse(
        id=test_row["id"],
        athlete_id=test_row["athlete_id"],
        test_date=test_row["test_date"],
        test_type=test_row["test_type"],
        lt1_value=test_row.get("lt1_value"),
        lt1_lactate=test_row.get("lt1_lactate"),
        lt1_hr=test_row.get("lt1_hr"),
        lt2_value=test_row.get("lt2_value"),
        lt2_lactate=test_row.get("lt2_lactate"),
        lt2_hr=test_row.get("lt2_hr"),
        notes=test_row.get("notes"),
        stages=[LactateStageResponse(**s) for s in stages_rows],
        analysis=analysis,
        has_gas_analysis=False,
        gas_summary=None,
        created_at=test_row["created_at"],
        updated_at=test_row["updated_at"],
    )


@router.get(
    "/tests/athlete/{athlete_id}",
    response_model=List[LactateTestListItem],
)
def list_tests(
    athlete_id: UUID,
    test_type: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List lactate tests for an athlete, optionally filtered by test type."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    query = (
        client.table("lactate_tests")
        .select("*")
        .eq("athlete_id", str(athlete_id))
        .order("test_date", desc=True)
    )

    if test_type:
        query = query.eq("test_type", test_type)

    tests_response = query.execute()
    tests = tests_response.data or []

    # Fetch all stages for these tests in one query (N+1 prevention)
    test_ids = [t["id"] for t in tests]
    stages_by_test: dict[str, list[dict]] = {}

    if test_ids:
        stages_response = (
            client.table("lactate_stages")
            .select("*")
            .in_("test_id", test_ids)
            .order("stage_number")
            .execute()
        )
        for s in stages_response.data or []:
            tid = s["test_id"]
            if tid not in stages_by_test:
                stages_by_test[tid] = []
            stages_by_test[tid].append(s)

    # Bulk fetch gas analysis summaries
    gas_map = _fetch_gas_summaries_bulk(client, test_ids)

    result = []
    for t in tests:
        stages = stages_by_test.get(t["id"], [])
        analysis = _build_analysis_for_stages(stages)
        has_gas, gas_summary = gas_map.get(t["id"], (False, None))
        result.append(
            LactateTestListItem(
                id=t["id"],
                athlete_id=t["athlete_id"],
                test_date=t["test_date"],
                test_type=t["test_type"],
                lt1_value=t.get("lt1_value"),
                lt1_lactate=t.get("lt1_lactate"),
                lt1_hr=t.get("lt1_hr"),
                lt2_value=t.get("lt2_value"),
                lt2_lactate=t.get("lt2_lactate"),
                lt2_hr=t.get("lt2_hr"),
                notes=t.get("notes"),
                stage_count=len(stages),
                analysis=analysis,
                has_gas_analysis=has_gas,
                gas_summary=gas_summary,
                created_at=t["created_at"],
                updated_at=t["updated_at"],
            )
        )

    return result


@router.get(
    "/tests/{test_id}",
    response_model=LactateTestResponse,
)
def get_test(
    test_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single lactate test with stages and analysis."""
    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    # Fetch stages
    stages_response = (
        client.table("lactate_stages")
        .select("*")
        .eq("test_id", str(test_id))
        .order("stage_number")
        .execute()
    )
    stages_rows = stages_response.data or []

    analysis = _build_analysis_for_stages(stages_rows)

    has_gas, gas_summary = _fetch_gas_summary(client, str(test_id))

    return LactateTestResponse(
        id=test["id"],
        athlete_id=test["athlete_id"],
        test_date=test["test_date"],
        test_type=test["test_type"],
        lt1_value=test.get("lt1_value"),
        lt1_lactate=test.get("lt1_lactate"),
        lt1_hr=test.get("lt1_hr"),
        lt2_value=test.get("lt2_value"),
        lt2_lactate=test.get("lt2_lactate"),
        lt2_hr=test.get("lt2_hr"),
        notes=test.get("notes"),
        stages=[LactateStageResponse(**s) for s in stages_rows],
        analysis=analysis,
        has_gas_analysis=has_gas,
        gas_summary=gas_summary,
        created_at=test["created_at"],
        updated_at=test["updated_at"],
    )


@router.patch(
    "/tests/{test_id}",
    response_model=LactateTestResponse,
)
def update_test(
    test_id: UUID,
    update: LactateTestUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a lactate test. If stages are provided, replaces all existing stages."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    # Update test fields
    update_data = update.model_dump(exclude_unset=True, exclude={"stages"})
    if update_data:
        # Convert date to string for JSON serialization
        if "test_date" in update_data and update_data["test_date"] is not None:
            update_data["test_date"] = str(update_data["test_date"])
        response = (
            client.table("lactate_tests")
            .update(update_data)
            .eq("id", str(test_id))
            .execute()
        )
        if response.data:
            test = response.data[0]

    # Replace stages if provided (replace-all semantics)
    if update.stages is not None:
        client.table("lactate_stages").delete().eq("test_id", str(test_id)).execute()
        stages_data = [
            {
                "test_id": str(test_id),
                "stage_number": i + 1,
                "intensity_value": s.intensity_value,
                "heart_rate_bpm": s.heart_rate_bpm,
                "blood_lactate_mmol": s.blood_lactate_mmol,
                "rpe": s.rpe,
            }
            for i, s in enumerate(update.stages)
        ]
        if stages_data:
            client.table("lactate_stages").insert(stages_data).execute()

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
    """Delete a lactate test (CASCADE deletes stages)."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    client.table("lactate_tests").delete().eq("id", str(test_id)).execute()
    return None


@router.post(
    "/tests/{test_id}/detect",
    response_model=LactateAutoDetectResponse,
)
def auto_detect(
    test_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Run breakpoint detection on a test's stages. Returns suggested LT1/LT2."""
    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found",
        )

    # Fetch stages
    stages_response = (
        client.table("lactate_stages")
        .select("*")
        .eq("test_id", str(test_id))
        .order("stage_number")
        .execute()
    )
    stages_rows = stages_response.data or []

    analysis = _build_analysis_for_stages(stages_rows)

    return LactateAutoDetectResponse(analysis=analysis)


# --- Gas Analysis Endpoints ---


@router.post(
    "/tests/{test_id}/gas-analysis/preview",
    response_model=GasAnalysisPreviewResponse,
)
def preview_gas_analysis(
    test_id: UUID,
    file: UploadFile = File(...),
    stage_duration_seconds: int = Form(180),
    rest_duration_seconds: int = Form(60),
    rest_start_seconds: int = Form(60),
    averaging_method: str = Form("last_60s"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Preview gas analysis parsing without saving. Validates file and returns stage averages."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    if averaging_method not in ("last_60s", "full_stage"):
        raise HTTPException(status_code=400, detail="Invalid averaging method")

    # Read file
    file_bytes = file.file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Fetch lactate stages for intensity mapping
    stages_resp = (
        client.table("lactate_stages")
        .select("intensity_value")
        .eq("test_id", str(test_id))
        .order("stage_number")
        .execute()
    )
    stage_intensities = [s["intensity_value"] for s in (stages_resp.data or [])]

    try:
        result = parse_cpet_file(
            file_bytes=file_bytes,
            filename=file.filename or "upload.xlsx",
            test_type=test["test_type"],
            stage_intensities=stage_intensities,
            rest_start_seconds=rest_start_seconds,
            stage_duration_seconds=stage_duration_seconds,
            rest_duration_seconds=rest_duration_seconds,
            averaging_method=averaging_method,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Compute fat max from preview
    stage_dicts = [sa.to_dict() for sa in result.stage_averages]
    fat_max_result = compute_fat_max(stage_dicts)

    fat_max_resp = None
    if fat_max_result:
        from app.schemas.gas_analysis import FatMaxResult as FatMaxSchema

        fat_max_resp = FatMaxSchema(
            max_fat_oxidation_gh=fat_max_result.max_fat_oxidation_gh,
            fat_max_stage_number=fat_max_result.fat_max_stage_number,
            fat_max_intensity=fat_max_result.fat_max_intensity,
            fat_max_hr=fat_max_result.fat_max_hr,
        )

    return GasAnalysisPreviewResponse(
        interval_seconds=result.interval_seconds,
        stage_count=len(result.stage_averages),
        sample_count=len(result.samples),
        columns_detected=result.columns_detected,
        column_mapping=result.column_mapping,
        stage_averages=[GasAnalysisStageSummary(**sa.to_dict()) for sa in result.stage_averages],
        fat_max=fat_max_resp,
    )


@router.post(
    "/tests/{test_id}/gas-analysis",
    response_model=GasAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_gas_analysis(
    test_id: UUID,
    file: UploadFile = File(...),
    stage_duration_seconds: int = Form(180),
    rest_duration_seconds: int = Form(60),
    rest_start_seconds: int = Form(60),
    averaging_method: str = Form("last_60s"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload and save gas analysis data for a lactate test."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    if averaging_method not in ("last_60s", "full_stage"):
        raise HTTPException(status_code=400, detail="Invalid averaging method")

    # Check for existing gas analysis
    existing = (
        client.table("gas_analysis_data")
        .select("id")
        .eq("test_id", str(test_id))
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Gas analysis already exists for this test. Delete it first.")

    # Read file
    file_bytes = file.file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Fetch lactate stages for intensity mapping
    stages_resp = (
        client.table("lactate_stages")
        .select("intensity_value")
        .eq("test_id", str(test_id))
        .order("stage_number")
        .execute()
    )
    stage_intensities = [s["intensity_value"] for s in (stages_resp.data or [])]

    try:
        result = parse_cpet_file(
            file_bytes=file_bytes,
            filename=file.filename or "upload.xlsx",
            test_type=test["test_type"],
            stage_intensities=stage_intensities,
            rest_start_seconds=rest_start_seconds,
            stage_duration_seconds=stage_duration_seconds,
            rest_duration_seconds=rest_duration_seconds,
            averaging_method=averaging_method,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Compute summary stats
    stage_dicts = [sa.to_dict() for sa in result.stage_averages]
    fat_max = compute_fat_max(stage_dicts)

    # Build insert data
    insert_data = {
        "test_id": str(test_id),
        "interval_seconds": result.interval_seconds,
        "rest_start_seconds": rest_start_seconds,
        "stage_duration_seconds": stage_duration_seconds,
        "rest_duration_seconds": rest_duration_seconds,
        "averaging_method": averaging_method,
        "samples": [s.to_dict() for s in result.samples],
        "stage_averages": stage_dicts,
        "column_mapping": result.column_mapping,
    }

    if fat_max:
        insert_data["max_fat_oxidation_gh"] = fat_max.max_fat_oxidation_gh
        insert_data["fat_max_stage_number"] = fat_max.fat_max_stage_number
        insert_data["fat_max_intensity"] = fat_max.fat_max_intensity
        insert_data["fat_max_hr"] = fat_max.fat_max_hr

    try:
        resp = client.table("gas_analysis_data").insert(insert_data).execute()
    except Exception as e:
        raise_on_duplicate(e, "Gas analysis already exists for this test")

    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to save gas analysis")

    row = resp.data[0]
    return GasAnalysisResponse(
        id=row["id"],
        test_id=row["test_id"],
        interval_seconds=row["interval_seconds"],
        rest_start_seconds=row.get("rest_start_seconds"),
        stage_duration_seconds=row.get("stage_duration_seconds"),
        rest_duration_seconds=row.get("rest_duration_seconds"),
        averaging_method=row.get("averaging_method"),
        samples=row["samples"],
        stage_averages=[GasAnalysisStageSummary(**sa) for sa in row["stage_averages"]],
        column_mapping=row.get("column_mapping"),
        max_fat_oxidation_gh=row.get("max_fat_oxidation_gh"),
        fat_max_stage_number=row.get("fat_max_stage_number"),
        fat_max_intensity=row.get("fat_max_intensity"),
        fat_max_hr=row.get("fat_max_hr"),
        notes=row.get("notes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get(
    "/tests/{test_id}/gas-analysis",
    response_model=GasAnalysisResponse,
)
def get_gas_analysis(
    test_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get gas analysis data for a lactate test."""
    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    resp = (
        client.table("gas_analysis_data")
        .select("*")
        .eq("test_id", str(test_id))
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No gas analysis for this test")

    row = resp.data[0]
    return GasAnalysisResponse(
        id=row["id"],
        test_id=row["test_id"],
        interval_seconds=row["interval_seconds"],
        rest_start_seconds=row.get("rest_start_seconds"),
        stage_duration_seconds=row.get("stage_duration_seconds"),
        rest_duration_seconds=row.get("rest_duration_seconds"),
        averaging_method=row.get("averaging_method"),
        samples=row["samples"],
        stage_averages=[GasAnalysisStageSummary(**sa) for sa in row["stage_averages"]],
        column_mapping=row.get("column_mapping"),
        max_fat_oxidation_gh=row.get("max_fat_oxidation_gh"),
        fat_max_stage_number=row.get("fat_max_stage_number"),
        fat_max_intensity=row.get("fat_max_intensity"),
        fat_max_hr=row.get("fat_max_hr"),
        notes=row.get("notes"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete(
    "/tests/{test_id}/gas-analysis",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_gas_analysis(
    test_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete gas analysis data for a lactate test."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    test = _verify_test_ownership(client, test_id, current_user)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    client.table("gas_analysis_data").delete().eq("test_id", str(test_id)).execute()
    return None
