"""Session template schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TemplateExerciseCreate(BaseModel):
    """Schema for creating a template exercise."""

    exercise_library_id: Optional[str] = None
    exercise_name: str = Field(..., max_length=100)
    exercise_category: Optional[str] = Field(None, max_length=50)
    order_index: int = Field(1, ge=1, le=50)
    sets: int = Field(1, ge=1, le=20)
    reps: Optional[int] = Field(None, ge=1, le=100)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    tempo: Optional[str] = Field(None, max_length=20)
    rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    duration_seconds: Optional[int] = Field(None, ge=0, le=3600)
    distance_meters: Optional[float] = Field(None, ge=0, le=50000)
    notes: Optional[str] = Field(None, max_length=500)
    intensity_type: Optional[str] = Field(None)
    intensity_value: Optional[float] = Field(None, ge=0, le=10000)
    rest_between_reps_seconds: Optional[int] = Field(None, ge=0, le=600)
    rest_between_reps: Optional[List[int]] = Field(None)
    rep_intensity_values: Optional[List[float]] = Field(None)

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

    @field_validator("rep_intensity_values")
    @classmethod
    def validate_rep_intensity_values(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("rep_intensity_values must be non-empty")
            for val in v:
                if val < 0 or val > 10000:
                    raise ValueError("Each rep_intensity_values entry must be 0-10000")
        return v


class TemplateExerciseResponse(BaseModel):
    """Schema for template exercise responses."""

    id: UUID
    template_id: UUID
    exercise_library_id: Optional[UUID] = None
    exercise_name: str
    exercise_category: Optional[str] = None
    order_index: int
    sets: int
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    tempo: Optional[str] = None
    rest_seconds: Optional[int] = None
    duration_seconds: Optional[int] = None
    distance_meters: Optional[float] = None
    notes: Optional[str] = None
    intensity_type: Optional[str] = None
    intensity_value: Optional[float] = None
    rest_between_reps_seconds: Optional[int] = None
    rest_between_reps: Optional[List[int]] = None
    rep_intensity_values: Optional[List[float]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionTemplateCreate(BaseModel):
    """Schema for creating a session template."""

    template_name: str = Field(..., max_length=100)
    training_type: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=1000)
    template_category: Optional[str] = Field(None, max_length=50)
    tier: Optional[str] = Field(None, max_length=20)
    exercises: List[TemplateExerciseCreate] = []

    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("template_name cannot be empty")
        return v.strip()

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("foundation", "intermediate", "advanced"):
            raise ValueError("tier must be one of: foundation, intermediate, advanced")
        return v


class SessionTemplateUpdate(BaseModel):
    """Schema for updating a session template."""

    template_name: Optional[str] = Field(None, max_length=100)
    training_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=1000)
    template_category: Optional[str] = Field(None, max_length=50)
    tier: Optional[str] = Field(None, max_length=20)
    exercises: Optional[List[TemplateExerciseCreate]] = None


class SessionTemplateResponse(BaseModel):
    """Schema for session template responses."""

    id: UUID
    coach_id: UUID
    template_name: str
    training_type: str
    description: Optional[str] = None
    notes: Optional[str] = None
    template_category: Optional[str] = None
    tier: Optional[str] = None
    exercises: List[TemplateExerciseResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
