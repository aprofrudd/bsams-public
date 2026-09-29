"""Metabolic profiling engine (Ferretti/di Prampero 3-sprint protocol).

Calculates alactic capacity, max glycolytic power, anaerobic cost,
and fatigue slope from 3x10s sprint data with blood lactate measurements.
"""

from dataclasses import dataclass, field


# Constants
BETA = 63  # O2 equivalent of lactate (J/kg per mmol/L)
ETA = 0.25  # Mechanical efficiency
TAU = 15  # Lactate half-life (seconds)


@dataclass
class MetabolicResult:
    """Result of metabolic profile calculation."""

    mech_work: list[float]  # 3 values (J)
    alactic_capacity: float  # J
    max_glycolytic_power: float | None  # W
    anaerobic_cost: float | None  # dimensionless
    fatigue_slope: float | None  # W
    alactic: list[float]  # 3 values (J, unclamped)
    glycolytic: list[float]  # 3 values (J, unclamped)
    warnings: list[str] = field(default_factory=list)


def sum_watts(
    samples: list[dict],
    from_sec: float,
    to_sec: float,
    trim_sec: float = 0,
) -> float:
    """Integrate power samples over a time window.

    Args:
        samples: List of dicts with elapsed_ms and watts keys.
        from_sec: Start of window in seconds.
        to_sec: End of window in seconds.
        trim_sec: Offset to trim from the start of the window.

    Returns:
        Total mechanical work in joules.
    """
    if not samples:
        return 0.0

    start_ms = (from_sec + trim_sec) * 1000
    end_ms = to_sec * 1000

    # Filter samples within the window
    filtered = [
        s for s in samples
        if s.get("elapsed_ms", 0) >= start_ms and s.get("elapsed_ms", 0) < end_ms
    ]

    if not filtered:
        return 0.0

    # Sort by elapsed_ms
    filtered.sort(key=lambda s: s["elapsed_ms"])

    total_j = 0.0
    n = len(filtered)

    for i, sample in enumerate(filtered):
        watts = sample.get("watts", 0) or 0

        if i == 0:
            # First sample: use interval to next sample (or 1.0 if only one)
            if n > 1:
                dt = (filtered[1]["elapsed_ms"] - filtered[0]["elapsed_ms"]) / 1000
            else:
                dt = 1.0
        else:
            dt = (filtered[i]["elapsed_ms"] - filtered[i - 1]["elapsed_ms"]) / 1000

        # Clamp dt to [0.1, 3.0] to handle jitter
        dt = max(0.1, min(3.0, dt))
        total_j += watts * dt

    return total_j


def calculate_metabolic_profile(
    body_mass_kg: float,
    resting_lactate: float,
    la_peaks: list[float],
    mech_work_j: list[float],
) -> MetabolicResult:
    """Calculate metabolic profile from 3-sprint protocol data.

    Args:
        body_mass_kg: Athlete body mass in kg.
        resting_lactate: Resting blood lactate (mmol/L).
        la_peaks: Peak lactate after each sprint [sprint1, sprint2, sprint3] (mmol/L).
        mech_work_j: Mechanical work per sprint [sprint1, sprint2, sprint3] (J).

    Returns:
        MetabolicResult with all computed values.
    """
    warnings: list[str] = []

    # Baseline corrections for residual lactate from previous sprints
    base2 = la_peaks[0] * (0.5 ** (3 / TAU))
    base3 = la_peaks[1] * (0.5 ** (12 / TAU))

    # Delta lactate per sprint
    dLa1 = la_peaks[0] - resting_lactate
    dLa2 = la_peaks[1] - base2
    dLa3 = la_peaks[2] - base3

    # Warn on negative deltas
    for i, dLa in enumerate([dLa1, dLa2, dLa3], 1):
        if dLa < 0:
            warnings.append(f"Negative delta lactate for sprint {i}: {dLa:.2f} mmol/L")

    # Warn on zero mechanical work
    for i, w in enumerate(mech_work_j, 1):
        if w <= 0:
            warnings.append(f"Zero or negative mechanical work for sprint {i}: {w:.1f} J")

    # Glycolytic energy per sprint (unclamped)
    glyco_1 = dLa1 * body_mass_kg * BETA * ETA
    glyco_2 = dLa2 * body_mass_kg * BETA * ETA
    glyco_3 = dLa3 * body_mass_kg * BETA * ETA

    # Alactic energy per sprint (unclamped)
    alac_1 = mech_work_j[0] - glyco_1
    alac_2 = mech_work_j[1] - glyco_2
    alac_3 = mech_work_j[2] - glyco_3

    # Key metrics
    alactic_capacity = mech_work_j[0] - dLa1 * body_mass_kg * BETA * ETA

    max_glycolytic_power: float | None = None
    if True:  # always compute
        max_glycolytic_power = (dLa2 * body_mass_kg * BETA * ETA) / 10

    anaerobic_cost: float | None = None
    if mech_work_j[1] > 0:
        anaerobic_cost = (dLa2 * body_mass_kg * BETA * ETA) / mech_work_j[1]

    fatigue_slope: float | None = None
    if True:  # always compute
        fatigue_slope = (dLa3 * body_mass_kg * BETA * ETA) / 10

    return MetabolicResult(
        mech_work=list(mech_work_j),
        alactic_capacity=alactic_capacity,
        max_glycolytic_power=max_glycolytic_power,
        anaerobic_cost=anaerobic_cost,
        fatigue_slope=fatigue_slope,
        alactic=[alac_1, alac_2, alac_3],
        glycolytic=[glyco_1, glyco_2, glyco_3],
        warnings=warnings,
    )


def generate_insights(result: MetabolicResult, body_mass_kg: float) -> list[dict]:
    """Generate insight cards from metabolic profile results.

    Args:
        result: MetabolicResult from calculation.
        body_mass_kg: Athlete body mass in kg.

    Returns:
        List of insight dicts with category, title, value, unit, interpretation.
    """
    insights = []

    # 1. Alactic Capacity
    alactic_per_kg = result.alactic_capacity / body_mass_kg if body_mass_kg > 0 else 0
    insights.append({
        "category": "alactic_capacity",
        "title": "Alactic Capacity",
        "value": round(result.alactic_capacity, 1),
        "unit": "J",
        "relative_value": round(alactic_per_kg, 1),
        "relative_unit": "J/kg",
        "interpretation": (
            "High" if alactic_per_kg > 40
            else "Moderate" if alactic_per_kg > 25
            else "Low"
        ),
    })

    # 2. Max Glycolytic Power
    if result.max_glycolytic_power is not None:
        glyco_per_kg = result.max_glycolytic_power / body_mass_kg if body_mass_kg > 0 else 0
        insights.append({
            "category": "glycolytic_power",
            "title": "Max Glycolytic Power",
            "value": round(result.max_glycolytic_power, 1),
            "unit": "W",
            "relative_value": round(glyco_per_kg, 2),
            "relative_unit": "W/kg",
            "interpretation": (
                "High" if glyco_per_kg > 5
                else "Moderate" if glyco_per_kg > 3
                else "Low"
            ),
        })

    # 3. Anaerobic Cost
    if result.anaerobic_cost is not None:
        insights.append({
            "category": "anaerobic_cost",
            "title": "Anaerobic Cost",
            "value": round(result.anaerobic_cost, 4),
            "unit": "",
            "interpretation": (
                "High (inefficient)" if result.anaerobic_cost > 0.5
                else "Moderate" if result.anaerobic_cost > 0.3
                else "Low (efficient)"
            ),
        })

    # 4. Fatigue Slope
    if result.fatigue_slope is not None:
        insights.append({
            "category": "fatigue_resistance",
            "title": "Fatigue Slope",
            "value": round(result.fatigue_slope, 1),
            "unit": "W",
            "interpretation": (
                "High fatigue" if result.fatigue_slope > 50
                else "Moderate fatigue" if result.fatigue_slope > 25
                else "Good fatigue resistance"
            ),
        })

    # 5. Energy System Balance (sprint 1)
    total_sprint1 = result.mech_work[0] if result.mech_work[0] > 0 else 1
    alactic_pct = (result.alactic[0] / total_sprint1) * 100
    glycolytic_pct = (result.glycolytic[0] / total_sprint1) * 100
    insights.append({
        "category": "energy_balance",
        "title": "Sprint 1 Energy Balance",
        "value": round(alactic_pct, 1),
        "unit": "% alactic",
        "glycolytic_pct": round(glycolytic_pct, 1),
        "interpretation": (
            "Alactic dominant" if alactic_pct > 70
            else "Balanced" if alactic_pct > 40
            else "Glycolytic dominant"
        ),
    })

    # 6. Mechanical Work Trend
    if len(result.mech_work) == 3 and result.mech_work[0] > 0:
        work_drop = ((result.mech_work[0] - result.mech_work[2]) / result.mech_work[0]) * 100
        insights.append({
            "category": "work_trend",
            "title": "Work Output Decline",
            "value": round(work_drop, 1),
            "unit": "%",
            "interpretation": (
                "Severe decline" if work_drop > 30
                else "Moderate decline" if work_drop > 15
                else "Well maintained"
            ),
        })

    return insights
