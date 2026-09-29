"""Test report schemas."""

from datetime import date, datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TestReportCreate(BaseModel):
    """Schema for creating a test report."""

    athlete_id: UUID
    report_date: date = Field(default_factory=date.today)
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    sections: Dict[str, bool] = Field(default_factory=dict)
    notes: Dict[str, str] = Field(default_factory=dict)


class TestReportUpdate(BaseModel):
    """Schema for updating a test report (PATCH semantics)."""

    report_date: Optional[date] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    sections: Optional[Dict[str, bool]] = None
    notes: Optional[Dict[str, str]] = None


class TestReportResponse(BaseModel):
    """Full test report response."""

    id: UUID
    athlete_id: UUID
    coach_id: UUID
    report_date: date
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    sections: Dict[str, bool] = Field(default_factory=dict)
    notes: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestReportListItem(BaseModel):
    """Compact report item for list views."""

    id: UUID
    athlete_id: UUID
    report_date: date
    created_at: datetime

    model_config = {"from_attributes": True}
