"""Schemas for database-wide analysis (admin-only)."""

from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisDomain(str, Enum):
    PERFORMANCE = "performance"
    TRAINING = "training"
    WELLNESS = "wellness"
    VBT = "vbt"
    LACTATE = "lactate"
    AIR_BIKE = "air_bike"
    ASSESSMENTS = "assessments"


class AggregationMode(str, Enum):
    ALL_RECORDS = "all_records"
    MEAN_PER_ATHLETE = "mean_per_athlete"
    MEDIAN_PER_ATHLETE = "median_per_athlete"
    PEAK_PER_ATHLETE = "peak_per_athlete"


class DataSource(str, Enum):
    BOXING_SCIENCE = "boxing_science"
    SHARED_POOL = "shared_pool"


class AthleteFilter(BaseModel):
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    status: Optional[str] = Field(None, pattern="^(amateur|professional)$")
    age_min: Optional[int] = Field(None, ge=0, le=100)
    age_max: Optional[int] = Field(None, ge=0, le=100)
    mass_band: Optional[str] = None
    stature_min_cm: Optional[float] = Field(None, ge=0)
    stature_max_cm: Optional[float] = Field(None, ge=0)


class DateFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class PerformanceFilters(BaseModel):
    metric_keys: Optional[List[str]] = None


class TrainingFilters(BaseModel):
    training_type: Optional[str] = None


class WellnessFilters(BaseModel):
    pass


class VbtFilters(BaseModel):
    exercise_name: Optional[str] = None


class LactateFilters(BaseModel):
    test_type: Optional[str] = None


class AirBikeFilters(BaseModel):
    pass


class AssessmentFilters(BaseModel):
    assessment_type: Optional[str] = None


class AnalysisRequest(BaseModel):
    domain: AnalysisDomain
    data_source: DataSource = DataSource.BOXING_SCIENCE
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS
    athlete_filter: Optional[AthleteFilter] = None
    date_filter: Optional[DateFilter] = None
    performance_filters: Optional[PerformanceFilters] = None
    training_filters: Optional[TrainingFilters] = None
    wellness_filters: Optional[WellnessFilters] = None
    vbt_filters: Optional[VbtFilters] = None
    lactate_filters: Optional[LactateFilters] = None
    air_bike_filters: Optional[AirBikeFilters] = None
    assessment_filters: Optional[AssessmentFilters] = None


class DescriptiveStats(BaseModel):
    metric: str
    label: str
    count: int
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    median: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class DysfunctionPrevalence(BaseModel):
    region: str
    dysfunction: str
    count: int
    total_assessed: int
    prevalence_pct: float


class AnalysisResponse(BaseModel):
    domain: str
    athlete_count: int
    record_count: int
    aggregation_mode: str = "all_records"
    filters_applied: Dict[str, str] = {}
    statistics: List[DescriptiveStats] = []
    dysfunction_prevalence: List[DysfunctionPrevalence] = []
    distributions: Dict[str, List[float]] = {}


class DomainInfo(BaseModel):
    key: str
    label: str


class DomainMetric(BaseModel):
    key: str
    label: str
    unit: str = ""


class DomainMetricsResponse(BaseModel):
    domain: str
    metrics: List[DomainMetric]
