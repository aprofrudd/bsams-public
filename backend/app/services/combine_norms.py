"""Boxing Science norm snapshots for a combine event.

The public board compares each boxer against Boxing Science norms, but the
`boxing_science` benchmark source in `analysis.py` is admin-gated and a public
request has no user at all. Rather than loosen that guard, an admin refreshes a
snapshot of `{score_key: {mean, sd, n}}` onto the event row; the public endpoint
then reads aggregates off a row it has already fetched — no extra query, and no
code path from an unauthenticated request to athlete data.

The event's own participants are excluded from the pool: 40 teenagers tested this
morning should not move the norms they are being measured against.

Each key carries a per-gender split as well as the pooled aggregate, and the split is
the only thing the board bands on — one mixed norm reads a strong 16-year-old girl as
DEVELOPING, in red, on a public wall.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.services.admin_pool import get_admin_athletes
from app.services.stat_engine import StatEngine

CHUNK_SIZE = 200

# PostgREST's default db-max-rows. Anything unpaginated is silently cut at this.
PAGE_SIZE = 1000

# The only genders an athlete record carries (schemas/enums.py).
GENDERS: Tuple[str, ...] = ("male", "female")

# Every score_key the engine looks up, so a missing one is a deliberate absence
SCORE_KEYS = (
    "height_cm",
    "pogo_rsi",
    "grip_best_kg",
    "trunk_rotation_best_kg",
    "landmine_velocity_ms",
    "air_bike_power_7s_wkg",
)


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return max(present) if present else None


def _gender(value: Any) -> Optional[str]:
    """An athlete's gender, normalised to the snapshot's keys, or None if unknown."""
    text = str(value or "").strip().lower()
    return text if text in GENDERS else None


def summarise(values: Sequence[float]) -> Optional[Dict[str, Any]]:
    """{mean, sd, n} for one score key, or None when there is nothing to summarise."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return {
        "mean": StatEngine.calculate_mean(vals),
        "sd": StatEngine.calculate_std_dev(vals),
        "n": len(vals),
    }


def norms_from_rows(
    *,
    events: Sequence[dict],
    vbt_sets: Sequence[dict],
    air_bike: Sequence[dict],
    gender_by_athlete: Dict[str, Optional[str]],
) -> Dict[str, Dict[str, Any]]:
    """Build the snapshot from already-fetched reference rows.

    Pure, so the aggregation is testable without Supabase. One value per athlete
    per key — their best — so an athlete tested ten times does not count ten times.
    Each key gets `by_gender` alongside the pooled aggregate; an athlete whose gender
    is not recorded counts in the pool but bands nobody.
    """
    per_athlete: Dict[str, Dict[str, List[float]]] = {}

    def add(athlete_id: str, key: str, value: Optional[float]) -> None:
        if value is None:
            return
        per_athlete.setdefault(athlete_id, {}).setdefault(key, []).append(value)

    for row in events:
        athlete_id = str(row.get("athlete_id"))
        metrics = row.get("metrics") or {}
        add(athlete_id, "height_cm", _num(metrics.get("height_cm")))
        add(athlete_id, "pogo_rsi", _num(metrics.get("pogo_rsi")))
        add(
            athlete_id,
            "grip_best_kg",
            _best(
                [
                    _num(metrics.get("grip_strength_left_kg")),
                    _num(metrics.get("grip_strength_right_kg")),
                ]
            ),
        )
        add(
            athlete_id,
            "trunk_rotation_best_kg",
            _best(
                [
                    _num(metrics.get("iso_trunk_rotation_left_kg")),
                    _num(metrics.get("iso_trunk_rotation_right_kg")),
                ]
            ),
        )

    for row in vbt_sets:
        add(str(row.get("athlete_id")), "landmine_velocity_ms", _num(row.get("velocity")))

    for row in air_bike:
        add(str(row.get("athlete_id")), "air_bike_power_7s_wkg", _num(row.get("wkg")))

    snapshot: Dict[str, Dict[str, Any]] = {}
    for key in SCORE_KEYS:
        pooled: List[float] = []
        by_gender: Dict[str, List[float]] = {gender: [] for gender in GENDERS}
        for athlete_id, values_by_key in per_athlete.items():
            values = values_by_key.get(key)
            if not values:
                continue
            best = max(values)
            pooled.append(best)
            gender = _gender(gender_by_athlete.get(athlete_id))
            if gender:
                by_gender[gender].append(best)

        summary = summarise(pooled)
        if not summary:
            continue
        split: Dict[str, Any] = {}
        for gender in GENDERS:
            per_gender = summarise(by_gender[gender])
            if per_gender:
                split[gender] = per_gender
        summary["by_gender"] = split
        snapshot[key] = summary
    return snapshot


def coverage_from_snapshot(snapshot: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """{score_key: {gender: n}} for the console — counts only.

    It tells an admin which bands are actually backed by enough athletes. A mean or an
    SD here would hand the reference distribution to anyone who can open the console.

    Every score key is reported, a key the pool could not summarise at all included,
    at zero. Leaving it out reads on screen exactly like a key that is fully covered,
    and a station with no norms is the one the admin most needs naming. A snapshot
    that was never refreshed reports nothing: the console already says so, and twelve
    zeroes beside "never refreshed" is noise, not a warning.
    """
    if not snapshot:
        return {}
    coverage: Dict[str, Dict[str, int]] = {}
    for key in SCORE_KEYS:
        by_gender = (snapshot.get(key) or {}).get("by_gender") or {}
        counts: Dict[str, int] = {}
        for gender in GENDERS:
            n = (by_gender.get(gender) or {}).get("n")
            valid = isinstance(n, (int, float)) and not isinstance(n, bool)
            counts[gender] = int(n) if valid else 0
        coverage[key] = counts
    return coverage


def fetch_all_rows(build_query: Callable[[], Any], page_size: int = PAGE_SIZE) -> List[dict]:
    """Every row of a select, not just the first page.

    PostgREST caps an unpaginated select at the project's db-max-rows (1000 by
    default) and says nothing about it, so a 40-boxer event logging both landmine
    sides would quietly lose attempts off the board. `build_query` must return a FRESH
    query each call — a builder that has already been ranged cannot be re-ranged.
    """
    rows: List[dict] = []
    start = 0
    while True:
        page = (
            build_query().order("id").range(start, start + page_size - 1).execute().data
            or []
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def _chunked_in(client, table: str, select: str, column: str, ids: Sequence[str]) -> List[dict]:
    """IN query, chunked to stay inside Supabase's URL limits and paged past db-max-rows."""
    out: List[dict] = []
    for i in range(0, len(ids), CHUNK_SIZE):
        chunk = list(ids[i : i + CHUNK_SIZE])
        if not chunk:
            continue
        out.extend(
            fetch_all_rows(
                lambda chunk=chunk: client.table(table).select(select).in_(column, chunk)
            )
        )
    return out


def compute_bs_norms(client, *, event: dict, exclude_athlete_ids: Set[str]) -> Dict[str, Any]:
    """Fetch the admin (Boxing Science) pool and summarise it into a snapshot."""
    pool = [
        a for a in get_admin_athletes(client) if str(a.get("id")) not in exclude_athlete_ids
    ]
    athlete_ids = [str(a["id"]) for a in pool]
    gender_by_athlete = {str(a["id"]): _gender(a.get("gender")) for a in pool}
    if not athlete_ids:
        return {}

    events = _chunked_in(
        client, "performance_events", "athlete_id, metrics", "athlete_id", athlete_ids
    )

    # Landmine: velocity at the reference load, from the profiles for this exercise
    exercise_name = event.get("landmine_exercise_name") or "Landmine Punch Throw"
    reference = _num(event.get("landmine_reference_load_kg")) or 0.0
    tolerance = _num(event.get("landmine_reference_tolerance_kg")) or 0.0
    metric = event.get("landmine_velocity_metric") or "peak"

    profiles = _chunked_in(
        client, "vbt_profiles", "id, athlete_id, exercise_name", "athlete_id", athlete_ids
    )
    # Promotion splits the two arms into "<exercise> (Left)" and "<exercise> (Right)";
    # the bare name only carries attempts logged before sides were captured. All three
    # are the same throw, and one best velocity per athlete comes out of the pooling.
    base_name = exercise_name.strip().lower()
    wanted_names = {base_name, f"{base_name} (left)", f"{base_name} (right)"}
    profile_by_id = {
        str(p["id"]): str(p["athlete_id"])
        for p in profiles
        if (p.get("exercise_name") or "").strip().lower() in wanted_names
    }
    vbt_rows: List[dict] = []
    if profile_by_id:
        sets = _chunked_in(
            client,
            "vbt_sets",
            "profile_id, load_kg, peak_velocity_ms, mean_velocity_ms",
            "profile_id",
            list(profile_by_id),
        )
        # Only the metric the event ranks on: peak and mean are different numbers, and
        # a norm built from a mix of them bands nobody correctly.
        primary = "peak_velocity_ms" if metric == "peak" else "mean_velocity_ms"
        for row in sets:
            load = _num(row.get("load_kg"))
            if load is None or abs(load - reference) > tolerance:
                continue
            velocity = _num(row.get(primary))
            if velocity is None:
                continue
            vbt_rows.append(
                {"athlete_id": profile_by_id[str(row["profile_id"])], "velocity": velocity}
            )

    # Air bike: peak 7s power per kilogram
    tests = _chunked_in(
        client, "air_bike_tests", "id, athlete_id, body_mass_kg", "athlete_id", athlete_ids
    )
    test_meta = {
        str(t["id"]): (str(t["athlete_id"]), _num(t.get("body_mass_kg"))) for t in tests
    }
    air_rows: List[dict] = []
    if test_meta:
        sprints = _chunked_in(
            client, "air_bike_sprints", "test_id, power_7s", "test_id", list(test_meta)
        )
        for row in sprints:
            meta = test_meta.get(str(row.get("test_id")))
            if not meta:
                continue
            athlete_id, mass = meta
            power = _num(row.get("power_7s"))
            if power is None or mass is None or mass <= 0:
                continue
            air_rows.append({"athlete_id": athlete_id, "wkg": round(power / mass, 2)})

    return norms_from_rows(
        events=events,
        vbt_sets=vbt_rows,
        air_bike=air_rows,
        gender_by_athlete=gender_by_athlete,
    )
