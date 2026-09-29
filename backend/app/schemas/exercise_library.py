"""Exercise library schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ExerciseLibraryCreate(BaseModel):
    """Schema for creating an exercise library entry."""

    exercise_name: str = Field(..., max_length=100)
    exercise_category: Optional[str] = Field(None, max_length=50)
    default_reps: Optional[int] = Field(None, ge=1, le=100)
    default_weight_kg: Optional[float] = Field(None, ge=0, le=500)
    default_tempo: Optional[str] = Field(None, max_length=20)
    default_rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    default_duration_seconds: Optional[int] = Field(None, ge=0, le=3600)
    default_distance_meters: Optional[float] = Field(None, ge=0, le=50000)
    notes: Optional[str] = Field(None, max_length=500)
    default_intensity_type: Optional[str] = Field(None)
    default_intensity_value: Optional[float] = Field(None, ge=0, le=10000)
    default_rest_between_reps_seconds: Optional[int] = Field(None, ge=0, le=600)
    default_rep_durations: Optional[List[int]] = Field(None)
    default_rest_between_reps: Optional[List[int]] = Field(None)
    default_rep_intensity_values: Optional[List[float]] = Field(None)
    default_set_configs: Optional[List[dict]] = Field(None)
    video_url: Optional[str] = Field(None, max_length=500)

    @field_validator("exercise_name")
    @classmethod
    def validate_exercise_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("exercise_name cannot be empty")
        return v.strip()

    @field_validator("default_intensity_type")
    @classmethod
    def validate_intensity_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("rpe", "speed_kmh", "power_watts"):
            raise ValueError("default_intensity_type must be one of: rpe, speed_kmh, power_watts")
        return v

    @field_validator("default_rep_durations")
    @classmethod
    def validate_default_rep_durations(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("default_rep_durations must be non-empty")
            for d in v:
                if not isinstance(d, int) or d < 1 or d > 3600:
                    raise ValueError("Each rep duration must be 1-3600")
        return v

    @field_validator("default_rest_between_reps")
    @classmethod
    def validate_default_rest_between_reps(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            for r in v:
                if not isinstance(r, int) or r < 0 or r > 600:
                    raise ValueError("Each default_rest_between_reps value must be 0-600")
        return v

    @field_validator("default_rep_intensity_values")
    @classmethod
    def validate_default_rep_intensity_values(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("default_rep_intensity_values must be non-empty")
            for val in v:
                if val < 0 or val > 10000:
                    raise ValueError("Each default_rep_intensity_values entry must be 0-10000")
        return v

    @field_validator("default_set_configs")
    @classmethod
    def validate_set_configs(cls, v: Optional[List[dict]]) -> Optional[List[dict]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("default_set_configs must be non-empty")
            if len(v) > 20:
                raise ValueError("default_set_configs max 20 entries")
            for entry in v:
                if not isinstance(entry, dict):
                    raise ValueError("Each set config must be a dict")
                has_reps = entry.get("reps") is not None
                has_weight = entry.get("weight_kg") is not None
                if not has_reps and not has_weight:
                    raise ValueError("Each set config must have at least reps or weight_kg")
                if has_reps:
                    reps = entry["reps"]
                    if not isinstance(reps, int) or reps < 1 or reps > 100:
                        raise ValueError("reps must be 1-100")
                if has_weight:
                    weight = entry["weight_kg"]
                    if not isinstance(weight, (int, float)) or weight < 0 or weight > 500:
                        raise ValueError("weight_kg must be 0-500")
        return v


class ExerciseLibraryUpdate(BaseModel):
    """Schema for updating an exercise library entry."""

    exercise_name: Optional[str] = Field(None, max_length=100)
    exercise_category: Optional[str] = Field(None, max_length=50)
    default_reps: Optional[int] = Field(None, ge=1, le=100)
    default_weight_kg: Optional[float] = Field(None, ge=0, le=500)
    default_tempo: Optional[str] = Field(None, max_length=20)
    default_rest_seconds: Optional[int] = Field(None, ge=0, le=600)
    default_duration_seconds: Optional[int] = Field(None, ge=0, le=3600)
    default_distance_meters: Optional[float] = Field(None, ge=0, le=50000)
    notes: Optional[str] = Field(None, max_length=500)
    default_intensity_type: Optional[str] = Field(None)
    default_intensity_value: Optional[float] = Field(None, ge=0, le=10000)
    default_rest_between_reps_seconds: Optional[int] = Field(None, ge=0, le=600)
    default_rep_durations: Optional[List[int]] = Field(None)
    default_rest_between_reps: Optional[List[int]] = Field(None)
    default_rep_intensity_values: Optional[List[float]] = Field(None)
    default_set_configs: Optional[List[dict]] = Field(None)
    video_url: Optional[str] = Field(None, max_length=500)

    @field_validator("default_intensity_type")
    @classmethod
    def validate_intensity_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("rpe", "speed_kmh", "power_watts"):
            raise ValueError("default_intensity_type must be one of: rpe, speed_kmh, power_watts")
        return v

    @field_validator("default_rep_durations")
    @classmethod
    def validate_default_rep_durations(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("default_rep_durations must be non-empty")
            for d in v:
                if not isinstance(d, int) or d < 1 or d > 3600:
                    raise ValueError("Each rep duration must be 1-3600")
        return v

    @field_validator("default_rest_between_reps")
    @classmethod
    def validate_default_rest_between_reps(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            for r in v:
                if not isinstance(r, int) or r < 0 or r > 600:
                    raise ValueError("Each default_rest_between_reps value must be 0-600")
        return v

    @field_validator("default_rep_intensity_values")
    @classmethod
    def validate_default_rep_intensity_values(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("default_rep_intensity_values must be non-empty")
            for val in v:
                if val < 0 or val > 10000:
                    raise ValueError("Each default_rep_intensity_values entry must be 0-10000")
        return v

    @field_validator("default_set_configs")
    @classmethod
    def validate_set_configs(cls, v: Optional[List[dict]]) -> Optional[List[dict]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("default_set_configs must be non-empty")
            if len(v) > 20:
                raise ValueError("default_set_configs max 20 entries")
            for entry in v:
                if not isinstance(entry, dict):
                    raise ValueError("Each set config must be a dict")
                has_reps = entry.get("reps") is not None
                has_weight = entry.get("weight_kg") is not None
                if not has_reps and not has_weight:
                    raise ValueError("Each set config must have at least reps or weight_kg")
                if has_reps:
                    reps = entry["reps"]
                    if not isinstance(reps, int) or reps < 1 or reps > 100:
                        raise ValueError("reps must be 1-100")
                if has_weight:
                    weight = entry["weight_kg"]
                    if not isinstance(weight, (int, float)) or weight < 0 or weight > 500:
                        raise ValueError("weight_kg must be 0-500")
        return v


class ExerciseLibraryResponse(BaseModel):
    """Schema for exercise library responses."""

    id: UUID
    coach_id: UUID
    exercise_name: str
    exercise_category: Optional[str] = None
    default_reps: Optional[int] = None
    default_weight_kg: Optional[float] = None
    default_tempo: Optional[str] = None
    default_rest_seconds: Optional[int] = None
    default_duration_seconds: Optional[int] = None
    default_distance_meters: Optional[float] = None
    notes: Optional[str] = None
    default_intensity_type: Optional[str] = None
    default_intensity_value: Optional[float] = None
    default_rest_between_reps_seconds: Optional[int] = None
    default_rep_durations: Optional[List[int]] = None
    default_rest_between_reps: Optional[List[int]] = None
    default_rep_intensity_values: Optional[List[float]] = None
    default_set_configs: Optional[List[dict]] = None
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
