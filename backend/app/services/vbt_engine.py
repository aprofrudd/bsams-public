"""VBT (Velocity Based Training) calculation engine.

Provides linear regression on load-velocity data, estimated 1RM prediction,
and bidirectional velocity/load threshold calculations.
"""

from dataclasses import dataclass
from typing import Optional


# Default Minimum Velocity Thresholds by exercise (m/s)
DEFAULT_MVT: dict[str, float] = {
    "trap bar deadlift": 0.30,
    "back squat": 0.30,
    "front squat": 0.30,
    "bench press": 0.17,
    "overhead press": 0.20,
    "landmine punch throw": 0.50,
}

# Fallback MVT when exercise is not in defaults
FALLBACK_MVT = 0.30


@dataclass
class RegressionResult:
    """Result of linear regression on load-velocity data."""

    slope: float
    intercept: float
    r_squared: float


@dataclass
class VbtAnalysisResult:
    """Complete VBT analysis for a load-velocity profile."""

    slope: float
    intercept: float
    r_squared: float
    estimated_1rm_kg: Optional[float]
    v0_ms: Optional[float]  # velocity at zero load (y-intercept)
    mvt_used_ms: float


def get_default_mvt(exercise_name: str) -> float:
    """Get the default Minimum Velocity Threshold for an exercise.

    Matches case-insensitively against the defaults dict.
    Returns FALLBACK_MVT (0.30) if not found.
    """
    return DEFAULT_MVT.get(exercise_name.lower().strip(), FALLBACK_MVT)


def calculate_regression(
    loads: list[float], velocities: list[float]
) -> Optional[RegressionResult]:
    """Calculate linear regression: velocity = slope * load + intercept.

    Uses least-squares method. Returns None if fewer than 2 data points
    or if all loads are identical.

    Args:
        loads: List of loads in kg (X values)
        velocities: List of velocities in m/s (Y values)

    Returns:
        RegressionResult with slope, intercept, r_squared, or None
    """
    n = len(loads)
    if n < 2 or n != len(velocities):
        return None

    sum_x = sum(loads)
    sum_y = sum(velocities)
    sum_xy = sum(x * y for x, y in zip(loads, velocities))
    sum_x2 = sum(x * x for x in loads)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return None  # All loads identical

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # R² calculation
    mean_y = sum_y / n
    ss_tot = sum((y - mean_y) ** 2 for y in velocities)
    ss_res = sum(
        (y - (slope * x + intercept)) ** 2 for x, y in zip(loads, velocities)
    )

    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

    return RegressionResult(slope=slope, intercept=intercept, r_squared=r_squared)


def predict_1rm(slope: float, intercept: float, mvt: float) -> Optional[float]:
    """Predict estimated 1RM: the load where velocity equals MVT.

    1RM = (MVT - intercept) / slope

    Returns None if slope is zero or positive (no valid intersection),
    or if result is non-positive.
    """
    if slope >= 0:
        return None  # Velocity should decrease with load (negative slope)

    load = (mvt - intercept) / slope
    if load <= 0:
        return None

    return round(load, 1)


def predict_velocity(slope: float, intercept: float, load_kg: float) -> float:
    """Predict velocity at a given load.

    velocity = slope * load + intercept
    """
    return round(slope * load_kg + intercept, 3)


def predict_load(slope: float, intercept: float, velocity_ms: float) -> Optional[float]:
    """Predict load at a given velocity.

    load = (velocity - intercept) / slope

    Returns None if slope is zero.
    """
    if slope == 0:
        return None
    load = (velocity_ms - intercept) / slope
    return round(load, 1) if load > 0 else None


def build_analysis(
    loads: list[float],
    velocities: list[float],
    mvt: float,
) -> Optional[VbtAnalysisResult]:
    """Build a complete VBT analysis from load-velocity data.

    Args:
        loads: Load values in kg
        velocities: Mean velocity values in m/s
        mvt: Minimum Velocity Threshold for the exercise

    Returns:
        VbtAnalysisResult or None if regression fails (< 2 data points)
    """
    regression = calculate_regression(loads, velocities)
    if regression is None:
        return None

    estimated_1rm = predict_1rm(regression.slope, regression.intercept, mvt)
    v0 = round(regression.intercept, 3) if regression.intercept > 0 else None

    return VbtAnalysisResult(
        slope=round(regression.slope, 6),
        intercept=round(regression.intercept, 4),
        r_squared=round(regression.r_squared, 4),
        estimated_1rm_kg=estimated_1rm,
        v0_ms=v0,
        mvt_used_ms=mvt,
    )
