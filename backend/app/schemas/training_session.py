"""Training session schemas."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ALLOWED_TRAINING_TYPES = [
    "Strength",
    "Boxing",
    "Conditioning",
    "Plyometric",
    "Recovery",
    "Sparring",
    "Pads",
    "Technical",
    "Other",
]


class TrainingSessionCreate(BaseModel):
    """Schema for creating a new training session."""

    athlete_id: UUID
    session_date: date
    training_type: str = Field(..., max_length=50)
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)
    rpe: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=1000)
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional JSONB metrics (e.g., jump readiness data)",
    )
    status: Optional[str] = Field(None, description="Session status: 'assigned' for coach-created sessions")

    @field_validator("training_type")
    @classmethod
    def validate_training_type(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("training_type cannot be empty")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "assigned":
            raise ValueError("status must be 'assigned' or null on creation")
        return v


class TrainingSessionUpdate(BaseModel):
    """Schema for updating a training session."""

    session_date: Optional[date] = None
    training_type: Optional[str] = Field(None, max_length=50)
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)
    rpe: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = Field(None, max_length=2000)
    notes: Optional[str] = Field(None, max_length=1000)
    metrics: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, description="Session status: 'completed' when athlete finishes assigned session")

    @field_validator("training_type")
    @classmethod
    def validate_training_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("training_type cannot be empty")
        return v.strip() if v is not None else v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "completed":
            raise ValueError("status must be 'completed' or null on update")
        return v


class BatchSessionAssign(BaseModel):
    """Batch-assign a template to multiple athletes."""
    template_id: UUID
    athlete_ids: List[UUID] = Field(..., min_length=1, max_length=50)
    session_date: date
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("athlete_ids")
    @classmethod
    def validate_no_duplicates(cls, v: List[UUID]) -> List[UUID]:
        if len(v) != len(set(v)):
            raise ValueError("athlete_ids must not contain duplicates")
        return v


class BatchSessionResponse(BaseModel):
    """Response from batch session assignment."""
    created_count: int
    sessions: List["TrainingSessionResponse"]


class TrainingSessionResponse(BaseModel):
    """Schema for training session responses."""

    id: UUID
    athlete_id: UUID
    session_date: date
    training_type: str
    duration_minutes: Optional[int] = None
    rpe: Optional[int] = None
    srpe: Optional[int] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Resolve forward reference in BatchSessionResponse
BatchSessionResponse.model_rebuild()
