"""Training block engine.

Handles percentage-based load resolution for training blocks.
Resolves percent_1rm values to absolute weight_kg per athlete
using recorded maxes (athlete_maxes).
"""

from typing import Optional


def serialize_exercises(exercises: list) -> list[dict]:
    """Serialize exercise models to JSONB-ready dicts, filtering None values.

    Args:
        exercises: List of Pydantic exercise models.

    Returns:
        List of dicts with None values removed.
    """
    return [
        {k: v for k, v in ex.model_dump().items() if v is not None}
        for ex in exercises
    ]


def filter_none(d: dict) -> dict:
    """Filter None values from a dict.

    Args:
        d: Input dictionary.

    Returns:
        New dict with None values removed.
    """
    return {k: v for k, v in d.items() if v is not None}


def format_athlete_name(athlete: dict) -> str:
    """Format athlete name from first_name + surname.

    Args:
        athlete: Dict with first_name and surname keys.

    Returns:
        Formatted full name string.
    """
    return f"{athlete.get('first_name', '')} {athlete.get('surname', '')}".strip()


def round_to_plate(kg: float, increment: float = 2.5) -> float:
    """Round weight to nearest plate increment.

    Args:
        kg: Weight in kilograms.
        increment: Plate increment (default 2.5 kg).

    Returns:
        Weight rounded to nearest increment.
    """
    if increment <= 0:
        return round(kg, 1)
    return round(kg / increment) * increment


def resolve_percent_1rm(
    client,
    athlete_id: str,
    exercise_name: str,
    percent_1rm: float,
) -> tuple[Optional[float], str]:
    """Resolve percent_1rm to absolute weight for an athlete.

    Looks up the athlete's recorded max in the athlete_maxes table.

    Args:
        client: Supabase client.
        athlete_id: Athlete UUID string.
        exercise_name: Exercise name to look up.
        percent_1rm: Percentage of 1RM (0-100).

    Returns:
        (weight_kg, source) where source is 'manual' or 'missing'.
        weight_kg is None if no 1RM data available.
    """
    manual_1rm = _resolve_from_maxes(client, athlete_id, exercise_name)
    if manual_1rm is not None:
        weight = round_to_plate(manual_1rm * percent_1rm / 100)
        return (weight, "manual")

    return (None, "missing")


def get_athlete_1rm(
    client,
    athlete_id: str,
    exercise_name: str,
) -> tuple[Optional[float], str]:
    """Get the current 1RM for an athlete + exercise.

    Same resolution order as resolve_percent_1rm but returns the raw 1RM.

    Returns:
        (max_1rm_kg, source) where source is 'manual' or 'missing'.
    """
    manual_1rm = _resolve_from_maxes(client, athlete_id, exercise_name)
    if manual_1rm is not None:
        return (manual_1rm, "manual")

    return (None, "missing")


def _resolve_from_maxes(
    client,
    athlete_id: str,
    exercise_name: str,
) -> Optional[float]:
    """Resolve 1RM from athlete_maxes table.

    Returns max_kg or None.
    """
    max_resp = (
        client.table("athlete_maxes")
        .select("max_kg")
        .eq("athlete_id", athlete_id)
        .ilike("exercise_name", exercise_name)
        .limit(1)
        .execute()
    )
    if not max_resp.data:
        return None

    return float(max_resp.data[0]["max_kg"])
