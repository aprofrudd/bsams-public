"""Training block schemas."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BlockExercise(BaseModel):
    """Schema for an exercise within a block session (JSONB)."""

    exercise_name: str = Field(..., max_length=100)
    exercise_category: Optional[str] = Field(None, max_length=50)
    order_index: int = Field(1, ge=1, le=50)
    sets: int = Field(1, ge=1, le=20)
    reps: Optional[int] = Field(None, ge=1, le=100)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    percent_1rm: Optional[float] = Field(None, gt=0, le=100)
    rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    duration_seconds: Optional[int] = Field(None, ge=0, le=3600)
    distance_meters: Optional[float] = Field(None, ge=0, le=50000)
    notes: Optional[str] = Field(None, max_length=500)
    intensity_type: Optional[str] = Field(None)
    intensity_value: Optional[float] = Field(None, ge=0, le=10000)
    intensity_min: Optional[float] = Field(None, ge=0, le=10000)
    intensity_max: Optional[float] = Field(None, ge=0, le=10000)
    rest_between_reps_seconds: Optional[int] = Field(None, ge=0, le=600)
    rep_intensity_values: Optional[List[float]] = Field(None)
    rep_durations: Optional[List[int]] = Field(None)
    rest_between_reps: Optional[List[int]] = Field(None)

    @field_validator("exercise_name")
    @classmethod
    def validate_exercise_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("exercise_name cannot be empty")
        return v.strip()

    @field_validator("intensity_type")
    @classmethod
    def validate_intensity_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("rpe", "speed_kmh", "power_watts"):
            raise ValueError("intensity_type must be one of: rpe, speed_kmh, power_watts")
        return v


class BlockSessionCreate(BaseModel):
    """Schema for creating a block session."""

    week_number: int = Field(..., ge=1, le=16)
    day_of_week: int = Field(..., ge=1, le=7)
    session_name: str = Field(..., max_length=100)
    training_type: str = Field(..., max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)
    exercises: List[BlockExercise] = []

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("session_name cannot be empty")
        return v.strip()

    @field_validator("training_type")
    @classmethod
    def validate_training_type(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("training_type cannot be empty")
        return v.strip()


class BlockSessionUpdate(BaseModel):
    """Schema for updating a block session."""

    week_number: Optional[int] = Field(None, ge=1, le=16)
    day_of_week: Optional[int] = Field(None, ge=1, le=7)
    session_name: Optional[str] = Field(None, max_length=100)
    training_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)
    exercises: Optional[List[BlockExercise]] = None


class BlockSessionResponse(BaseModel):
    """Schema for block session responses."""

    id: UUID
    block_id: UUID
    week_number: int
    day_of_week: int
    session_name: str
    training_type: str
    notes: Optional[str] = None
    exercises: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrainingBlockCreate(BaseModel):
    """Schema for creating a training block."""

    block_name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    num_weeks: int = Field(4, ge=1, le=16)
    category: str = Field("Strength", max_length=50)

    @field_validator("block_name")
    @classmethod
    def validate_block_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("block_name cannot be empty")
        return v.strip()


class TrainingBlockUpdate(BaseModel):
    """Schema for updating a training block."""

    block_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    num_weeks: Optional[int] = Field(None, ge=1, le=16)
    category: Optional[str] = Field(None, max_length=50)


class TrainingBlockResponse(BaseModel):
    """Schema for training block responses."""

    id: UUID
    coach_id: UUID
    block_name: str
    description: Optional[str] = None
    num_weeks: int
    category: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrainingBlockDetailResponse(TrainingBlockResponse):
    """Detailed training block response with sessions."""

    sessions: List[BlockSessionResponse] = []


class BlockApplyRequest(BaseModel):
    """Request to apply a block to athletes."""

    athlete_ids: List[UUID] = Field(..., min_length=1, max_length=50)
    start_date: date

    @field_validator("athlete_ids")
    @classmethod
    def validate_no_duplicates(cls, v: List[UUID]) -> List[UUID]:
        if len(v) != len(set(v)):
            raise ValueError("athlete_ids must not contain duplicates")
        return v

    @field_validator("start_date")
    @classmethod
    def validate_start_date_is_monday(cls, v: date) -> date:
        if v.weekday() != 0:
            raise ValueError("start_date must be a Monday")
        return v


class UnresolvedExercise(BaseModel):
    """An exercise where 1RM could not be resolved for an athlete."""

    athlete_id: UUID
    athlete_name: str
    exercise_name: str


class BlockApplyResponse(BaseModel):
    """Response from applying a block to athletes."""

    created_count: int
    sessions_per_athlete: int
    unresolved_exercises: List[UnresolvedExercise] = []
    application_id: UUID


class BlockPreviewRequest(BaseModel):
    """Request to preview block application weight resolution."""

    athlete_ids: List[UUID] = Field(..., min_length=1, max_length=50)

    @field_validator("athlete_ids")
    @classmethod
    def validate_no_duplicates(cls, v: List[UUID]) -> List[UUID]:
        if len(v) != len(set(v)):
            raise ValueError("athlete_ids must not contain duplicates")
        return v


class WeightResolution(BaseModel):
    """Weight resolution result for one athlete + exercise."""

    athlete_id: UUID
    athlete_name: str
    exercise_name: str
    percent_1rm: float
    max_1rm_kg: Optional[float] = None
    resolved_weight_kg: Optional[float] = None
    source: str  # 'vbt', 'manual', 'missing'


class BlockPreviewResponse(BaseModel):
    """Response from previewing block application."""

    resolutions: List[WeightResolution] = []
    total_sessions: int
    sessions_per_athlete: int


class AthleteMaxUpsert(BaseModel):
    """Schema for upserting an athlete max."""

    exercise_name: str = Field(..., max_length=100)
    max_kg: float = Field(..., gt=0, le=1000)
    source: str = Field("manual")

    @field_validator("exercise_name")
    @classmethod
    def validate_exercise_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("exercise_name cannot be empty")
        return v.strip()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in ("manual", "vbt"):
            raise ValueError("source must be 'manual' or 'vbt'")
        return v


class AthleteMaxResponse(BaseModel):
    """Schema for athlete max responses."""

    id: UUID
    athlete_id: UUID
    exercise_name: str
    max_kg: float
    source: str
    updated_at: datetime

    model_config = {"from_attributes": True}
