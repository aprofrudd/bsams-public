"""Analysis API router for benchmarks and Z-score calculations."""

from datetime import date
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.access_control import verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.enums import Gender
from app.schemas.metric_registry import NON_METRIC_KEYS
from app.services.admin_pool import get_admin_athletes, get_opted_in_athletes
from app.services.stat_engine import StatEngine

router = APIRouter(prefix="/analysis", tags=["analysis"])
limiter = Limiter(key_func=get_remote_address)


class ReferenceGroup(str, Enum):
    """Reference group options for benchmark calculations."""

    COHORT = "cohort"  # Whole cohort
    GENDER = "gender"  # Gender-specific
    MASS_BAND = "mass_band"  # Mass band specific


class BenchmarkSource(str, Enum):
    """Source of benchmark data."""

    OWN = "own"  # Coach's own athletes
    BOXING_SCIENCE = "boxing_science"  # Admin users' data pool
    SHARED_POOL = "shared_pool"  # Opted-in coaches' pooled data (admin only)


class BenchmarkResponse(BaseModel):
    """Response for benchmark statistics."""

    mean: Optional[float] = None
    std_dev: Optional[float] = None
    mode: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    count: int = 0
    reference_group: str
    metric: str


class ZScoreResponse(BaseModel):
    """Response for Z-score calculation."""

    value: float
    z_score: float
    mean: float
    std_dev: float
    percentile_rank: Optional[float] = None
    reference_group: str
    metric: str


@router.get("/benchmarks", response_model=BenchmarkResponse)
@limiter.limit("60/minute")
def get_benchmarks(
    request: Request,
    metric: str = Query(..., description="Metric key to analyze (e.g., 'height_cm')"),
    reference_group: ReferenceGroup = Query(
        ReferenceGroup.COHORT, description="Reference group for comparison"
    ),
    gender: Optional[Gender] = Query(None, description="Gender filter (required if reference_group=gender)"),
    mass_band: Optional[str] = Query(None, description="Mass band filter (e.g., '70-74.9kg')"),
    benchmark_source: BenchmarkSource = Query(
        BenchmarkSource.OWN, description="Source of benchmark data (own or boxing_science)"
    ),
    start_date: Optional[date] = Query(None, description="Filter events from this date"),
    end_date: Optional[date] = Query(None, description="Filter events until this date"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get benchmark statistics for a metric within a reference group.

    The reference group determines how athletes are grouped for comparison:
    - cohort: All athletes belonging to the coach
    - gender: Only athletes of the specified gender
    - mass_band: Only athletes within the specified 5kg mass band
    """
    client = get_client_or_503()

    # Validate parameters
    if reference_group == ReferenceGroup.GENDER and not gender:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gender parameter required when reference_group=gender",
        )

    if reference_group == ReferenceGroup.MASS_BAND and not mass_band:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mass band parameter required when reference_group=mass_band",
        )

    # Guard: only admins can use boxing_science or shared_pool sources
    if benchmark_source in (BenchmarkSource.BOXING_SCIENCE, BenchmarkSource.SHARED_POOL):
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required for this benchmark source",
            )

    # Get reference athletes based on benchmark source
    if benchmark_source == BenchmarkSource.BOXING_SCIENCE:
        athletes_data = get_admin_athletes(client)
    elif benchmark_source == BenchmarkSource.SHARED_POOL:
        athletes_data = get_opted_in_athletes(client)
    elif current_user.role == "athlete":
        athletes_result = (
            client.table("athletes")
            .select("id, gender")
            .eq("user_id", str(current_user.id))
            .execute()
        )
        athletes_data = athletes_result.data if athletes_result.data else []
    else:
        athletes_result = (
            client.table("athletes")
            .select("id, gender")
            .eq("coach_id", str(current_user.id))
            .execute()
        )
        athletes_data = athletes_result.data if athletes_result.data else []

    if not athletes_data:
        return BenchmarkResponse(
            count=0,
            reference_group=reference_group.value,
            metric=metric,
        )

    # Filter athletes by reference group
    athlete_ids = []
    for athlete in athletes_data:
        if reference_group == ReferenceGroup.GENDER:
            if athlete["gender"] == gender.value:
                athlete_ids.append(athlete["id"])
        else:
            athlete_ids.append(athlete["id"])

    if not athlete_ids:
        return BenchmarkResponse(
            count=0,
            reference_group=reference_group.value,
            metric=metric,
        )

    # Get performance events for these athletes
    events_query = (
        client.table("performance_events")
        .select("metrics")
        .in_("athlete_id", athlete_ids)
    )
    if start_date:
        events_query = events_query.gte("event_date", start_date.isoformat())
    if end_date:
        events_query = events_query.lte("event_date", end_date.isoformat())
    events_result = events_query.execute()

    if not events_result.data:
        return BenchmarkResponse(
            count=0,
            reference_group=reference_group.value,
            metric=metric,
        )

    # Extract metric values
    values = []
    for event in events_result.data:
        metrics = event.get("metrics", {})

        # Filter by mass band if needed
        if reference_group == ReferenceGroup.MASS_BAND:
            body_mass = metrics.get("body_mass_kg")
            if body_mass is None:
                continue
            if StatEngine.get_mass_band(body_mass) != mass_band:
                continue

        # Extract the requested metric
        if metric in metrics:
            try:
                value = float(metrics[metric])
                values.append(value)
            except (TypeError, ValueError):
                continue

    if not values:
        return BenchmarkResponse(
            count=0,
            reference_group=reference_group.value,
            metric=metric,
        )

    # Calculate benchmarks
    benchmarks = StatEngine.calculate_benchmarks(values)

    return BenchmarkResponse(
        mean=benchmarks["mean"],
        std_dev=benchmarks["std_dev"],
        mode=benchmarks["mode"],
        ci_lower=benchmarks["ci_lower"],
        ci_upper=benchmarks["ci_upper"],
        count=benchmarks["count"],
        reference_group=reference_group.value,
        metric=metric,
    )


@router.get("/athlete/{athlete_id}/zscore", response_model=ZScoreResponse)
@limiter.limit("60/minute")
def get_athlete_zscore(
    request: Request,
    athlete_id: UUID,
    metric: str = Query(..., description="Metric key to analyze (e.g., 'height_cm')"),
    event_id: Optional[UUID] = Query(None, description="Specific event ID. If not provided, uses latest event."),
    reference_group: ReferenceGroup = Query(
        ReferenceGroup.COHORT, description="Reference group for comparison"
    ),
    benchmark_source: BenchmarkSource = Query(
        BenchmarkSource.OWN, description="Source of benchmark data (own or boxing_science)"
    ),
    start_date: Optional[date] = Query(None, description="Filter reference events from this date"),
    end_date: Optional[date] = Query(None, description="Filter reference events until this date"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Calculate the Z-score for an athlete's metric value.

    The Z-score indicates how many standard deviations the athlete's
    value is from the reference group mean.
    """
    client = get_client_or_503()

    # Verify athlete access and get their gender
    if current_user.role == "athlete":
        athlete_result = (
            client.table("athletes")
            .select("id, gender")
            .eq("id", str(athlete_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
    else:
        athlete_result = (
            client.table("athletes")
            .select("id, gender")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )

    if not athlete_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    athlete = athlete_result.data[0]
    athlete_gender = athlete["gender"]

    # Get the specific event or latest event
    if event_id:
        event_result = (
            client.table("performance_events")
            .select("metrics")
            .eq("id", str(event_id))
            .eq("athlete_id", str(athlete_id))
            .execute()
        )
    else:
        event_result = (
            client.table("performance_events")
            .select("metrics")
            .eq("athlete_id", str(athlete_id))
            .order("event_date", desc=True)
            .limit(1)
            .execute()
        )

    if not event_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No events found for athlete",
        )

    event_metrics = event_result.data[0]["metrics"]

    # Get the athlete's value for this metric
    if metric not in event_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{metric}' not found in event",
        )

    athlete_value = float(event_metrics[metric])

    # Get body mass for mass band filtering
    athlete_mass = event_metrics.get("body_mass_kg")

    # Determine reference group parameters
    gender_filter = None
    mass_band_filter = None

    if reference_group == ReferenceGroup.GENDER:
        gender_filter = Gender(athlete_gender)
    elif reference_group == ReferenceGroup.MASS_BAND:
        if athlete_mass is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Body mass required for mass band reference group",
            )
        mass_band_filter = StatEngine.get_mass_band(athlete_mass)

    # Guard: only admins can use boxing_science or shared_pool sources
    if benchmark_source in (BenchmarkSource.BOXING_SCIENCE, BenchmarkSource.SHARED_POOL):
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required for this benchmark source",
            )

    # Get benchmarks for the reference group
    if benchmark_source == BenchmarkSource.BOXING_SCIENCE:
        ref_athletes_data = get_admin_athletes(client)
    elif benchmark_source == BenchmarkSource.SHARED_POOL:
        ref_athletes_data = get_opted_in_athletes(client)
    elif current_user.role == "athlete":
        athletes_query = (
            client.table("athletes")
            .select("id")
            .eq("user_id", str(current_user.id))
        )
        if gender_filter:
            athletes_query = athletes_query.eq("gender", gender_filter.value)
        athletes_result = athletes_query.execute()
        ref_athletes_data = athletes_result.data if athletes_result.data else []
    else:
        athletes_query = (
            client.table("athletes")
            .select("id")
            .eq("coach_id", str(current_user.id))
        )
        if gender_filter:
            athletes_query = athletes_query.eq("gender", gender_filter.value)
        athletes_result = athletes_query.execute()
        ref_athletes_data = athletes_result.data if athletes_result.data else []

    # Apply gender filter for non-own sources
    if benchmark_source in (BenchmarkSource.BOXING_SCIENCE, BenchmarkSource.SHARED_POOL) and gender_filter:
        ref_athletes_data = [a for a in ref_athletes_data if a.get("gender") == gender_filter.value]

    if not ref_athletes_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No athletes in reference group",
        )

    athlete_ids = [a["id"] for a in ref_athletes_data]

    # Get all events for reference group
    ref_events_query = (
        client.table("performance_events")
        .select("metrics")
        .in_("athlete_id", athlete_ids)
    )
    if start_date:
        ref_events_query = ref_events_query.gte("event_date", start_date.isoformat())
    if end_date:
        ref_events_query = ref_events_query.lte("event_date", end_date.isoformat())
    events_result = ref_events_query.execute()

    # Extract values for the metric
    values = []
    for event in events_result.data:
        metrics = event.get("metrics", {})

        # Filter by mass band if needed
        if mass_band_filter:
            event_mass = metrics.get("body_mass_kg")
            if event_mass is None:
                continue
            if StatEngine.get_mass_band(event_mass) != mass_band_filter:
                continue

        if metric in metrics:
            try:
                values.append(float(metrics[metric]))
            except (TypeError, ValueError):
                continue

    if not values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data in reference group for this metric",
        )

    # Calculate statistics
    mean = StatEngine.calculate_mean(values)
    std_dev = StatEngine.calculate_std_dev(values)

    if mean is None or std_dev is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient data to calculate Z-score",
        )

    z_score = StatEngine.calculate_z_score(athlete_value, mean, std_dev)
    percentile = StatEngine.calculate_percentile_rank(athlete_value, values)

    ref_group_label = reference_group.value
    if mass_band_filter:
        ref_group_label = f"mass_band:{mass_band_filter}"
    elif gender_filter:
        ref_group_label = f"gender:{gender_filter.value}"

    return ZScoreResponse(
        value=round(athlete_value, 2),
        z_score=z_score,
        mean=mean,
        std_dev=std_dev,
        percentile_rank=percentile,
        reference_group=ref_group_label,
        metric=metric,
    )


@router.get("/athlete/{athlete_id}/zscores", response_model=Dict[str, ZScoreResponse])
@limiter.limit("60/minute")
def get_athlete_zscores_bulk(
    request: Request,
    athlete_id: UUID,
    metric: str = Query(..., description="Metric key to analyze (e.g., 'height_cm')"),
    reference_group: ReferenceGroup = Query(
        ReferenceGroup.COHORT, description="Reference group for comparison"
    ),
    benchmark_source: BenchmarkSource = Query(
        BenchmarkSource.OWN, description="Source of benchmark data (own or boxing_science)"
    ),
    start_date: Optional[date] = Query(None, description="Filter events from this date"),
    end_date: Optional[date] = Query(None, description="Filter events until this date"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Calculate Z-scores for all events of an athlete in a single request.

    Returns a dict mapping event_id -> ZScoreResponse.
    This replaces N individual /zscore calls with a single bulk request.
    """
    client = get_client_or_503()

    # Verify athlete access
    if current_user.role == "athlete":
        athlete_result = (
            client.table("athletes")
            .select("id, gender")
            .eq("id", str(athlete_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
    else:
        athlete_result = (
            client.table("athletes")
            .select("id, gender")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )

    if not athlete_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    athlete = athlete_result.data[0]
    athlete_gender = athlete["gender"]

    # Get all events for this athlete
    athlete_events_query = (
        client.table("performance_events")
        .select("id, metrics")
        .eq("athlete_id", str(athlete_id))
    )
    if start_date:
        athlete_events_query = athlete_events_query.gte("event_date", start_date.isoformat())
    if end_date:
        athlete_events_query = athlete_events_query.lte("event_date", end_date.isoformat())
    athlete_events = athlete_events_query.execute()

    if not athlete_events.data:
        return {}

    # Guard: only admins can use boxing_science or shared_pool sources
    if benchmark_source in (BenchmarkSource.BOXING_SCIENCE, BenchmarkSource.SHARED_POOL):
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required for this benchmark source",
            )

    # Build reference group
    gender_filter = None
    if reference_group == ReferenceGroup.GENDER:
        gender_filter = Gender(athlete_gender)

    if benchmark_source == BenchmarkSource.BOXING_SCIENCE:
        ref_athletes_data = get_admin_athletes(client)
        if gender_filter:
            ref_athletes_data = [a for a in ref_athletes_data if a.get("gender") == gender_filter.value]
    elif benchmark_source == BenchmarkSource.SHARED_POOL:
        ref_athletes_data = get_opted_in_athletes(client)
        if gender_filter:
            ref_athletes_data = [a for a in ref_athletes_data if a.get("gender") == gender_filter.value]
    elif current_user.role == "athlete":
        athletes_query = (
            client.table("athletes")
            .select("id")
            .eq("user_id", str(current_user.id))
        )
        if gender_filter:
            athletes_query = athletes_query.eq("gender", gender_filter.value)
        athletes_result = athletes_query.execute()
        ref_athletes_data = athletes_result.data if athletes_result.data else []
    else:
        athletes_query = (
            client.table("athletes")
            .select("id")
            .eq("coach_id", str(current_user.id))
        )
        if gender_filter:
            athletes_query = athletes_query.eq("gender", gender_filter.value)
        athletes_result = athletes_query.execute()
        ref_athletes_data = athletes_result.data if athletes_result.data else []

    if not ref_athletes_data:
        return {}

    ref_athlete_ids = [a["id"] for a in ref_athletes_data]

    # Get all reference events
    ref_events_query = (
        client.table("performance_events")
        .select("metrics")
        .in_("athlete_id", ref_athlete_ids)
    )
    if start_date:
        ref_events_query = ref_events_query.gte("event_date", start_date.isoformat())
    if end_date:
        ref_events_query = ref_events_query.lte("event_date", end_date.isoformat())
    ref_events = ref_events_query.execute()

    # Extract reference values for the metric
    ref_values = []
    for event in ref_events.data:
        metrics = event.get("metrics", {})

        if reference_group == ReferenceGroup.MASS_BAND:
            event_mass = metrics.get("body_mass_kg")
            if event_mass is None:
                continue

        if metric in metrics:
            try:
                ref_values.append(float(metrics[metric]))
            except (TypeError, ValueError):
                continue

    if not ref_values:
        return {}

    mean = StatEngine.calculate_mean(ref_values)
    std_dev = StatEngine.calculate_std_dev(ref_values)

    if mean is None or std_dev is None:
        return {}

    ref_group_label = reference_group.value
    if gender_filter:
        ref_group_label = f"gender:{gender_filter.value}"

    # Calculate Z-score for each event
    results: Dict[str, ZScoreResponse] = {}
    for event in athlete_events.data:
        event_metrics = event.get("metrics", {})
        if metric not in event_metrics:
            continue
        try:
            value = float(event_metrics[metric])
        except (TypeError, ValueError):
            continue

        # For mass band, check this event's mass band
        if reference_group == ReferenceGroup.MASS_BAND:
            event_mass = event_metrics.get("body_mass_kg")
            if event_mass is None:
                continue
            mass_band_filter = StatEngine.get_mass_band(event_mass)
            # Recalculate with mass band filtering
            mb_values = []
            for ref_event in ref_events.data:
                rm = ref_event.get("metrics", {})
                rm_mass = rm.get("body_mass_kg")
                if rm_mass is None:
                    continue
                if StatEngine.get_mass_band(rm_mass) != mass_band_filter:
                    continue
                if metric in rm:
                    try:
                        mb_values.append(float(rm[metric]))
                    except (TypeError, ValueError):
                        continue
            if not mb_values:
                continue
            mb_mean = StatEngine.calculate_mean(mb_values)
            mb_std = StatEngine.calculate_std_dev(mb_values)
            if mb_mean is None or mb_std is None:
                continue
            z = StatEngine.calculate_z_score(value, mb_mean, mb_std)
            mb_percentile = StatEngine.calculate_percentile_rank(value, mb_values)
            results[event["id"]] = ZScoreResponse(
                value=round(value, 2),
                z_score=z,
                mean=mb_mean,
                std_dev=mb_std,
                percentile_rank=mb_percentile,
                reference_group=f"mass_band:{mass_band_filter}",
                metric=metric,
            )
        else:
            z = StatEngine.calculate_z_score(value, mean, std_dev)
            percentile = StatEngine.calculate_percentile_rank(value, ref_values)
            results[event["id"]] = ZScoreResponse(
                value=round(value, 2),
                z_score=z,
                mean=mean,
                std_dev=std_dev,
                percentile_rank=percentile,
                reference_group=ref_group_label,
                metric=metric,
            )

    return results


@router.get("/athlete/{athlete_id}/metrics", response_model=List[str])
@limiter.limit("60/minute")
def get_athlete_metrics(
    request: Request,
    athlete_id: UUID,
    start_date: Optional[date] = Query(None, description="Filter events from this date"),
    end_date: Optional[date] = Query(None, description="Filter events until this date"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get available metric keys for an athlete.

    Returns a list of distinct metric keys from the athlete's events,
    excluding metadata fields like test_type and body_mass_kg.
    """
    client = get_client_or_503()

    # Verify athlete access
    if current_user.role == "athlete":
        athlete_result = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
    else:
        athlete_result = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )

    if not athlete_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    # Get all events for athlete
    events_query = (
        client.table("performance_events")
        .select("metrics")
        .eq("athlete_id", str(athlete_id))
    )
    if start_date:
        events_query = events_query.gte("event_date", start_date.isoformat())
    if end_date:
        events_query = events_query.lte("event_date", end_date.isoformat())
    events_result = events_query.execute()

    if not events_result.data:
        return []

    # Collect distinct metric keys
    metric_keys: set[str] = set()
    for event in events_result.data:
        metrics = event.get("metrics", {})
        for key in metrics:
            if key not in NON_METRIC_KEYS:
                metric_keys.add(key)

    return sorted(metric_keys)
