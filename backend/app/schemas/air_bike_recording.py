"""Air bike BLE recording schemas."""

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AirBikeRecordingCreate(BaseModel):
    """Schema for creating an air bike BLE recording."""

    test_date: date
    duration_s: int = Field(..., ge=1, le=3600)
    samples: List[dict] = Field(..., min_length=1)
    notes: Optional[str] = Field(None, max_length=2000)


class AirBikeRecordingResponse(BaseModel):
    """Full air bike recording response with computed summary stats."""

    id: UUID
    athlete_id: UUID
    test_date: date
    duration_s: int
    avg_power_w: Optional[float] = None
    peak_power_w: Optional[float] = None
    total_work_j: Optional[float] = None
    avg_cadence_rpm: Optional[float] = None
    peak_cadence_rpm: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    total_distance_m: Optional[float] = None
    total_calories_kcal: Optional[float] = None
    samples: Optional[Any] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AirBikeRecordingListItem(BaseModel):
    """Compact recording item for list views (no samples)."""

    id: UUID
    athlete_id: UUID
    test_date: date
    duration_s: int
    avg_power_w: Optional[float] = None
    peak_power_w: Optional[float] = None
    total_work_j: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
