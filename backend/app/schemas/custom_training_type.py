"""Custom training type schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CustomTrainingTypeCreate(BaseModel):
    """Schema for creating a custom training type."""

    type_name: str = Field(..., min_length=1, max_length=50)

    @field_validator("type_name")
    @classmethod
    def validate_type_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("type_name cannot be empty")
        return v


class CustomTrainingTypeResponse(BaseModel):
    """Schema for training type responses."""

    id: UUID
    coach_id: UUID
    type_name: str
    display_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingTypeItem(BaseModel):
    """Schema for a training type in the list (system or custom)."""

    type_name: str
    is_system: bool = False
    id: Optional[UUID] = None
