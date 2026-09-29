"""Test reports API router."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.test_report import (
    TestReportCreate,
    TestReportListItem,
    TestReportResponse,
    TestReportUpdate,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _verify_report_ownership(client, report_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify report exists and belongs to the current user. Returns report data or None."""
    response = (
        client.table("test_reports")
        .select("*")
        .eq("id", str(report_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


@router.post(
    "/",
    response_model=TestReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    report: TestReportCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a test report."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, report.athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    report_data = {
        "athlete_id": str(report.athlete_id),
        "coach_id": str(current_user.id),
        "report_date": str(report.report_date),
        "date_range_start": str(report.date_range_start) if report.date_range_start else None,
        "date_range_end": str(report.date_range_end) if report.date_range_end else None,
        "sections": report.sections,
        "notes": report.notes,
    }

    response = client.table("test_reports").insert(report_data).execute()

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create report",
        )

    return TestReportResponse(**response.data[0])


@router.get(
    "/athlete/{athlete_id}",
    response_model=List[TestReportListItem],
)
def list_reports(
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List test reports for an athlete."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    response = (
        client.table("test_reports")
        .select("id, athlete_id, report_date, created_at")
        .eq("athlete_id", str(athlete_id))
        .eq("coach_id", str(current_user.id))
        .order("report_date", desc=True)
        .execute()
    )

    return [TestReportListItem(**r) for r in (response.data or [])]


@router.get(
    "/{report_id}",
    response_model=TestReportResponse,
)
def get_report(
    report_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single test report."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    report = _verify_report_ownership(client, report_id, current_user)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return TestReportResponse(**report)


@router.patch(
    "/{report_id}",
    response_model=TestReportResponse,
)
def update_report(
    report_id: UUID,
    update: TestReportUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a test report."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    report = _verify_report_ownership(client, report_id, current_user)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    update_data = update.model_dump(exclude_unset=True)
    if not update_data:
        return TestReportResponse(**report)

    # Convert dates to strings for Supabase
    for key in ("report_date", "date_range_start", "date_range_end"):
        if key in update_data and update_data[key] is not None:
            update_data[key] = str(update_data[key])

    response = (
        client.table("test_reports")
        .update(update_data)
        .eq("id", str(report_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update report",
        )

    return TestReportResponse(**response.data[0])


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_report(
    report_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a test report."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    report = _verify_report_ownership(client, report_id, current_user)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    client.table("test_reports").delete().eq("id", str(report_id)).execute()
    return None
