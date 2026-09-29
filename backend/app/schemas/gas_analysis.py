"""Gas analysis (CPET) schemas."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GasAnalysisUploadConfig(BaseModel):
    """Protocol configuration for gas analysis upload."""

    stage_duration_seconds: int = Field(180, ge=60, le=600)
    rest_duration_seconds: int = Field(60, ge=0, le=300)
    rest_start_seconds: int = Field(60, ge=0, le=300)
    averaging_method: Literal["last_60s", "full_stage"] = "last_60s"


class GasAnalysisSample(BaseModel):
    """A single time-series data point from the gas analyzer."""

    elapsed_s: float
    vo2_l_min: Optional[float] = None
    vo2_ml_kg_min: Optional[float] = None
    vco2_l_min: Optional[float] = None
    rer: Optional[float] = None
    ve_l_min: Optional[float] = None
    bf_per_min: Optional[float] = None
    vt_l: Optional[float] = None
    hr_bpm: Optional[int] = None
    fat_gh: Optional[float] = None
    cho_gh: Optional[float] = None
    ee_kcal_h: Optional[float] = None
    cho_ee_kcal_h: Optional[float] = None
    fat_ee_kcal_h: Optional[float] = None
    work_rate_w: Optional[float] = None


class GasAnalysisStageSummary(BaseModel):
    """Per-stage averaged gas metrics."""

    stage_number: int
    intensity_value: Optional[float] = None
    avg_vo2_l_min: Optional[float] = None
    avg_vo2_ml_kg_min: Optional[float] = None
    avg_vco2_l_min: Optional[float] = None
    avg_rer: Optional[float] = None
    avg_ve_l_min: Optional[float] = None
    avg_bf_per_min: Optional[float] = None
    avg_vt_l: Optional[float] = None
    avg_hr_bpm: Optional[float] = None
    avg_fat_gh: Optional[float] = None
    avg_cho_gh: Optional[float] = None
    avg_ee_kcal_h: Optional[float] = None
    avg_cho_ee_kcal_h: Optional[float] = None
    avg_fat_ee_kcal_h: Optional[float] = None
    data_point_count: int = 0


class FatMaxResult(BaseModel):
    """Max fat oxidation result."""

    max_fat_oxidation_gh: float
    fat_max_stage_number: int
    fat_max_intensity: Optional[float] = None
    fat_max_hr: Optional[float] = None


class ThresholdGasMetrics(BaseModel):
    """Interpolated gas values at a threshold intensity."""

    intensity: float
    vo2_ml_kg_min: Optional[float] = None
    vo2_l_min: Optional[float] = None
    rer: Optional[float] = None
    ve_l_min: Optional[float] = None
    bf_per_min: Optional[float] = None
    hr_bpm: Optional[float] = None
    fat_gh: Optional[float] = None
    cho_gh: Optional[float] = None
    ee_kcal_h: Optional[float] = None
    cho_ee_kcal_h: Optional[float] = None
    fat_ee_kcal_h: Optional[float] = None


class GasAnalysisPreviewResponse(BaseModel):
    """Preview response before saving."""

    interval_seconds: int
    stage_count: int
    sample_count: int
    columns_detected: List[str]
    column_mapping: Dict[str, str]
    stage_averages: List[GasAnalysisStageSummary]
    fat_max: Optional[FatMaxResult] = None


class GasSummary(BaseModel):
    """Compact gas analysis summary for list views."""

    max_fat_oxidation_gh: Optional[float] = None
    fat_max_intensity: Optional[float] = None


class GasAnalysisResponse(BaseModel):
    """Full gas analysis response."""

    id: UUID
    test_id: UUID
    interval_seconds: int
    rest_start_seconds: Optional[int] = None
    stage_duration_seconds: Optional[int] = None
    rest_duration_seconds: Optional[int] = None
    averaging_method: Optional[str] = None
    samples: List[Dict[str, Any]]
    stage_averages: List[GasAnalysisStageSummary]
    column_mapping: Optional[Dict[str, str]] = None
    max_fat_oxidation_gh: Optional[float] = None
    fat_max_stage_number: Optional[int] = None
    fat_max_intensity: Optional[float] = None
    fat_max_hr: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
