"""Wellness entry schemas using the Validated Hooper Index (Hooper et al., 1995).

Four subjective measures on a 1-7 scale:
  - sleep (1=very very good, 7=very very bad)
  - fatigue (1=very very low, 7=very very high)
  - stress (1=very very low, 7=very very high)
  - doms (1=very very low, 7=very very high)

Hooper Index = sleep + fatigue + stress + doms (range 4-28, lower is better).
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WellnessEntryCreate(BaseModel):
    """Schema for creating a new wellness entry."""

    athlete_id: UUID
    entry_date: date
    sleep: int = Field(..., ge=1, le=7)
    fatigue: int = Field(..., ge=1, le=7)
    stress: int = Field(..., ge=1, le=7)
    doms: int = Field(..., ge=1, le=7)
    notes: Optional[str] = Field(None, max_length=1000)


class WellnessEntryUpdate(BaseModel):
    """Schema for updating a wellness entry."""

    entry_date: Optional[date] = None
    sleep: Optional[int] = Field(None, ge=1, le=7)
    fatigue: Optional[int] = Field(None, ge=1, le=7)
    stress: Optional[int] = Field(None, ge=1, le=7)
    doms: Optional[int] = Field(None, ge=1, le=7)
    notes: Optional[str] = Field(None, max_length=1000)


class WellnessEntryResponse(BaseModel):
    """Schema for wellness entry responses."""

    id: UUID
    athlete_id: UUID
    entry_date: date
    sleep: int
    fatigue: int
    stress: int
    doms: int
    hooper_index: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
