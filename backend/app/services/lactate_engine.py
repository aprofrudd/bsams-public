"""Lactate threshold detection engine.

Provides piecewise regression breakpoint detection to identify LT1 and LT2
from staged lactate test data (intensity vs blood lactate concentration).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Segment:
    """A single linear segment of the piecewise regression."""

    start_x: float
    end_x: float
    slope: float
    intercept: float


@dataclass
class BreakpointResult:
    """Result of piecewise regression breakpoint detection."""

    lt1_x: float
    lt1_lactate: float
    lt2_x: float
    lt2_lactate: float
    segments: list[Segment]  # always 3
    total_sse: float
    r_squared: float


def _fit_segment(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Fit a single linear regression segment.

    Returns (slope, intercept, sse).
    If only one point, returns (0, y[0], 0).
    If empty, returns (0, 0, 0).
    """
    n = len(xs)
    if n == 0:
        return (0.0, 0.0, 0.0)
    if n == 1:
        return (0.0, ys[0], 0.0)

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        # All x values identical — flat line at mean y
        mean_y = sum_y / n
        sse = sum((y - mean_y) ** 2 for y in ys)
        return (0.0, mean_y, sse)

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    sse = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    return (slope, intercept, sse)


def detect_breakpoints(
    intensities: list[float], lactates: list[float]
) -> Optional[BreakpointResult]:
    """Detect LT1 and LT2 breakpoints using piecewise regression.

    Splits sorted data into 3 linear segments minimizing total SSE.
    Requires at least 5 data points.

    Args:
        intensities: Intensity values (speed km/h or power W)
        lactates: Blood lactate values (mmol/L)

    Returns:
        BreakpointResult with LT1/LT2 and segment info, or None if insufficient data.
    """
    n = len(intensities)
    if n < 5 or n != len(lactates):
        return None

    # Sort by intensity ascending
    pairs = sorted(zip(intensities, lactates), key=lambda p: p[0])
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    # Check all identical intensities
    if xs[0] == xs[-1]:
        return None

    best_sse = float("inf")
    best_i = -1
    best_j = -1

    # Try all valid breakpoint pairs (i, j)
    # Segment 1: [0..i] (≥2 pts), Segment 2: [i+1..j] (≥1 pt), Segment 3: [j+1..n-1] (≥2 pts)
    for i in range(1, n - 3):  # i: last index of segment 1 (need ≥2 pts, so i >= 1)
        for j in range(i + 1, n - 2):  # j: last index of segment 2 (need ≥2 pts in seg 3, so j <= n-3)
            seg1_xs, seg1_ys = xs[: i + 1], ys[: i + 1]
            seg2_xs, seg2_ys = xs[i + 1 : j + 1], ys[i + 1 : j + 1]
            seg3_xs, seg3_ys = xs[j + 1 :], ys[j + 1 :]

            _, _, sse1 = _fit_segment(seg1_xs, seg1_ys)
            _, _, sse2 = _fit_segment(seg2_xs, seg2_ys)
            _, _, sse3 = _fit_segment(seg3_xs, seg3_ys)

            total_sse = sse1 + sse2 + sse3
            if total_sse < best_sse:
                best_sse = total_sse
                best_i = i
                best_j = j

    if best_i < 0:
        return None

    # Refit best segments
    seg1_xs, seg1_ys = xs[: best_i + 1], ys[: best_i + 1]
    seg2_xs, seg2_ys = xs[best_i + 1 : best_j + 1], ys[best_i + 1 : best_j + 1]
    seg3_xs, seg3_ys = xs[best_j + 1 :], ys[best_j + 1 :]

    slope1, intercept1, _ = _fit_segment(seg1_xs, seg1_ys)
    slope2, intercept2, _ = _fit_segment(seg2_xs, seg2_ys)
    slope3, intercept3, _ = _fit_segment(seg3_xs, seg3_ys)

    # LT1 = midpoint between last of segment 1 and first of segment 2
    lt1_x = (xs[best_i] + xs[best_i + 1]) / 2
    # LT2 = midpoint between last of segment 2 and first of segment 3
    lt2_x = (xs[best_j] + xs[best_j + 1]) / 2

    # Evaluate regression lines at breakpoint X values
    lt1_lactate = slope1 * lt1_x + intercept1
    lt2_lactate = slope2 * lt2_x + intercept2

    # Calculate R²
    mean_y = sum(ys) / n
    ss_total = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1.0 - (best_sse / ss_total) if ss_total > 0 else 1.0

    segments = [
        Segment(start_x=seg1_xs[0], end_x=seg1_xs[-1], slope=slope1, intercept=intercept1),
        Segment(start_x=seg2_xs[0], end_x=seg2_xs[-1], slope=slope2, intercept=intercept2),
        Segment(start_x=seg3_xs[0], end_x=seg3_xs[-1], slope=slope3, intercept=intercept3),
    ]

    return BreakpointResult(
        lt1_x=round(lt1_x, 2),
        lt1_lactate=round(lt1_lactate, 2),
        lt2_x=round(lt2_x, 2),
        lt2_lactate=round(lt2_lactate, 2),
        segments=segments,
        total_sse=round(best_sse, 6),
        r_squared=round(r_squared, 4),
    )


def build_lactate_analysis(
    intensities: list[float], lactates: list[float]
) -> Optional[BreakpointResult]:
    """Build a lactate threshold analysis from stage data.

    Public wrapper around detect_breakpoints.

    Args:
        intensities: Intensity values (speed or power)
        lactates: Blood lactate values (mmol/L)

    Returns:
        BreakpointResult or None if insufficient data.
    """
    return detect_breakpoints(intensities, lactates)
