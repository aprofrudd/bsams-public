"""Conditioning engine.

Resolves tier-based intensity targets for conditioning templates.
Uses athlete metabolic/air bike data to calculate personalised
intensity ranges (min/max) based on training tier.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Tier multiplier ranges (fraction of reference power)
TIER_RANGES: dict[str, tuple[float, float]] = {
    "foundation": (0.4, 0.6),
    "intermediate": (0.6, 0.8),
    "advanced": (0.8, 1.0),
}


def resolve_target_intensity(
    client,
    athlete_id: str,
    tier: str,
    intensity_type: str,
) -> tuple[Optional[float], Optional[float], str]:
    """Resolve target intensity range for an athlete based on tier.

    Resolution order for power_watts:
      1. metabolic_profiles.sprint_1_avg_power_w (Ferretti protocol)
      2. air_bike_recordings.peak_power_w (BLE recording)
      3. air_bike_sprints.power_7s (sprint test)

    For rpe/speed_kmh, returns tier-based defaults without athlete data.

    Args:
        client: Supabase client.
        athlete_id: Athlete UUID string.
        tier: One of 'foundation', 'intermediate', 'advanced'.
        intensity_type: One of 'rpe', 'speed_kmh', 'power_watts'.

    Returns:
        (min_val, max_val, source) where source describes where
        the reference value came from. Returns (None, None, 'missing')
        if no athlete data available for power-based resolution.
    """
    if tier not in TIER_RANGES:
        return (None, None, "invalid_tier")

    low_mult, high_mult = TIER_RANGES[tier]

    if intensity_type == "rpe":
        # RPE ranges are tier-based defaults (no athlete data needed)
        rpe_ranges: dict[str, tuple[float, float]] = {
            "foundation": (5.0, 6.0),
            "intermediate": (6.0, 8.0),
            "advanced": (8.0, 10.0),
        }
        min_val, max_val = rpe_ranges[tier]
        return (min_val, max_val, "default")

    if intensity_type == "speed_kmh":
        # Speed ranges are tier-based defaults
        speed_ranges: dict[str, tuple[float, float]] = {
            "foundation": (8.0, 12.0),
            "intermediate": (12.0, 16.0),
            "advanced": (16.0, 20.0),
        }
        min_val, max_val = speed_ranges[tier]
        return (min_val, max_val, "default")

    if intensity_type == "power_watts":
        reference_power, source = _get_reference_power(client, athlete_id)
        if reference_power is None:
            return (None, None, "missing")

        min_val = round(reference_power * low_mult, 1)
        max_val = round(reference_power * high_mult, 1)
        return (min_val, max_val, source)

    return (None, None, "unknown_type")


def _get_reference_power(
    client,
    athlete_id: str,
) -> tuple[Optional[float], str]:
    """Get reference power for an athlete.

    Resolution order:
      1. metabolic_profiles → sprint_1_avg_power_w
      2. air_bike_recordings → peak_power_w
      3. air_bike_sprints → power_7s

    Returns:
        (power_watts, source) or (None, 'missing').
    """
    # 1. Try metabolic profile (Ferretti protocol — most accurate)
    try:
        resp = (
            client.table("metabolic_profiles")
            .select("sprint_1_avg_power_w")
            .eq("athlete_id", athlete_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data and resp.data[0].get("sprint_1_avg_power_w") is not None:
            return (float(resp.data[0]["sprint_1_avg_power_w"]), "metabolic_profile")
    except Exception:
        logger.warning("Failed to query metabolic_profiles for athlete %s", athlete_id)

    # 2. Try BLE recording
    try:
        resp = (
            client.table("air_bike_recordings")
            .select("peak_power_w")
            .eq("athlete_id", athlete_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data and resp.data[0].get("peak_power_w") is not None:
            return (float(resp.data[0]["peak_power_w"]), "air_bike_recording")
    except Exception:
        logger.warning("Failed to query air_bike_recordings for athlete %s", athlete_id)

    # 3. Try air bike sprint test
    try:
        # Get latest test for this athlete
        test_resp = (
            client.table("air_bike_tests")
            .select("id")
            .eq("athlete_id", athlete_id)
            .order("test_date", desc=True)
            .limit(1)
            .execute()
        )
        if test_resp.data:
            test_id = test_resp.data[0]["id"]
            sprint_resp = (
                client.table("air_bike_sprints")
                .select("power_7s")
                .eq("test_id", test_id)
                .eq("sprint_number", 1)
                .limit(1)
                .execute()
            )
            if sprint_resp.data and sprint_resp.data[0].get("power_7s") is not None:
                return (float(sprint_resp.data[0]["power_7s"]), "air_bike_sprint")
    except Exception:
        logger.warning("Failed to query air_bike_sprints for athlete %s", athlete_id)

    return (None, "missing")
