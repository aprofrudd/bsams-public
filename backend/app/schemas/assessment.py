"""Movement assessment schemas for NASM-style movement screening.

Assessment types:
  - overhead_squat
  - single_leg_squat_left
  - single_leg_squat_right

Findings are stored as JSONB with structure:
  {
    "feet_ankles": {
      "turn_out": {"observed": true, "severity": "moderate", "side": "bilateral"},
      "heels_rise": {"observed": false}
    },
    "knees": {
      "valgus": {"observed": true, "severity": "mild", "side": "left"},
      "excessive_forward": {"observed": false}
    },
    "lphc": {
      "forward_lean": {"observed": true, "severity": "moderate"},
      "low_back_arch": {"observed": false},
      "hip_shift": {"observed": false}
    },
    "shoulders": {
      "arms_fall_forward": {"observed": true, "severity": "significant"}
    },
    "head": {
      "forward_protrusion": {"observed": false}
    }
  }

Severity levels: mild, moderate, significant
Side options: left, right, bilateral
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


VALID_ASSESSMENT_TYPES = [
    "overhead_squat",
    "single_leg_squat_left",
    "single_leg_squat_right",
]


class AssessmentPhotoResponse(BaseModel):
    """Schema for assessment photo responses."""

    id: UUID
    assessment_id: UUID
    view_type: str
    storage_path: str
    photo_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MovementAssessmentCreate(BaseModel):
    """Schema for creating a new movement assessment."""

    athlete_id: UUID
    assessment_date: date
    assessment_type: str = Field(
        ...,
        description="Assessment type: overhead_squat, single_leg_squat_left, single_leg_squat_right",
    )
    findings: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=2000)
    summary: Optional[str] = Field(None, max_length=2000)


class MovementAssessmentUpdate(BaseModel):
    """Schema for updating a movement assessment."""

    assessment_date: Optional[date] = None
    assessment_type: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None
    notes: Optional[str] = Field(None, max_length=2000)
    summary: Optional[str] = Field(None, max_length=2000)


class MovementAssessmentResponse(BaseModel):
    """Schema for movement assessment responses."""

    id: UUID
    athlete_id: UUID
    assessment_date: date
    assessment_type: str
    findings: Dict[str, Any]
    notes: Optional[str] = None
    summary: Optional[str] = None
    photos: List[AssessmentPhotoResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MovementAssessmentListItem(BaseModel):
    """Schema for assessment list items (without full photo details)."""

    id: UUID
    athlete_id: UUID
    assessment_date: date
    assessment_type: str
    findings: Dict[str, Any]
    notes: Optional[str] = None
    summary: Optional[str] = None
    photo_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
