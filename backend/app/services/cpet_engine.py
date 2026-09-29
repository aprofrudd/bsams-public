"""CPET gas analysis computation engine.

Computes max fat oxidation, threshold-associated metrics via interpolation,
and CHO/FAT crossover detection from stage-averaged gas analysis data.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FatMaxResult:
    """Max fat oxidation result with associated metrics."""

    max_fat_oxidation_gh: float
    fat_max_stage_number: int
    fat_max_intensity: Optional[float] = None
    fat_max_hr: Optional[float] = None


@dataclass
class ThresholdMetrics:
    """Interpolated gas metrics at a given threshold intensity."""

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


def compute_fat_max(stage_averages: list[dict]) -> Optional[FatMaxResult]:
    """Find the stage with maximum fat oxidation.

    Args:
        stage_averages: List of stage average dicts with avg_fat_gh key.

    Returns:
        FatMaxResult or None if no fat data available.
    """
    best_fat = -1.0
    best_stage = None

    for sa in stage_averages:
        fat = sa.get("avg_fat_gh")
        if fat is not None and fat > best_fat:
            best_fat = fat
            best_stage = sa

    if best_stage is None or best_fat <= 0:
        return None

    return FatMaxResult(
        max_fat_oxidation_gh=round(best_fat, 1),
        fat_max_stage_number=best_stage["stage_number"],
        fat_max_intensity=best_stage.get("intensity_value"),
        fat_max_hr=round(best_stage["avg_hr_bpm"]) if best_stage.get("avg_hr_bpm") else None,
    )


def interpolate_at_intensity(
    stage_averages: list[dict],
    target_intensity: float,
    metric_key: str,
) -> Optional[float]:
    """Linear interpolation of a metric at a target intensity.

    Finds the two adjacent stages bracketing the target intensity and
    interpolates linearly between them.

    Args:
        stage_averages: List of stage average dicts sorted by intensity.
        target_intensity: The intensity value to interpolate at.
        metric_key: The key to interpolate (e.g. 'avg_vo2_ml_kg_min').

    Returns:
        Interpolated value or None if interpolation not possible.
    """
    # Filter stages with both intensity and the target metric
    valid = [
        sa for sa in stage_averages
        if sa.get("intensity_value") is not None and sa.get(metric_key) is not None
    ]
    if not valid:
        return None

    # Sort by intensity
    valid.sort(key=lambda sa: sa["intensity_value"])

    # Exact match
    for sa in valid:
        if sa["intensity_value"] == target_intensity:
            return sa[metric_key]

    # Find bracketing stages
    lower = None
    upper = None
    for sa in valid:
        if sa["intensity_value"] <= target_intensity:
            lower = sa
        elif upper is None:
            upper = sa

    if lower is None or upper is None:
        # Extrapolation: use nearest two points
        if len(valid) < 2:
            return valid[0][metric_key] if valid else None
        if lower is None:
            lower, upper = valid[0], valid[1]
        else:
            lower, upper = valid[-2], valid[-1]

    # Linear interpolation
    x1, x2 = lower["intensity_value"], upper["intensity_value"]
    y1, y2 = lower[metric_key], upper[metric_key]

    if x2 == x1:
        return y1

    t = (target_intensity - x1) / (x2 - x1)
    return round(y1 + t * (y2 - y1), 2)


def compute_threshold_metrics(
    stage_averages: list[dict],
    threshold_intensity: float,
) -> Optional[ThresholdMetrics]:
    """Compute interpolated gas metrics at a threshold intensity.

    Args:
        stage_averages: List of stage average dicts.
        threshold_intensity: Intensity value (speed or power) at the threshold.

    Returns:
        ThresholdMetrics with all interpolated values, or None if no data.
    """
    if not stage_averages:
        return None

    metrics = ThresholdMetrics(intensity=threshold_intensity)

    field_map = {
        "avg_vo2_ml_kg_min": "vo2_ml_kg_min",
        "avg_vo2_l_min": "vo2_l_min",
        "avg_rer": "rer",
        "avg_ve_l_min": "ve_l_min",
        "avg_bf_per_min": "bf_per_min",
        "avg_hr_bpm": "hr_bpm",
        "avg_fat_gh": "fat_gh",
        "avg_cho_gh": "cho_gh",
        "avg_ee_kcal_h": "ee_kcal_h",
        "avg_cho_ee_kcal_h": "cho_ee_kcal_h",
        "avg_fat_ee_kcal_h": "fat_ee_kcal_h",
    }

    any_set = False
    for src_key, dst_key in field_map.items():
        val = interpolate_at_intensity(stage_averages, threshold_intensity, src_key)
        if val is not None:
            setattr(metrics, dst_key, val)
            any_set = True

    return metrics if any_set else None


def find_crossover_intensity(stage_averages: list[dict]) -> Optional[float]:
    """Find the intensity where CHO expenditure exceeds FAT expenditure.

    Looks at consecutive stages to find where cho_ee_kcal_h crosses above fat_ee_kcal_h.
    Falls back to cho_gh/fat_gh if expenditure columns not available.

    Args:
        stage_averages: List of stage average dicts sorted by intensity.

    Returns:
        Interpolated intensity at crossover, or None if not found.
    """
    valid = []
    for sa in stage_averages:
        intensity = sa.get("intensity_value")
        cho = sa.get("avg_cho_ee_kcal_h") or sa.get("avg_cho_gh")
        fat = sa.get("avg_fat_ee_kcal_h") or sa.get("avg_fat_gh")
        if intensity is not None and cho is not None and fat is not None:
            valid.append({"intensity": intensity, "cho": cho, "fat": fat})

    if len(valid) < 2:
        return None

    valid.sort(key=lambda x: x["intensity"])

    for i in range(len(valid) - 1):
        diff_curr = valid[i]["cho"] - valid[i]["fat"]
        diff_next = valid[i + 1]["cho"] - valid[i + 1]["fat"]

        # Crossover: CHO was below FAT, now CHO is above FAT
        if diff_curr <= 0 and diff_next > 0:
            # Linear interpolation to find exact crossover point
            x1, x2 = valid[i]["intensity"], valid[i + 1]["intensity"]
            if diff_next == diff_curr:
                return x1
            t = -diff_curr / (diff_next - diff_curr)
            return round(x1 + t * (x2 - x1), 2)

    return None
