"""Combine leaderboard engine.

Reduces every logged attempt to one ranked scalar per station, then builds the
board: per-station bests, cohort statistics, within-cohort z-scores, comparison
bands against the Boxing Science norms, and the composite Combine Score — a
T-score over those z-scores, or a percentile composite, per the event's setting.

`build_leaderboard` is a PURE function — all database I/O happens in the router.
That is what makes the ranking maths unit-testable without a Supabase mock.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services.stat_engine import StatEngine

# Station keys, in the order they appear on the big screen.
STATIONS: Tuple[str, ...] = (
    "cmj",
    "pogo",
    "landmine",
    "grip",
    "trunk_rotation",
    "air_bike",
)

# A Boxing Science norm below this sample size is not shown — too few athletes to
# say anything meaningful about a 15-year-old's result.
MIN_BS_NORM_N = 20

# Filtering to a weight category can leave a handful of boxers; z-scores over three
# people are noise, so below this the panel falls back to whole-event statistics.
MIN_FILTERED_COHORT_N = 5

# Combine Score is a T-score: 50 is the room's average, 10 points is one SD.
SCORE_CENTRE = 50.0
SCORE_SCALE = 10.0


@dataclass(frozen=True)
class StationSpec:
    """How one station is labelled, ranked and compared."""

    station: str
    label: str
    short_label: str
    unit: str
    higher_is_better: bool
    score_key: str  # key into the event's bs_norms_snapshot
    decimals: int


STATION_SPECS: Dict[str, StationSpec] = {
    "cmj": StationSpec("cmj", "Countermovement Jump", "CMJ", "cm", True, "height_cm", 1),
    "pogo": StationSpec("pogo", "10-5 Pogo (RSI)", "Pogo", "", True, "pogo_rsi", 2),
    "landmine": StationSpec(
        "landmine", "Landmine Punch", "Punch", "m/s", True, "landmine_velocity_ms", 2
    ),
    "grip": StationSpec("grip", "Grip Strength", "Grip", "kg", True, "grip_best_kg", 1),
    "trunk_rotation": StationSpec(
        "trunk_rotation", "Trunk Rotation", "Rotation", "kg", True, "trunk_rotation_best_kg", 1
    ),
    "air_bike": StationSpec(
        "air_bike", "Air Bike Power", "Bike", "W/kg", True, "air_bike_power_7s_wkg", 2
    ),
}


@dataclass
class AttemptValue:
    """One attempt reduced to the single number the leaderboard ranks on."""

    attempt_id: str
    participant_id: str
    station: str
    attempt_number: int
    primary: float
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeaderboardFilters:
    """Optional narrowing of the displayed cohort."""

    weight_category: Optional[str] = None
    age_group: Optional[str] = None
    club: Optional[str] = None
    squad: Optional[str] = None

    def is_active(self) -> bool:
        return any([self.weight_category, self.age_group, self.club, self.squad])

    def matches(self, participant: dict) -> bool:
        for attr in ("weight_category", "age_group", "club", "squad"):
            wanted = getattr(self, attr)
            if wanted and (participant.get(attr) or "") != wanted:
                return False
        return True


# ---------------------------------------------------------------------------
# Scalar reduction — one attempt in, one ranked number out
# ---------------------------------------------------------------------------


def _num(value: Any) -> Optional[float]:
    """Coerce a JSONB value to float. PostgREST hands NUMERIC back as a string."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def asymmetry_pct(left: Optional[float], right: Optional[float]) -> Optional[float]:
    """Left/right imbalance as a percentage of the stronger side."""
    if left is None or right is None:
        return None
    stronger = max(left, right)
    if stronger <= 0:
        return None
    return round(abs(left - right) / stronger * 100, 1)


def _bilateral(measures: dict, spec: StationSpec) -> Optional[AttemptValue]:
    """Shared reduction for grip and trunk rotation: rank the better side."""
    left = _num(measures.get("left_kg"))
    right = _num(measures.get("right_kg"))
    sides = [v for v in (left, right) if v is not None]
    if not sides:
        return None
    best = max(sides)
    detail: Dict[str, Any] = {
        "left_kg": left,
        "right_kg": right,
        "asymmetry_pct": asymmetry_pct(left, right),
        "dominant_side": None,
    }
    if left is not None and right is not None and left != right:
        detail["dominant_side"] = "left" if left > right else "right"
    for key in ("rfd_left_n_s", "rfd_right_n_s"):
        value = _num(measures.get(key))
        if value is not None:
            detail[key] = value
    return AttemptValue("", "", spec.station, 0, best, detail)


def score_attempt(
    attempt: dict,
    *,
    participant: dict,
    event: dict,
) -> Optional[AttemptValue]:
    """Reduce one attempt row to its ranked scalar.

    Returns None when the attempt cannot be ranked — a landmine throw at a load
    other than the reference load, or an air bike sprint with no body mass to
    scale by. Those attempts are still stored; they just don't sit on the board.
    """
    station = attempt.get("station")
    spec = STATION_SPECS.get(station)
    if spec is None:
        return None
    measures = attempt.get("measures") or {}

    value: Optional[float] = None
    detail: Dict[str, Any] = {}

    if station == "cmj":
        value = _num(measures.get("height_cm"))

    elif station == "pogo":
        flight = _num(measures.get("flight_time_ms"))
        contact = _num(measures.get("contact_time_ms"))
        # Derive from the pair whenever it is there: that is what the operator
        # measured, and a typed RSI disagreeing with it on the board is worse than
        # either number on its own. A typed value still covers a missing pair.
        if flight is not None and contact is not None and contact > 0:
            value = round(flight / contact, 3)
        else:
            value = _num(measures.get("rsi"))
        detail = {"flight_time_ms": flight, "contact_time_ms": contact}

    elif station == "landmine":
        load = _num(measures.get("load_kg"))
        reference = _num(event.get("landmine_reference_load_kg"))
        tolerance = _num(event.get("landmine_reference_tolerance_kg"))
        tolerance = 0.0 if tolerance is None else tolerance
        if load is None or reference is None or abs(load - reference) > tolerance:
            return None  # a valid throw, but not at the load the board compares
        metric = event.get("landmine_velocity_metric") or "peak"
        primary_key = "peak_velocity_ms" if metric == "peak" else "mean_velocity_ms"
        # No fallback to the other metric: peak and mean are different numbers, and a
        # board that ranks a mix of them puts a wrong order on the wall.
        value = _num(measures.get(primary_key))
        detail = {
            "load_kg": load,
            "peak_velocity_ms": _num(measures.get("peak_velocity_ms")),
            "mean_velocity_ms": _num(measures.get("mean_velocity_ms")),
            "side": measures.get("side"),
        }

    elif station in ("grip", "trunk_rotation"):
        reduced = _bilateral(measures, spec)
        if reduced is None:
            return None
        value, detail = reduced.primary, reduced.detail

    elif station == "air_bike":
        power = _num(measures.get("power_7s"))
        if power is None:
            return None
        detail = {
            "sprint_number": measures.get("sprint_number"),
            "power_7s": power,
            "power_17s": _num(measures.get("power_17s")),
            "power_27s": _num(measures.get("power_27s")),
            "absolute_w": power,
        }
        # Always per kilogram, whatever the basis column says. `absolute_w` is gone
        # from the API, and a stray pre-034 row must not score watts against a W/kg
        # norm — that reads ELITE for everyone and labels watts "W/kg" on the wall.
        mass = _num(participant.get("body_mass_kg")) or _num(measures.get("body_mass_kg"))
        if mass is None or mass <= 0:
            return None  # no body mass, so W/kg is undefined
        value = round(power / mass, 2)
        detail["body_mass_kg"] = mass

    if value is None:
        return None

    return AttemptValue(
        attempt_id=str(attempt.get("id") or ""),
        participant_id=str(attempt.get("participant_id") or ""),
        station=station,
        attempt_number=int(attempt.get("attempt_number") or 0),
        primary=value,
        detail=detail,
    )


def best_per_participant(
    attempts: Sequence[dict],
    *,
    participants_by_id: Dict[str, dict],
    event: dict,
) -> Dict[str, Dict[str, AttemptValue]]:
    """{participant_id: {station: best attempt}}.

    Voided attempts, withdrawn participants and unrankable attempts are skipped.
    """
    bests: Dict[str, Dict[str, AttemptValue]] = {}
    for attempt in attempts:
        if attempt.get("voided_at"):
            continue
        participant_id = str(attempt.get("participant_id") or "")
        participant = participants_by_id.get(participant_id)
        if participant is None or participant.get("withdrawn_at"):
            continue
        scored = score_attempt(attempt, participant=participant, event=event)
        if scored is None:
            continue
        spec = STATION_SPECS[scored.station]
        current = bests.setdefault(participant_id, {}).get(scored.station)
        if current is None:
            bests[participant_id][scored.station] = scored
        elif spec.higher_is_better:
            if scored.primary > current.primary:
                bests[participant_id][scored.station] = scored
        elif scored.primary < current.primary:
            bests[participant_id][scored.station] = scored
    return bests


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def cohort_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    """n, mean, median, sd, min, max for one station's bests."""
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "sd": None, "min": None, "max": None}
    return {
        "n": len(vals),
        "mean": StatEngine.calculate_mean(vals),
        "median": StatEngine.calculate_median(vals),
        "sd": StatEngine.calculate_std_dev(vals),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
    }


def rank_values(
    values_by_participant: Dict[str, float], higher_is_better: bool
) -> Dict[str, int]:
    """Competition ranking — equal values share a rank and the next rank skips.

    [10, 10, 8] ranks as {1, 1, 3}.
    """
    ordered = sorted(
        values_by_participant.items(), key=lambda kv: kv[1], reverse=higher_is_better
    )
    ranks: Dict[str, int] = {}
    previous_value: Optional[float] = None
    previous_rank = 0
    for index, (participant_id, value) in enumerate(ordered, start=1):
        if previous_value is not None and value == previous_value:
            ranks[participant_id] = previous_rank
        else:
            ranks[participant_id] = index
            previous_rank = index
            previous_value = value
    return ranks


def cohort_z(value: float, stats: Dict[str, Optional[float]], higher_is_better: bool) -> float:
    """Within-cohort z, signed so that better is always positive.

    StatEngine returns 0.0 when SD is 0, which is the right answer while the first
    couple of boxers are still going through a station.
    """
    mean = stats.get("mean")
    sd = stats.get("sd")
    if mean is None or sd is None:
        return 0.0
    z = StatEngine.calculate_z_score(value, mean, sd)
    return z if higher_is_better else -z


def gender_norm(
    norm: Optional[Dict[str, Any]], gender: Optional[str]
) -> Optional[Dict[str, Any]]:
    """The boxer's own gender entry from a snapshot norm, or None.

    Never the pooled entry. One mixed norm reads a strong 16-year-old girl as
    DEVELOPING, in red, on a public wall. A snapshot taken before the split has no
    `by_gender`, so bands stay off there until an admin refreshes them.
    """
    if not norm or not gender:
        return None
    by_gender = norm.get("by_gender") or {}
    return by_gender.get(str(gender).strip().lower()) or None


def bs_z(
    value: float,
    norm: Optional[Dict[str, Any]],
    *,
    gender: Optional[str] = None,
    higher_is_better: bool = True,
    min_n: int = MIN_BS_NORM_N,
) -> Optional[float]:
    """Z against the boxer's gender-matched Boxing Science norm, or None."""
    matched = gender_norm(norm, gender)
    if not matched:
        return None
    n = matched.get("n")
    mean = _num(matched.get("mean"))
    sd = _num(matched.get("sd"))
    if n is None or int(n) < min_n or mean is None or sd is None or sd == 0:
        return None
    z = StatEngine.calculate_z_score(value, mean, sd)
    return z if higher_is_better else -z


def bs_band(z: Optional[float]) -> Optional[str]:
    """A four-level band instead of a number.

    Publishing a numeric z next to the raw value for a whole cohort would let anyone
    solve for the Boxing Science mean and SD. A band is not invertible — and it reads
    better on a wall.
    """
    if z is None:
        return None
    if z >= 1.0:
        return "elite"
    if z >= 0.25:
        return "above_average"
    if z >= -0.75:
        return "average"
    return "developing"


def combine_score(
    station_zs: Dict[str, float]
) -> Optional[Tuple[float, float, int]]:
    """(score, mean_z, stations_completed) from the stations a boxer has done.

    Missing stations are ignored rather than counted as zero, so someone who has
    only reached three stations is not punished for the timetable.
    """
    zs = [z for z in station_zs.values() if z is not None]
    if not zs:
        return None
    mean_z = sum(zs) / len(zs)
    score = SCORE_CENTRE + SCORE_SCALE * mean_z
    score = max(0.0, min(100.0, score))
    return round(score, 1), round(mean_z, 3), len(zs)


def station_percentiles(
    values_by_participant: Dict[str, float], higher_is_better: bool
) -> Dict[str, float]:
    """Each participant's share of the rest of the displayed cohort they beat, 0-100.

    Tied values take the midpoint of the positions they span, which is the same thing
    as counting each tie as half a win. The best of a clean spread scores 100 and the
    worst 0; a single participant has beaten nobody and lost to nobody, so they sit at
    50 until someone else finishes the station.

    Unrounded on purpose — this is working state. Only the composite it feeds is
    published, and that is rounded there, the way `cohort_z` is rounded at the row.
    """
    count = len(values_by_participant)
    if count == 0:
        return {}
    if count == 1:
        return {pid: 50.0 for pid in values_by_participant}

    # Worst first, so a position is the number of boxers beaten.
    ordered = sorted(
        values_by_participant.items(), key=lambda kv: kv[1], reverse=not higher_is_better
    )
    percentiles: Dict[str, float] = {}
    start = 0
    while start < len(ordered):
        stop = start
        while stop + 1 < len(ordered) and ordered[stop + 1][1] == ordered[start][1]:
            stop += 1
        share = ((start + stop) / 2) / (count - 1) * 100
        for participant_id, _ in ordered[start : stop + 1]:
            percentiles[participant_id] = share
        start = stop + 1
    return percentiles


def percentile_score(percentiles_by_station: Dict[str, float]) -> Optional[float]:
    """The percentile composite: the mean over the stations a boxer has completed.

    Missing stations are ignored rather than counted as zero, exactly as
    `combine_score` does — nobody is punished for where the timetable put them.
    """
    percentiles = [p for p in percentiles_by_station.values() if p is not None]
    if not percentiles:
        return None
    return round(sum(percentiles) / len(percentiles), 1)


def overall_basis(event: dict) -> str:
    """Which composite this event's Combine Score uses.

    Anything unrecognised — including a row written before the column existed — reads
    as 'z'. Switching the basis is a deliberate act by the operator; nothing else,
    least of all a missing column, may switch it on their behalf.
    """
    basis = event.get("overall_score_basis")
    return basis if basis in ("z", "percentile") else "z"


# ---------------------------------------------------------------------------
# Orchestration (pure)
# ---------------------------------------------------------------------------


def display_name(participant: dict, style: str) -> str:
    """Render a roster name for the requested privacy level."""
    bib = participant.get("bib")
    if style == "bib":
        return f"#{bib}" if bib is not None else "—"
    first = (participant.get("first_name") or "").strip()
    surname = (participant.get("surname") or "").strip()
    if not first and not surname:
        full = (participant.get("name") or "").strip()
        parts = full.split()
        first = parts[0] if parts else ""
        surname = parts[-1] if len(parts) > 1 else ""
    if style == "first_only":
        return first or (f"#{bib}" if bib is not None else "—")
    if style == "first_initial":
        initial = f" {surname[0]}." if surname else ""
        return f"{first}{initial}".strip() or (f"#{bib}" if bib is not None else "—")
    return " ".join(p for p in (first, surname) if p) or (f"#{bib}" if bib is not None else "—")


def build_leaderboard(
    *,
    event: dict,
    participants: Sequence[dict],
    attempts: Sequence[dict],
    filters: Optional[LeaderboardFilters] = None,
    public: bool = False,
) -> Dict[str, Any]:
    """Assemble the whole board. No I/O — everything is passed in."""
    filters = filters or LeaderboardFilters()
    name_style = (event.get("public_name_style") or "full") if public else "full"
    show_club = bool(event.get("show_club", True)) if public else True
    show_bs = bool(event.get("show_bs_benchmark", True))
    norms = event.get("bs_norms_snapshot") or {}
    enabled_stations = [s for s in STATIONS if s in STATION_SPECS]

    if public and not show_club and filters.club:
        # Narrowing by a club the board does not show would let anyone enumerate
        # which named minors box for it.
        filters = replace(filters, club=None)

    active = [p for p in participants if not p.get("withdrawn_at")]
    participants_by_id = {str(p["id"]): p for p in active}
    # An ordered list, not a set: tied rows keep insertion order, and a set of random
    # uuids iterates in whatever the worker's hash seed says, so tied boxers would
    # swap places between polls.
    displayed = [p for p in active if filters.matches(p)]
    displayed_ids = [str(p["id"]) for p in displayed]

    bests = best_per_participant(
        attempts, participants_by_id=participants_by_id, event=event
    )

    # One pass for every row's attempt count, rather than a scan of every attempt per row.
    attempt_counts = Counter(
        (str(a.get("participant_id")), a.get("station"))
        for a in attempts
        if not a.get("voided_at")
    )

    panels: List[Dict[str, Any]] = []
    z_by_participant: Dict[str, Dict[str, float]] = {pid: {} for pid in displayed_ids}
    percentile_by_participant: Dict[str, Dict[str, float]] = {
        pid: {} for pid in displayed_ids
    }

    for station in enabled_stations:
        spec = STATION_SPECS[station]

        # Rank the number the board shows: two pogo throws that both display 2.50
        # must share first place, not be separated at the third decimal.
        displayed_values = {
            pid: round(bests[pid][station].primary, spec.decimals)
            for pid in displayed_ids
            if station in bests.get(pid, {})
        }
        stats = cohort_stats(list(displayed_values.values()))
        cohort_basis = "filtered" if filters.is_active() else "event"

        # A three-person filter produces meaningless z-scores, so fall back to the
        # whole room and say so.
        if filters.is_active() and (stats["n"] or 0) < MIN_FILTERED_COHORT_N:
            all_values = [
                round(bests[pid][station].primary, spec.decimals)
                for pid in participants_by_id
                if station in bests.get(pid, {})
            ]
            if len(all_values) > (stats["n"] or 0):
                stats = cohort_stats(all_values)
                cohort_basis = "event"

        ranks = rank_values(displayed_values, spec.higher_is_better)
        # Over the displayed cohort, like the ranks beside them. The z path widens to
        # the whole room when a filter leaves too few to z-score against; a percentile
        # needs no such rescue, being a position among the boxers on screen.
        for pid, percentile in station_percentiles(
            displayed_values, spec.higher_is_better
        ).items():
            percentile_by_participant.setdefault(pid, {})[station] = percentile

        rows: List[Dict[str, Any]] = []
        for pid, value in displayed_values.items():
            participant = participants_by_id[pid]
            attempt = bests[pid][station]
            z = cohort_z(value, stats, spec.higher_is_better)
            z_by_participant.setdefault(pid, {})[station] = z

            norm_z = (
                bs_z(
                    value,
                    norms.get(spec.score_key),
                    gender=participant.get("gender"),
                    higher_is_better=spec.higher_is_better,
                )
                if show_bs
                else None
            )
            band = bs_band(norm_z)
            if public and ranks.get(pid) != 1:
                # Only the leader is banded in public. A band beside every raw value
                # lets the fixed thresholds bracket the Boxing Science mean and SD.
                band = None

            row: Dict[str, Any] = {
                "bib": participant.get("bib"),
                "display_name": display_name(participant, name_style),
                "weight_category": participant.get("weight_category"),
                "age_group": participant.get("age_group"),
                "value": round(value, spec.decimals),
                "display_value": f"{value:.{spec.decimals}f}{(' ' + spec.unit) if spec.unit else ''}",
                "rank": ranks.get(pid),
                "attempts": attempt_counts.get((pid, station), 0),
                "z_cohort": round(z, 2),
                "bs_band": band,
                "asymmetry_pct": attempt.detail.get("asymmetry_pct"),
                "dominant_side": attempt.detail.get("dominant_side"),
                # Landmine only: which arm threw the ranked best.
                "side": attempt.detail.get("side"),
            }
            if show_club:
                row["club"] = participant.get("club")
            if not public:
                # Identifiers and the raw benchmark z stay on the authenticated board.
                row["participant_id"] = pid
                row["athlete_id"] = participant.get("athlete_id")
                row["z_bs"] = round(norm_z, 2) if norm_z is not None else None
                row["detail"] = attempt.detail
            rows.append(row)

        # Bib then name after rank, so tied rows hold one order across every poll.
        rows.sort(
            key=lambda r: (
                r["rank"] is None,
                r["rank"] or 0,
                r["bib"] is None,
                r["bib"] or 0,
                r["display_name"],
            )
        )

        panels.append(
            {
                "station": station,
                "label": spec.label,
                "short_label": spec.short_label,
                "unit": spec.unit,
                "decimals": spec.decimals,
                "higher_is_better": spec.higher_is_better,
                "cohort_basis": cohort_basis,
                "completed": len(displayed_values),
                "stats": stats,
                "results": rows,
            }
        )

    min_stations = int(event.get("min_stations_for_overall") or 1)
    basis = overall_basis(event)
    overall_by_pid: Dict[str, Dict[str, Any]] = {}
    for pid in displayed_ids:
        scored = combine_score(z_by_participant.get(pid, {}))
        if scored is None:
            continue
        score, mean_z, completed = scored
        if basis == "percentile":
            # The same stations and the same eligibility — a different number in the
            # same place. Guarded rather than assumed: a board that cannot compute a
            # percentile falls back to the T-score instead of publishing nothing.
            percentile = percentile_score(percentile_by_participant.get(pid, {}))
            if percentile is not None:
                score = percentile
        participant = participants_by_id[pid]
        entry: Dict[str, Any] = {
            "bib": participant.get("bib"),
            "display_name": display_name(participant, name_style),
            "weight_category": participant.get("weight_category"),
            "combine_score": score,
            "stations_completed": completed,
            # Below the threshold a boxer still appears, but unranked — they read as
            # "3/6, not yet ranked" rather than vanishing from the board.
            "eligible": completed >= min_stations,
            "rank": None,
        }
        if show_club:
            entry["club"] = participant.get("club")
        if not public:
            entry["participant_id"] = pid
            entry["mean_z"] = mean_z
        overall_by_pid[pid] = entry

    eligible_scores = {
        pid: e["combine_score"] for pid, e in overall_by_pid.items() if e["eligible"]
    }
    overall_ranks = rank_values(eligible_scores, True)
    for pid, entry in overall_by_pid.items():
        entry["rank"] = overall_ranks.get(pid)

    overall_raw = sorted(
        overall_by_pid.values(),
        key=lambda e: (
            not e["eligible"],
            e["rank"] is None,
            e["rank"] or 0,
            -e["combine_score"],
            e["bib"] is None,
            e["bib"] or 0,
            e["display_name"],
        ),
    )

    return {
        "event_name": event.get("event_name"),
        "event_date": event.get("event_date"),
        "venue": event.get("venue"),
        "results_updated_at": event.get("results_updated_at"),
        "participant_count": len(displayed),
        # The board has to label the number it is showing.
        "score_basis": basis,
        "filters": _available_filters(active, show_club=show_club),
        "stations": panels,
        "overall": overall_raw,
    }


def _available_filters(
    participants: Sequence[dict], *, show_club: bool = True
) -> Dict[str, List[str]]:
    """The filter chips the board can offer, drawn from the roster itself.

    When clubs are hidden the club list is withheld too — otherwise switching the
    per-row club off would still publish every club that turned up.
    """
    keys = ["weight_category", "age_group", "squad"]
    if show_club:
        keys.insert(2, "club")
    out: Dict[str, List[str]] = {}
    for key in keys:
        values = sorted({p[key] for p in participants if p.get(key)})
        if values:
            out[key] = values
    return out
