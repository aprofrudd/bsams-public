"""Database-wide analysis engine (admin-only).

Three-layer architecture:
  Router → AnalysisEngine → StatEngine

The _fetch_{domain}_data() methods return raw value arrays so a future
MLEngine can call the same methods for training data without duplicating
query logic.
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.schemas.database_analysis import (
    AggregationMode,
    AirBikeFilters,
    AnalysisDomain,
    AnalysisRequest,
    AnalysisResponse,
    AssessmentFilters,
    AthleteFilter,
    DataSource,
    DateFilter,
    DescriptiveStats,
    DysfunctionPrevalence,
    LactateFilters,
    PerformanceFilters,
    TrainingFilters,
    VbtFilters,
    WellnessFilters,
)
from app.schemas.metric_registry import METRIC_BY_KEY, METRIC_DEFINITIONS, NON_METRIC_KEYS
from app.services.admin_pool import get_admin_athletes, get_opted_in_athletes
from app.services.stat_engine import StatEngine

logger = logging.getLogger("bsams.analysis_engine")

CHUNK_SIZE = 200


def _chunked_in_query(
    client: Any,
    table: str,
    select: str,
    id_column: str,
    ids: List[str],
    extra_filters: Optional[Dict[str, Any]] = None,
    date_column: Optional[str] = None,
    date_filter: Optional[DateFilter] = None,
) -> List[dict]:
    """Query a table with IN filter, chunking IDs to avoid Supabase limits."""
    results: List[dict] = []
    for i in range(0, len(ids), CHUNK_SIZE):
        chunk = ids[i : i + CHUNK_SIZE]
        query = client.table(table).select(select).in_(id_column, chunk)

        if extra_filters:
            for col, val in extra_filters.items():
                query = query.eq(col, val)

        if date_filter and date_column:
            if date_filter.start_date:
                query = query.gte(date_column, date_filter.start_date.isoformat())
            if date_filter.end_date:
                query = query.lte(date_column, date_filter.end_date.isoformat())

        resp = query.execute()
        if resp.data:
            results.extend(resp.data)

    return results


class AnalysisEngine:
    """Fetches cross-database data and computes aggregate statistics."""

    @staticmethod
    def filter_athletes(
        client: Any,
        data_source: DataSource,
        athlete_filter: Optional[AthleteFilter],
    ) -> List[str]:
        """Return athlete IDs from the selected pool, applying demographic filters."""
        if data_source == DataSource.BOXING_SCIENCE:
            pool = get_admin_athletes(client)
        else:
            pool = get_opted_in_athletes(client)

        if not pool:
            return []

        athlete_ids = [a["id"] for a in pool]
        if not athlete_ids:
            return []

        # Fetch full athlete records for filtering
        full_athletes = _chunked_in_query(
            client, "athletes",
            "id, gender, date_of_birth, body_mass_kg, stature_cm, status",
            "id", athlete_ids,
        )

        if athlete_filter:
            full_athletes = _apply_athlete_filters(full_athletes, athlete_filter)

        return [a["id"] for a in full_athletes]

    @staticmethod
    def run_analysis(client: Any, request: AnalysisRequest) -> AnalysisResponse:
        """Orchestrate: filter athletes → fetch domain data → compute stats."""
        athlete_ids = AnalysisEngine.filter_athletes(
            client, request.data_source, request.athlete_filter,
        )

        filters_applied = _build_filters_applied(request)

        if not athlete_ids:
            return AnalysisResponse(
                domain=request.domain.value,
                athlete_count=0,
                record_count=0,
                filters_applied=filters_applied,
            )

        domain = request.domain
        date_filter = request.date_filter
        agg_mode = request.aggregation_mode

        if domain == AnalysisDomain.PERFORMANCE:
            return _analyze_performance(
                client, athlete_ids, date_filter,
                request.performance_filters, filters_applied, agg_mode,
            )
        elif domain == AnalysisDomain.TRAINING:
            return _analyze_training(
                client, athlete_ids, date_filter,
                request.training_filters, filters_applied, agg_mode,
            )
        elif domain == AnalysisDomain.WELLNESS:
            return _analyze_wellness(
                client, athlete_ids, date_filter,
                request.wellness_filters, filters_applied, agg_mode,
            )
        elif domain == AnalysisDomain.VBT:
            return _analyze_vbt(
                client, athlete_ids, date_filter,
                request.vbt_filters, filters_applied, agg_mode,
            )
        elif domain == AnalysisDomain.LACTATE:
            return _analyze_lactate(
                client, athlete_ids, date_filter,
                request.lactate_filters, filters_applied, agg_mode,
            )
        elif domain == AnalysisDomain.AIR_BIKE:
            return _analyze_air_bike(
                client, athlete_ids, date_filter,
                request.air_bike_filters, filters_applied, agg_mode,
            )
        elif domain == AnalysisDomain.ASSESSMENTS:
            return _analyze_assessments(
                client, athlete_ids, date_filter,
                request.assessment_filters, filters_applied,
            )

        return AnalysisResponse(
            domain=domain.value,
            athlete_count=len(athlete_ids),
            record_count=0,
            filters_applied=filters_applied,
        )


# ── Athlete filtering ────────────────────────────────────────────────


def _apply_athlete_filters(
    athletes: List[dict], f: AthleteFilter
) -> List[dict]:
    """Apply demographic filters to athlete records."""
    result = athletes

    if f.gender:
        result = [a for a in result if a.get("gender") == f.gender]

    if f.status:
        result = [a for a in result if a.get("status") == f.status]

    if f.age_min is not None or f.age_max is not None:
        today = date.today()
        filtered = []
        for a in result:
            dob = a.get("date_of_birth")
            if not dob:
                continue
            if isinstance(dob, str):
                try:
                    dob = datetime.strptime(dob, "%Y-%m-%d").date()
                except ValueError:
                    continue
            age = (today - dob).days / 365.25
            if f.age_min is not None and age < f.age_min:
                continue
            if f.age_max is not None and age > f.age_max:
                continue
            filtered.append(a)
        result = filtered

    if f.mass_band:
        result = [
            a for a in result
            if a.get("body_mass_kg")
            and StatEngine.get_mass_band(a["body_mass_kg"]) == f.mass_band
        ]

    if f.stature_min_cm is not None:
        result = [
            a for a in result
            if a.get("stature_cm") is not None
            and a["stature_cm"] >= f.stature_min_cm
        ]

    if f.stature_max_cm is not None:
        result = [
            a for a in result
            if a.get("stature_cm") is not None
            and a["stature_cm"] <= f.stature_max_cm
        ]

    return result


# ── Helpers ───────────────────────────────────────────────────────────


def _build_filters_applied(request: AnalysisRequest) -> Dict[str, str]:
    """Build human-readable filter summary."""
    fa: Dict[str, str] = {"data_source": request.data_source.value}

    af = request.athlete_filter
    if af:
        if af.gender:
            fa["gender"] = af.gender
        if af.status:
            fa["status"] = af.status
        if af.age_min is not None:
            fa["age_min"] = str(af.age_min)
        if af.age_max is not None:
            fa["age_max"] = str(af.age_max)
        if af.mass_band:
            fa["mass_band"] = af.mass_band
        if af.stature_min_cm is not None:
            fa["stature_min_cm"] = str(af.stature_min_cm)
        if af.stature_max_cm is not None:
            fa["stature_max_cm"] = str(af.stature_max_cm)

    df = request.date_filter
    if df:
        if df.start_date:
            fa["start_date"] = df.start_date.isoformat()
        if df.end_date:
            fa["end_date"] = df.end_date.isoformat()

    return fa


def _stats_for_metric(
    key: str, label: str, values: List[float],
) -> DescriptiveStats:
    """Compute descriptive stats for a single metric."""
    stats = StatEngine.calculate_descriptive_stats(values)
    if stats is None:
        return DescriptiveStats(metric=key, label=label, count=0)
    return DescriptiveStats(
        metric=key,
        label=label,
        count=stats["count"],
        mean=stats["mean"],
        std_dev=stats["std_dev"],
        median=stats["median"],
        min_val=stats["min"],
        max_val=stats["max"],
        ci_lower=stats["ci_lower"],
        ci_upper=stats["ci_upper"],
    )


def _apply_aggregation(
    athlete_dists: Dict[str, Dict[str, List[float]]],
    mode: AggregationMode,
) -> Dict[str, List[float]]:
    """Flatten athlete-keyed distributions based on aggregation mode.

    Args:
        athlete_dists: metric -> {athlete_id -> [values]}
        mode: aggregation strategy

    Returns:
        metric -> [flat values] ready for _stats_for_metric()
    """
    result: Dict[str, List[float]] = {}

    for metric, athlete_vals in athlete_dists.items():
        flat: List[float] = []

        if mode == AggregationMode.ALL_RECORDS:
            for vals in athlete_vals.values():
                flat.extend(vals)
        elif mode == AggregationMode.MEAN_PER_ATHLETE:
            for vals in athlete_vals.values():
                if vals:
                    m = StatEngine.calculate_mean(vals)
                    if m is not None:
                        flat.append(m)
        elif mode == AggregationMode.MEDIAN_PER_ATHLETE:
            for vals in athlete_vals.values():
                if vals:
                    m = StatEngine.calculate_median(vals)
                    if m is not None:
                        flat.append(m)
        elif mode == AggregationMode.PEAK_PER_ATHLETE:
            for vals in athlete_vals.values():
                if vals:
                    flat.append(max(vals))

        if flat:
            result[metric] = flat

    return result


# ── Domain analyzers ─────────────────────────────────────────────────


def _fetch_performance_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[PerformanceFilters],
) -> tuple[List[dict], Dict[str, Dict[str, List[float]]]]:
    """Fetch performance events and extract athlete-keyed metric distributions."""
    rows = _chunked_in_query(
        client, "performance_events", "athlete_id, metrics, event_date",
        "athlete_id", athlete_ids,
        date_column="event_date", date_filter=date_filter,
    )

    # Determine which metrics to report
    requested_keys = None
    if filters and filters.metric_keys:
        requested_keys = set(filters.metric_keys)

    distributions: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        athlete_id = row["athlete_id"]
        metrics = row.get("metrics") or {}
        for key, val in metrics.items():
            if key in NON_METRIC_KEYS:
                continue
            if requested_keys and key not in requested_keys:
                continue
            if isinstance(val, (int, float)) and val is not None:
                distributions.setdefault(key, {}).setdefault(athlete_id, []).append(float(val))

    return rows, distributions


def _analyze_performance(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[PerformanceFilters],
    filters_applied: Dict[str, str],
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS,
) -> AnalysisResponse:
    rows, athlete_dists = _fetch_performance_data(
        client, athlete_ids, date_filter, filters,
    )

    flat_dists = _apply_aggregation(athlete_dists, aggregation_mode)

    statistics = []
    for key, values in sorted(flat_dists.items()):
        defn = METRIC_BY_KEY.get(key)
        label = defn.label if defn else key
        statistics.append(_stats_for_metric(key, label, values))

    unique_athletes = {r["athlete_id"] for r in rows}

    return AnalysisResponse(
        domain=AnalysisDomain.PERFORMANCE.value,
        athlete_count=len(unique_athletes),
        record_count=len(rows),
        aggregation_mode=aggregation_mode.value,
        filters_applied=filters_applied,
        statistics=statistics,
        distributions=flat_dists,
    )


def _fetch_training_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[TrainingFilters],
) -> tuple[List[dict], Dict[str, Dict[str, List[float]]]]:
    """Fetch training sessions and extract athlete-keyed metric distributions."""
    extra = {}
    if filters and filters.training_type:
        extra["training_type"] = filters.training_type

    rows = _chunked_in_query(
        client, "training_sessions",
        "athlete_id, duration_minutes, rpe, srpe, training_type, session_date",
        "athlete_id", athlete_ids,
        extra_filters=extra if extra else None,
        date_column="session_date", date_filter=date_filter,
    )

    distributions: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        athlete_id = row["athlete_id"]
        if row.get("duration_minutes") is not None:
            distributions.setdefault("duration_minutes", {}).setdefault(athlete_id, []).append(
                float(row["duration_minutes"])
            )
        if row.get("rpe") is not None:
            distributions.setdefault("rpe", {}).setdefault(athlete_id, []).append(float(row["rpe"]))
        if row.get("srpe") is not None:
            distributions.setdefault("srpe", {}).setdefault(athlete_id, []).append(float(row["srpe"]))

    return rows, distributions


def _analyze_training(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[TrainingFilters],
    filters_applied: Dict[str, str],
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS,
) -> AnalysisResponse:
    rows, athlete_dists = _fetch_training_data(
        client, athlete_ids, date_filter, filters,
    )

    flat_dists = _apply_aggregation(athlete_dists, aggregation_mode)

    label_map = {
        "duration_minutes": "Duration (min)",
        "rpe": "RPE",
        "srpe": "sRPE",
    }

    statistics = [
        _stats_for_metric(k, label_map.get(k, k), v)
        for k, v in sorted(flat_dists.items())
    ]

    unique_athletes = {r["athlete_id"] for r in rows}

    return AnalysisResponse(
        domain=AnalysisDomain.TRAINING.value,
        athlete_count=len(unique_athletes),
        record_count=len(rows),
        aggregation_mode=aggregation_mode.value,
        filters_applied=filters_applied,
        statistics=statistics,
        distributions=flat_dists,
    )


def _fetch_wellness_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[WellnessFilters],
) -> tuple[List[dict], Dict[str, Dict[str, List[float]]]]:
    """Fetch wellness entries and extract athlete-keyed score distributions."""
    rows = _chunked_in_query(
        client, "wellness_entries",
        "athlete_id, sleep_quality, fatigue, muscle_soreness, stress_level, mood, hooper_index, entry_date",
        "athlete_id", athlete_ids,
        date_column="entry_date", date_filter=date_filter,
    )

    score_fields = [
        "sleep_quality", "fatigue", "muscle_soreness", "stress_level", "mood", "hooper_index",
    ]

    distributions: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        athlete_id = row["athlete_id"]
        for field in score_fields:
            val = row.get(field)
            if val is not None:
                distributions.setdefault(field, {}).setdefault(athlete_id, []).append(float(val))

    return rows, distributions


def _analyze_wellness(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[WellnessFilters],
    filters_applied: Dict[str, str],
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS,
) -> AnalysisResponse:
    rows, athlete_dists = _fetch_wellness_data(
        client, athlete_ids, date_filter, filters,
    )

    flat_dists = _apply_aggregation(athlete_dists, aggregation_mode)

    label_map = {
        "sleep_quality": "Sleep Quality",
        "fatigue": "Fatigue",
        "muscle_soreness": "Muscle Soreness",
        "stress_level": "Stress Level",
        "mood": "Mood",
        "hooper_index": "Hooper Index",
    }

    statistics = [
        _stats_for_metric(k, label_map.get(k, k), v)
        for k, v in sorted(flat_dists.items())
    ]

    unique_athletes = {r["athlete_id"] for r in rows}

    return AnalysisResponse(
        domain=AnalysisDomain.WELLNESS.value,
        athlete_count=len(unique_athletes),
        record_count=len(rows),
        aggregation_mode=aggregation_mode.value,
        filters_applied=filters_applied,
        statistics=statistics,
        distributions=flat_dists,
    )


def _fetch_vbt_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[VbtFilters],
) -> tuple[List[dict], Dict[str, Dict[str, List[float]]]]:
    """Fetch VBT profiles + sets and extract athlete-keyed distributions."""
    extra = {}
    if filters and filters.exercise_name:
        extra["exercise_name"] = filters.exercise_name

    profiles = _chunked_in_query(
        client, "vbt_profiles",
        "id, athlete_id, exercise_name, test_date",
        "athlete_id", athlete_ids,
        extra_filters=extra if extra else None,
        date_column="test_date", date_filter=date_filter,
    )

    if not profiles:
        return [], {}

    profile_to_athlete = {p["id"]: p["athlete_id"] for p in profiles}

    profile_ids = [p["id"] for p in profiles]
    sets = _chunked_in_query(
        client, "vbt_sets",
        "profile_id, load_kg, mean_velocity",
        "profile_id", profile_ids,
    )

    distributions: Dict[str, Dict[str, List[float]]] = {}
    for s in sets:
        athlete_id = profile_to_athlete.get(s["profile_id"])
        if not athlete_id:
            continue
        if s.get("load_kg") is not None:
            distributions.setdefault("load_kg", {}).setdefault(athlete_id, []).append(float(s["load_kg"]))
        if s.get("mean_velocity") is not None:
            distributions.setdefault("mean_velocity", {}).setdefault(athlete_id, []).append(
                float(s["mean_velocity"])
            )

    return profiles, distributions


def _analyze_vbt(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[VbtFilters],
    filters_applied: Dict[str, str],
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS,
) -> AnalysisResponse:
    profiles, athlete_dists = _fetch_vbt_data(
        client, athlete_ids, date_filter, filters,
    )

    flat_dists = _apply_aggregation(athlete_dists, aggregation_mode)

    label_map = {
        "load_kg": "Load (kg)",
        "mean_velocity": "Mean Velocity (m/s)",
    }

    statistics = [
        _stats_for_metric(k, label_map.get(k, k), v)
        for k, v in sorted(flat_dists.items())
    ]

    unique_athletes = {p["athlete_id"] for p in profiles}

    return AnalysisResponse(
        domain=AnalysisDomain.VBT.value,
        athlete_count=len(unique_athletes),
        record_count=len(profiles),
        aggregation_mode=aggregation_mode.value,
        filters_applied=filters_applied,
        statistics=statistics,
        distributions=flat_dists,
    )


def _fetch_lactate_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[LactateFilters],
) -> tuple[List[dict], Dict[str, Dict[str, List[float]]]]:
    """Fetch lactate tests and extract athlete-keyed threshold distributions."""
    extra = {}
    if filters and filters.test_type:
        extra["test_type"] = filters.test_type

    rows = _chunked_in_query(
        client, "lactate_tests",
        "id, athlete_id, test_date, test_type, lt1_speed, lt1_hr, lt2_speed, lt2_hr",
        "athlete_id", athlete_ids,
        extra_filters=extra if extra else None,
        date_column="test_date", date_filter=date_filter,
    )

    distributions: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        athlete_id = row["athlete_id"]
        for field in ["lt1_speed", "lt1_hr", "lt2_speed", "lt2_hr"]:
            val = row.get(field)
            if val is not None:
                distributions.setdefault(field, {}).setdefault(athlete_id, []).append(float(val))

    return rows, distributions


def _analyze_lactate(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[LactateFilters],
    filters_applied: Dict[str, str],
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS,
) -> AnalysisResponse:
    rows, athlete_dists = _fetch_lactate_data(
        client, athlete_ids, date_filter, filters,
    )

    flat_dists = _apply_aggregation(athlete_dists, aggregation_mode)

    label_map = {
        "lt1_speed": "LT1 Speed",
        "lt1_hr": "LT1 Heart Rate",
        "lt2_speed": "LT2 Speed",
        "lt2_hr": "LT2 Heart Rate",
    }

    statistics = [
        _stats_for_metric(k, label_map.get(k, k), v)
        for k, v in sorted(flat_dists.items())
    ]

    unique_athletes = {r["athlete_id"] for r in rows}

    return AnalysisResponse(
        domain=AnalysisDomain.LACTATE.value,
        athlete_count=len(unique_athletes),
        record_count=len(rows),
        aggregation_mode=aggregation_mode.value,
        filters_applied=filters_applied,
        statistics=statistics,
        distributions=flat_dists,
    )


def _fetch_air_bike_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[AirBikeFilters],
) -> tuple[List[dict], Dict[str, Dict[str, List[float]]]]:
    """Fetch air bike tests + sprints and extract athlete-keyed power distributions."""
    tests = _chunked_in_query(
        client, "air_bike_tests",
        "id, athlete_id, test_date",
        "athlete_id", athlete_ids,
        date_column="test_date", date_filter=date_filter,
    )

    if not tests:
        return [], {}

    test_to_athlete = {t["id"]: t["athlete_id"] for t in tests}

    test_ids = [t["id"] for t in tests]
    sprints = _chunked_in_query(
        client, "air_bike_sprints",
        "test_id, sprint_duration_s, peak_power_w, avg_power_w",
        "test_id", test_ids,
    )

    distributions: Dict[str, Dict[str, List[float]]] = {}
    for s in sprints:
        athlete_id = test_to_athlete.get(s["test_id"])
        if not athlete_id:
            continue
        if s.get("peak_power_w") is not None:
            distributions.setdefault("peak_power_w", {}).setdefault(athlete_id, []).append(
                float(s["peak_power_w"])
            )
        if s.get("avg_power_w") is not None:
            distributions.setdefault("avg_power_w", {}).setdefault(athlete_id, []).append(
                float(s["avg_power_w"])
            )

    return tests, distributions


def _analyze_air_bike(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[AirBikeFilters],
    filters_applied: Dict[str, str],
    aggregation_mode: AggregationMode = AggregationMode.ALL_RECORDS,
) -> AnalysisResponse:
    tests, athlete_dists = _fetch_air_bike_data(
        client, athlete_ids, date_filter, filters,
    )

    flat_dists = _apply_aggregation(athlete_dists, aggregation_mode)

    label_map = {
        "peak_power_w": "Peak Power (W)",
        "avg_power_w": "Avg Power (W)",
    }

    statistics = [
        _stats_for_metric(k, label_map.get(k, k), v)
        for k, v in sorted(flat_dists.items())
    ]

    unique_athletes = {t["athlete_id"] for t in tests}

    return AnalysisResponse(
        domain=AnalysisDomain.AIR_BIKE.value,
        athlete_count=len(unique_athletes),
        record_count=len(tests),
        aggregation_mode=aggregation_mode.value,
        filters_applied=filters_applied,
        statistics=statistics,
        distributions=flat_dists,
    )


def _fetch_assessment_data(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[AssessmentFilters],
) -> tuple[List[dict], List[DysfunctionPrevalence]]:
    """Fetch movement assessments and compute dysfunction prevalence."""
    extra = {}
    if filters and filters.assessment_type:
        extra["assessment_type"] = filters.assessment_type

    rows = _chunked_in_query(
        client, "movement_assessments",
        "athlete_id, assessment_type, findings, assessment_date",
        "athlete_id", athlete_ids,
        extra_filters=extra if extra else None,
        date_column="assessment_date", date_filter=date_filter,
    )

    # Count dysfunction prevalence across all assessments
    dysfunction_counts: Dict[str, Dict[str, int]] = {}  # region -> dysfunction -> count
    total_assessed = len(rows)

    for row in rows:
        findings = row.get("findings") or {}
        for region, dysfunctions in findings.items():
            if not isinstance(dysfunctions, dict):
                continue
            for dysfunction, detail in dysfunctions.items():
                if not isinstance(detail, dict):
                    continue
                if detail.get("observed"):
                    dysfunction_counts.setdefault(region, {})
                    dysfunction_counts[region][dysfunction] = (
                        dysfunction_counts[region].get(dysfunction, 0) + 1
                    )

    prevalence = []
    for region, dysfunctions in sorted(dysfunction_counts.items()):
        for dysfunction, count in sorted(dysfunctions.items()):
            pct = round((count / total_assessed) * 100, 1) if total_assessed > 0 else 0.0
            prevalence.append(DysfunctionPrevalence(
                region=region,
                dysfunction=dysfunction,
                count=count,
                total_assessed=total_assessed,
                prevalence_pct=pct,
            ))

    return rows, prevalence


def _analyze_assessments(
    client: Any,
    athlete_ids: List[str],
    date_filter: Optional[DateFilter],
    filters: Optional[AssessmentFilters],
    filters_applied: Dict[str, str],
) -> AnalysisResponse:
    rows, prevalence = _fetch_assessment_data(
        client, athlete_ids, date_filter, filters,
    )

    unique_athletes = {r["athlete_id"] for r in rows}

    return AnalysisResponse(
        domain=AnalysisDomain.ASSESSMENTS.value,
        athlete_count=len(unique_athletes),
        record_count=len(rows),
        aggregation_mode="all_records",
        filters_applied=filters_applied,
        dysfunction_prevalence=prevalence,
    )
