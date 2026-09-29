"""Programme form schemas."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProgrammeFormCreate(BaseModel):
    form_name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    num_weeks: int = Field(4, ge=1, le=16)
    sessions_per_week: int = Field(2, ge=1, le=7)
    form_data: dict = Field(default_factory=lambda: {"sessions": []})

    @field_validator("form_name")
    @classmethod
    def validate_form_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("form_name cannot be empty")
        return v.strip()


class ProgrammeFormUpdate(BaseModel):
    form_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    num_weeks: Optional[int] = Field(None, ge=1, le=16)
    sessions_per_week: Optional[int] = Field(None, ge=1, le=7)
    form_data: Optional[dict] = None


class ProgrammeFormResponse(BaseModel):
    id: UUID
    coach_id: UUID
    form_name: str
    description: Optional[str] = None
    num_weeks: int
    sessions_per_week: int
    form_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProgrammeFormApply(BaseModel):
    athlete_ids: List[str]
    start_date: date

    @field_validator("start_date")
    @classmethod
    def validate_start_date_monday(cls, v: date) -> date:
        if v.isoweekday() != 1:
            raise ValueError("start_date must be a Monday")
        return v

    @field_validator("athlete_ids")
    @classmethod
    def validate_athlete_ids(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("athlete_ids must not be empty")
        return v


class ProgrammeFormApplyResponse(BaseModel):
    created_count: int
    sessions_per_athlete: int
