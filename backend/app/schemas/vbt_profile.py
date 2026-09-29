"""VBT load-velocity profile schemas."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class VbtSetCreate(BaseModel):
    """Schema for creating a VBT set (one load-velocity data point)."""

    load_kg: float = Field(..., gt=0, le=1000)
    mean_velocity_ms: Optional[float] = Field(None, ge=0, le=5)
    peak_velocity_ms: Optional[float] = Field(None, ge=0, le=10)
    reps: Optional[int] = Field(None, ge=1, le=20)

    @model_validator(mode="after")
    def at_least_one_velocity(self):
        if self.mean_velocity_ms is None and self.peak_velocity_ms is None:
            raise ValueError("At least one velocity (mean or peak) is required")
        return self


class VbtSetResponse(BaseModel):
    """Schema for VBT set responses."""

    id: UUID
    profile_id: UUID
    set_number: int
    load_kg: float
    mean_velocity_ms: Optional[float] = None
    peak_velocity_ms: Optional[float] = None
    reps: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VbtAnalysis(BaseModel):
    """Calculated regression analysis for a VBT profile."""

    slope: float
    intercept: float
    r_squared: float
    estimated_1rm_kg: Optional[float] = None
    v0_ms: Optional[float] = None  # velocity at zero load
    mvt_used_ms: float


class VbtProfileCreate(BaseModel):
    """Schema for creating a VBT profile with nested sets."""

    exercise_name: str = Field(..., max_length=100)
    profile_date: date
    mvt_ms: Optional[float] = Field(None, gt=0, le=3)
    notes: Optional[str] = Field(None, max_length=1000)
    sets: List[VbtSetCreate] = Field(..., min_length=1)

    @field_validator("exercise_name")
    @classmethod
    def validate_exercise_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("exercise_name cannot be empty")
        return v.strip()


class VbtProfileUpdate(BaseModel):
    """Schema for updating a VBT profile."""

    exercise_name: Optional[str] = Field(None, max_length=100)
    profile_date: Optional[date] = None
    mvt_ms: Optional[float] = Field(None, gt=0, le=3)
    notes: Optional[str] = Field(None, max_length=1000)
    sets: Optional[List[VbtSetCreate]] = None


class VbtProfileResponse(BaseModel):
    """Schema for VBT profile responses with sets and analysis."""

    id: UUID
    athlete_id: UUID
    exercise_name: str
    profile_date: date
    mvt_ms: Optional[float] = None
    notes: Optional[str] = None
    sets: List[VbtSetResponse] = []
    analysis: Optional[VbtAnalysis] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VbtProfileListItem(BaseModel):
    """Compact profile item for list views (no sets, includes analysis summary)."""

    id: UUID
    athlete_id: UUID
    exercise_name: str
    profile_date: date
    mvt_ms: Optional[float] = None
    notes: Optional[str] = None
    set_count: int = 0
    analysis: Optional[VbtAnalysis] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VbtPredictionRequest(BaseModel):
    """Request for velocity threshold calculator."""

    velocity_ms: Optional[float] = Field(None, ge=0, le=5)
    percent_1rm: Optional[float] = Field(None, gt=0, le=100)

    @model_validator(mode="after")
    def exactly_one_input(self):
        has_vel = self.velocity_ms is not None
        has_pct = self.percent_1rm is not None
        if not has_vel and not has_pct:
            raise ValueError("Provide either velocity_ms or percent_1rm")
        if has_vel and has_pct:
            raise ValueError("Provide only one of velocity_ms or percent_1rm")
        return self


class VbtPredictionResponse(BaseModel):
    """Response for velocity threshold calculator."""

    predicted_load_kg: Optional[float] = None
    predicted_velocity_ms: Optional[float] = None
    percent_1rm: Optional[float] = None
