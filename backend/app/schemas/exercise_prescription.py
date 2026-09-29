"""Exercise prescription schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class ExercisePrescriptionCreate(BaseModel):
    """Schema for creating a new exercise prescription."""

    exercise_name: str = Field(..., max_length=100)
    exercise_category: Optional[str] = Field(None, max_length=50)
    set_number: int = Field(..., ge=1, le=20)
    reps: Optional[int] = Field(None, ge=1, le=100)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    tempo: Optional[str] = Field(None, max_length=20)
    rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    duration_seconds: Optional[int] = Field(None, ge=0, le=3600)
    distance_meters: Optional[float] = Field(None, ge=0, le=50000)
    notes: Optional[str] = Field(None, max_length=500)
    intensity_type: Optional[str] = Field(None)
    intensity_value: Optional[float] = Field(None, ge=0, le=10000)
    intensity_min: Optional[float] = Field(None, ge=0, le=10000)
    intensity_max: Optional[float] = Field(None, ge=0, le=10000)
    rest_between_reps_seconds: Optional[int] = Field(None, ge=0, le=600)
    rep_durations: Optional[List[int]] = Field(None)
    rest_between_reps: Optional[List[int]] = Field(None)
    rep_intensity_values: Optional[List[float]] = Field(None)
    section_type: Optional[str] = None
    reps_text: Optional[str] = Field(None, max_length=100)
    recommended_weight_kg: Optional[float] = Field(None, ge=0, le=1000)

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

    @field_validator("rep_durations")
    @classmethod
    def validate_rep_durations(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("rep_durations must be non-empty")
            for d in v:
                if not isinstance(d, int) or d < 1 or d > 3600:
                    raise ValueError("Each rep duration must be 1-3600")
        return v

    @field_validator("rest_between_reps")
    @classmethod
    def validate_rest_between_reps(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            for r in v:
                if not isinstance(r, int) or r < 0 or r > 600:
                    raise ValueError("Each rest_between_reps value must be 0-600")
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

    @model_validator(mode="after")
    def validate_array_lengths(self):
        if self.rep_durations is not None and self.reps is not None:
            if len(self.rep_durations) != self.reps:
                raise ValueError(
                    f"rep_durations length ({len(self.rep_durations)}) must match reps ({self.reps})"
                )
        if self.rest_between_reps is not None and self.reps is not None:
            if len(self.rest_between_reps) != self.reps - 1:
                raise ValueError(
                    f"rest_between_reps length ({len(self.rest_between_reps)}) must be reps - 1 ({self.reps - 1})"
                )
        if self.rep_intensity_values is not None and self.reps is not None:
            if len(self.rep_intensity_values) != self.reps:
                raise ValueError(
                    f"rep_intensity_values length ({len(self.rep_intensity_values)}) must match reps ({self.reps})"
                )
        return self


class ExercisePrescriptionUpdate(BaseModel):
    """Schema for updating an exercise prescription."""

    exercise_name: Optional[str] = Field(None, max_length=100)
    exercise_category: Optional[str] = Field(None, max_length=50)
    set_number: Optional[int] = Field(None, ge=1, le=20)
    reps: Optional[int] = Field(None, ge=1, le=100)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    tempo: Optional[str] = Field(None, max_length=20)
    rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    duration_seconds: Optional[int] = Field(None, ge=0, le=3600)
    distance_meters: Optional[float] = Field(None, ge=0, le=50000)
    notes: Optional[str] = Field(None, max_length=500)
    intensity_type: Optional[str] = Field(None)
    intensity_value: Optional[float] = Field(None, ge=0, le=10000)
    intensity_min: Optional[float] = Field(None, ge=0, le=10000)
    intensity_max: Optional[float] = Field(None, ge=0, le=10000)
    rest_between_reps_seconds: Optional[int] = Field(None, ge=0, le=600)
    rep_durations: Optional[List[int]] = Field(None)
    rest_between_reps: Optional[List[int]] = Field(None)
    rep_intensity_values: Optional[List[float]] = Field(None)
    section_type: Optional[str] = None
    reps_text: Optional[str] = Field(None, max_length=100)
    recommended_weight_kg: Optional[float] = Field(None, ge=0, le=1000)

    @field_validator("intensity_type")
    @classmethod
    def validate_intensity_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("rpe", "speed_kmh", "power_watts"):
            raise ValueError("intensity_type must be one of: rpe, speed_kmh, power_watts")
        return v

    @field_validator("rep_durations")
    @classmethod
    def validate_rep_durations(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("rep_durations must be non-empty")
            for d in v:
                if not isinstance(d, int) or d < 1 or d > 3600:
                    raise ValueError("Each rep duration must be 1-3600")
        return v

    @field_validator("rest_between_reps")
    @classmethod
    def validate_rest_between_reps(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            for r in v:
                if not isinstance(r, int) or r < 0 or r > 600:
                    raise ValueError("Each rest_between_reps value must be 0-600")
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

    @model_validator(mode="after")
    def validate_array_lengths(self):
        if self.rep_durations is not None and self.reps is not None:
            if len(self.rep_durations) != self.reps:
                raise ValueError(
                    f"rep_durations length ({len(self.rep_durations)}) must match reps ({self.reps})"
                )
        if self.rest_between_reps is not None and self.reps is not None:
            if len(self.rest_between_reps) != self.reps - 1:
                raise ValueError(
                    f"rest_between_reps length ({len(self.rest_between_reps)}) must be reps - 1 ({self.reps - 1})"
                )
        if self.rep_intensity_values is not None and self.reps is not None:
            if len(self.rep_intensity_values) != self.reps:
                raise ValueError(
                    f"rep_intensity_values length ({len(self.rep_intensity_values)}) must match reps ({self.reps})"
                )
        return self


class ExercisePrescriptionResponse(BaseModel):
    """Schema for exercise prescription responses."""

    id: UUID
    session_id: UUID
    exercise_name: str
    exercise_category: Optional[str] = None
    set_number: int
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    tempo: Optional[str] = None
    rest_seconds: Optional[int] = None
    duration_seconds: Optional[int] = None
    distance_meters: Optional[float] = None
    notes: Optional[str] = None
    intensity_type: Optional[str] = None
    intensity_value: Optional[float] = None
    intensity_min: Optional[float] = None
    intensity_max: Optional[float] = None
    rest_between_reps_seconds: Optional[int] = None
    rep_durations: Optional[List[int]] = None
    rest_between_reps: Optional[List[int]] = None
    rep_intensity_values: Optional[List[float]] = None
    section_type: Optional[str] = None
    reps_text: Optional[str] = None
    recommended_weight_kg: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
