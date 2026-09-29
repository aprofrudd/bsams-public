"""Lactate test schemas."""

from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class LactateStageCreate(BaseModel):
    """Schema for creating a lactate stage (one data point)."""

    intensity_value: float = Field(..., gt=0, le=2000)
    heart_rate_bpm: Optional[int] = Field(None, ge=30, le=250)
    blood_lactate_mmol: float = Field(..., ge=0, le=30)
    rpe: Optional[float] = Field(None, ge=1, le=10)


class LactateStageResponse(BaseModel):
    """Schema for lactate stage responses."""

    id: UUID
    test_id: UUID
    stage_number: int
    intensity_value: float
    heart_rate_bpm: Optional[int] = None
    blood_lactate_mmol: float
    rpe: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PiecewiseSegment(BaseModel):
    """A single segment of the piecewise regression."""

    start_x: float
    end_x: float
    slope: float
    intercept: float


class LactateAnalysis(BaseModel):
    """Calculated breakpoint analysis for a lactate test."""

    suggested_lt1_value: Optional[float] = None
    suggested_lt1_lactate: Optional[float] = None
    suggested_lt2_value: Optional[float] = None
    suggested_lt2_lactate: Optional[float] = None
    segments: Optional[List[PiecewiseSegment]] = None
    total_sse: Optional[float] = None
    r_squared: Optional[float] = None


class LactateTestCreate(BaseModel):
    """Schema for creating a lactate test with nested stages."""

    test_date: date
    test_type: Literal["running", "cycling"]
    lt1_value: Optional[float] = Field(None, ge=0, le=2000)
    lt1_lactate: Optional[float] = Field(None, ge=0, le=30)
    lt1_hr: Optional[int] = Field(None, ge=30, le=250)
    lt2_value: Optional[float] = Field(None, ge=0, le=2000)
    lt2_lactate: Optional[float] = Field(None, ge=0, le=30)
    lt2_hr: Optional[int] = Field(None, ge=30, le=250)
    notes: Optional[str] = Field(None, max_length=2000)
    stages: List[LactateStageCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def lt2_gte_lt1(self):
        if (
            self.lt1_value is not None
            and self.lt2_value is not None
            and self.lt2_value < self.lt1_value
        ):
            raise ValueError("LT2 value must be greater than or equal to LT1 value")
        return self


class LactateTestUpdate(BaseModel):
    """Schema for updating a lactate test."""

    test_date: Optional[date] = None
    test_type: Optional[Literal["running", "cycling"]] = None
    lt1_value: Optional[float] = Field(None, ge=0, le=2000)
    lt1_lactate: Optional[float] = Field(None, ge=0, le=30)
    lt1_hr: Optional[int] = Field(None, ge=30, le=250)
    lt2_value: Optional[float] = Field(None, ge=0, le=2000)
    lt2_lactate: Optional[float] = Field(None, ge=0, le=30)
    lt2_hr: Optional[int] = Field(None, ge=30, le=250)
    notes: Optional[str] = Field(None, max_length=2000)
    stages: Optional[List[LactateStageCreate]] = None


class GasSummary(BaseModel):
    """Compact gas analysis summary."""

    max_fat_oxidation_gh: Optional[float] = None
    fat_max_intensity: Optional[float] = None


class LactateTestResponse(BaseModel):
    """Schema for lactate test responses with stages and analysis."""

    id: UUID
    athlete_id: UUID
    test_date: date
    test_type: str
    lt1_value: Optional[float] = None
    lt1_lactate: Optional[float] = None
    lt1_hr: Optional[int] = None
    lt2_value: Optional[float] = None
    lt2_lactate: Optional[float] = None
    lt2_hr: Optional[int] = None
    notes: Optional[str] = None
    stages: List[LactateStageResponse] = []
    analysis: Optional[LactateAnalysis] = None
    has_gas_analysis: bool = False
    gas_summary: Optional[GasSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LactateTestListItem(BaseModel):
    """Compact test item for list views (no stages, includes analysis summary)."""

    id: UUID
    athlete_id: UUID
    test_date: date
    test_type: str
    lt1_value: Optional[float] = None
    lt1_lactate: Optional[float] = None
    lt1_hr: Optional[int] = None
    lt2_value: Optional[float] = None
    lt2_lactate: Optional[float] = None
    lt2_hr: Optional[int] = None
    notes: Optional[str] = None
    stage_count: int = 0
    analysis: Optional[LactateAnalysis] = None
    has_gas_analysis: bool = False
    gas_summary: Optional[GasSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LactateAutoDetectResponse(BaseModel):
    """Response for auto-detect breakpoint endpoint."""

    analysis: Optional[LactateAnalysis] = None
