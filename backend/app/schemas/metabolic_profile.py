"""Metabolic profile schemas."""

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MetabolicProfileCreate(BaseModel):
    """Schema for creating a metabolic profile."""

    test_date: date
    body_mass_kg: float = Field(..., ge=30, le=250)
    data_source: str = Field(..., pattern="^(ble|manual)$")
    resting_lactate_mmol: float = Field(..., ge=0, le=30)
    la_peak_1_mmol: float = Field(..., ge=0, le=30)
    la_peak_2_mmol: float = Field(..., ge=0, le=30)
    la_peak_3_mmol: float = Field(..., ge=0, le=30)
    sprint_1_avg_power_w: Optional[float] = Field(None, ge=0, le=5000)
    sprint_2_avg_power_w: Optional[float] = Field(None, ge=0, le=5000)
    sprint_3_avg_power_w: Optional[float] = Field(None, ge=0, le=5000)
    trim_1_s: Optional[float] = Field(0, ge=0)
    trim_2_s: Optional[float] = Field(0, ge=0)
    trim_3_s: Optional[float] = Field(0, ge=0)
    sprint_1_samples: Optional[List[dict]] = None
    sprint_2_samples: Optional[List[dict]] = None
    sprint_3_samples: Optional[List[dict]] = None
    notes: Optional[str] = Field(None, max_length=2000)


class MetabolicProfileUpdate(BaseModel):
    """Schema for updating a metabolic profile (trims + notes only)."""

    trim_1_s: Optional[float] = Field(None, ge=0)
    trim_2_s: Optional[float] = Field(None, ge=0)
    trim_3_s: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class MetabolicProfileResponse(BaseModel):
    """Full metabolic profile response with computed results."""

    id: UUID
    athlete_id: UUID
    test_date: date
    body_mass_kg: float
    data_source: str
    resting_lactate_mmol: float
    la_peak_1_mmol: float
    la_peak_2_mmol: float
    la_peak_3_mmol: float
    sprint_1_avg_power_w: Optional[float] = None
    sprint_2_avg_power_w: Optional[float] = None
    sprint_3_avg_power_w: Optional[float] = None
    alactic_capacity_j: Optional[float] = None
    max_glycolytic_power_w: Optional[float] = None
    anaerobic_cost: Optional[float] = None
    fatigue_slope_w: Optional[float] = None
    mech_work_sprint_1_j: Optional[float] = None
    mech_work_sprint_2_j: Optional[float] = None
    mech_work_sprint_3_j: Optional[float] = None
    alactic_1_j: Optional[float] = None
    alactic_2_j: Optional[float] = None
    alactic_3_j: Optional[float] = None
    glycolytic_1_j: Optional[float] = None
    glycolytic_2_j: Optional[float] = None
    glycolytic_3_j: Optional[float] = None
    trim_1_s: Optional[float] = 0
    trim_2_s: Optional[float] = 0
    trim_3_s: Optional[float] = 0
    sprint_1_samples: Optional[Any] = None
    sprint_2_samples: Optional[Any] = None
    sprint_3_samples: Optional[Any] = None
    notes: Optional[str] = None
    insights: Optional[List[dict]] = None
    warnings: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetabolicProfileListItem(BaseModel):
    """Compact profile item for list views (no samples)."""

    id: UUID
    athlete_id: UUID
    test_date: date
    body_mass_kg: float
    data_source: str
    alactic_capacity_j: Optional[float] = None
    max_glycolytic_power_w: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
