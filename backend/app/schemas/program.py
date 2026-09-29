"""Program marketplace schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProgramExercise(BaseModel):
    """Schema for an exercise within a program template (JSONB)."""
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


class ProgramTemplateCreate(BaseModel):
    """Schema for creating a program template."""
    template_name: str = Field(..., max_length=100)
    training_type: str = Field(..., max_length=50)
    order_index: int = Field(1, ge=1, le=100)
    notes: Optional[str] = Field(None, max_length=1000)
    exercises: List[ProgramExercise] = []

    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("template_name cannot be empty")
        return v.strip()


class ProgramTemplateUpdate(BaseModel):
    """Schema for updating a program template."""
    template_name: Optional[str] = Field(None, max_length=100)
    training_type: Optional[str] = Field(None, max_length=50)
    order_index: Optional[int] = Field(None, ge=1, le=100)
    notes: Optional[str] = Field(None, max_length=1000)
    exercises: Optional[List[ProgramExercise]] = None


class ProgramTemplateResponse(BaseModel):
    """Schema for program template responses."""
    id: UUID
    program_id: UUID
    template_name: str
    training_type: str
    order_index: int
    notes: Optional[str] = None
    exercises: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProgramPackageCreate(BaseModel):
    """Schema for creating a program package."""
    program_name: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: str = Field("General", max_length=50)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    is_published: bool = False

    @field_validator("program_name")
    @classmethod
    def validate_program_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("program_name cannot be empty")
        return v.strip()


class ProgramPackageUpdate(BaseModel):
    """Schema for updating a program package."""
    program_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=50)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    is_published: Optional[bool] = None


class ProgramPackageResponse(BaseModel):
    """Schema for program package responses."""
    id: UUID
    created_by: UUID
    program_name: str
    description: Optional[str] = None
    category: str
    cover_image_url: Optional[str] = None
    is_published: bool
    template_count: int = 0
    is_installed: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProgramPackageDetailResponse(ProgramPackageResponse):
    """Detailed program response with templates."""
    templates: List[ProgramTemplateResponse] = []


class InstalledTemplateResponse(BaseModel):
    """Program template formatted for TemplateSessionModal."""
    id: UUID
    program_id: UUID
    program_name: str
    template_name: str
    training_type: str
    order_index: int
    notes: Optional[str] = None
    exercises: List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}
