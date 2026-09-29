"""Database-wide analysis router (admin-only)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.database_analysis import (
    AnalysisDomain,
    AnalysisRequest,
    AnalysisResponse,
    DomainInfo,
    DomainMetric,
    DomainMetricsResponse,
)
from app.schemas.metric_registry import METRIC_DEFINITIONS, NON_METRIC_KEYS
from app.services.analysis_engine import AnalysisEngine

router = APIRouter(prefix="/database-analysis", tags=["database-analysis"])
limiter = Limiter(key_func=get_remote_address)


def _require_admin(current_user: AuthenticatedUser) -> None:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


DOMAIN_LABELS = {
    "performance": "Performance Testing",
    "training": "Training",
    "wellness": "Wellness",
    "vbt": "Velocity Based Training",
    "lactate": "Lactate Testing",
    "air_bike": "Air Bike",
    "assessments": "Movement Assessments",
}

DOMAIN_METRICS = {
    "training": [
        DomainMetric(key="duration_minutes", label="Duration (min)", unit="min"),
        DomainMetric(key="rpe", label="RPE", unit=""),
        DomainMetric(key="srpe", label="sRPE", unit="AU"),
    ],
    "wellness": [
        DomainMetric(key="sleep_quality", label="Sleep Quality", unit="1-5"),
        DomainMetric(key="fatigue", label="Fatigue", unit="1-5"),
        DomainMetric(key="muscle_soreness", label="Muscle Soreness", unit="1-5"),
        DomainMetric(key="stress_level", label="Stress Level", unit="1-5"),
        DomainMetric(key="mood", label="Mood", unit="1-5"),
        DomainMetric(key="hooper_index", label="Hooper Index", unit=""),
    ],
    "vbt": [
        DomainMetric(key="load_kg", label="Load (kg)", unit="kg"),
        DomainMetric(key="mean_velocity", label="Mean Velocity (m/s)", unit="m/s"),
    ],
    "lactate": [
        DomainMetric(key="lt1_speed", label="LT1 Speed", unit=""),
        DomainMetric(key="lt1_hr", label="LT1 Heart Rate", unit="bpm"),
        DomainMetric(key="lt2_speed", label="LT2 Speed", unit=""),
        DomainMetric(key="lt2_hr", label="LT2 Heart Rate", unit="bpm"),
    ],
    "air_bike": [
        DomainMetric(key="peak_power_w", label="Peak Power (W)", unit="W"),
        DomainMetric(key="avg_power_w", label="Avg Power (W)", unit="W"),
    ],
    "assessments": [
        DomainMetric(key="dysfunction_prevalence", label="Dysfunction Prevalence", unit="%"),
    ],
}


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("30/minute")
async def analyze(
    request: Request,
    body: AnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AnalysisResponse:
    """Run aggregate analysis across the database. Admin only."""
    _require_admin(current_user)

    client = get_client_or_503()
    return AnalysisEngine.run_analysis(client, body)


@router.get("/domains")
@limiter.limit("60/minute")
async def list_domains(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[DomainInfo]:
    """Return available analysis domains with labels."""
    _require_admin(current_user)

    return [
        DomainInfo(key=d.value, label=DOMAIN_LABELS.get(d.value, d.value))
        for d in AnalysisDomain
    ]


@router.get("/domain/{domain}/metrics", response_model=DomainMetricsResponse)
@limiter.limit("60/minute")
async def get_domain_metrics(
    request: Request,
    domain: AnalysisDomain,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DomainMetricsResponse:
    """Return available metrics for a domain."""
    _require_admin(current_user)

    if domain == AnalysisDomain.PERFORMANCE:
        metrics = [
            DomainMetric(key=m.key, label=m.label, unit=m.unit)
            for m in METRIC_DEFINITIONS
            if m.domain == "testing" and m.key not in NON_METRIC_KEYS
        ]
    else:
        metrics = DOMAIN_METRICS.get(domain.value, [])

    return DomainMetricsResponse(domain=domain.value, metrics=metrics)
