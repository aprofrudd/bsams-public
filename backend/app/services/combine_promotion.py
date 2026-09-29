"""Promote combine attempts into the real athlete tables.

Attempts are the authoritative log: every jump, every throw, every sprint, with
soft-void for corrections. This module writes the *best* of them into the tables
the rest of BSAMS reads, tagged with `combine_event_id`, so combine results show
up in athlete history, test reports, benchmarks and the GDPR export with no
special-casing anywhere else.

Exactly one `performance_events` row exists per athlete per combine (enforced by a
partial unique index in migration 033). That is deliberate: `analysis.py` builds
cohort benchmarks from *all* events for the reference athletes, so writing one row
per attempt would weight the squad mean by however many jumps each boxer took.

Ownership: every read, write and delete here is scoped to `combine_event_id`. The
side tables are unique per athlete per day, so an athlete tested by their own coach
on the morning of the combine has a row this module must not touch — and a void
would otherwise delete real data that no re-sync can bring back.

Concurrency: the hot path (a station saving an attempt) writes only the station it
just saved, merging that station's keys through the `combine_upsert_event_metrics`
RPC, which is atomic across the two uvicorn workers. Two iPads on two stations then
cannot roll each other's best back. The cold path (a void, a correction or
`POST /sync`) recomputes every station and replaces the row, which is the only way
to clear keys for a station whose every attempt has been voided.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from app.services.combine_engine import STATION_SPECS, best_per_participant, score_attempt

logger = logging.getLogger("bsams")

# Station -> the metric-registry keys it writes into performance_events.metrics
EVENT_METRIC_KEYS: Dict[str, Tuple[str, ...]] = {
    "cmj": ("height_cm",),
    "pogo": ("pogo_flight_time_ms", "pogo_contact_time_ms", "pogo_rsi"),
    "grip": (
        "grip_strength_left_kg",
        "grip_strength_right_kg",
        "grip_rfd_left_n_s",
        "grip_rfd_right_n_s",
    ),
    "trunk_rotation": (
        "iso_trunk_rotation_left_kg",
        "iso_trunk_rotation_right_kg",
        "iso_trunk_rotation_rfd_left_n_s",
        "iso_trunk_rotation_rfd_right_n_s",
    ),
}

# Stations that land somewhere other than performance_events
STATIONS_WITH_OWN_TABLE = ("landmine", "air_bike")

# What promotion writes, and the names a failure is reported under.
PROMOTION_TARGETS: Tuple[str, ...] = ("event_metrics", "landmine", "air_bike")

# Postgres unique_violation.
UNIQUE_VIOLATION = "23505"

# One profile per side, so the two arms never average into a single load-velocity
# line. Attempts logged before sides were captured carry none and keep the bare name.
LANDMINE_PROFILE_SIDES: Tuple[Tuple[Optional[str], str], ...] = (
    ("left", " (Left)"),
    ("right", " (Right)"),
    (None, ""),
)


def _clean(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Drop None values — the metric validator only accepts numbers."""
    return {k: v for k, v in metrics.items() if v is not None}


def build_event_metrics(
    bests: Dict[str, Any],
    *,
    stations: Sequence[str] = tuple(EVENT_METRIC_KEYS),
) -> Dict[str, Any]:
    """Metric JSONB for one athlete, from their best attempt at each JSONB station."""
    metrics: Dict[str, Any] = {}

    if "cmj" in stations and "cmj" in bests:
        metrics["height_cm"] = bests["cmj"].primary

    if "pogo" in stations and "pogo" in bests:
        best = bests["pogo"]
        metrics["pogo_rsi"] = best.primary
        metrics["pogo_flight_time_ms"] = best.detail.get("flight_time_ms")
        metrics["pogo_contact_time_ms"] = best.detail.get("contact_time_ms")

    if "grip" in stations and "grip" in bests:
        detail = bests["grip"].detail
        metrics["grip_strength_left_kg"] = detail.get("left_kg")
        metrics["grip_strength_right_kg"] = detail.get("right_kg")
        metrics["grip_rfd_left_n_s"] = detail.get("rfd_left_n_s")
        metrics["grip_rfd_right_n_s"] = detail.get("rfd_right_n_s")

    if "trunk_rotation" in stations and "trunk_rotation" in bests:
        detail = bests["trunk_rotation"].detail
        metrics["iso_trunk_rotation_left_kg"] = detail.get("left_kg")
        metrics["iso_trunk_rotation_right_kg"] = detail.get("right_kg")
        metrics["iso_trunk_rotation_rfd_left_n_s"] = detail.get("rfd_left_n_s")
        metrics["iso_trunk_rotation_rfd_right_n_s"] = detail.get("rfd_right_n_s")

    return _clean(metrics)


def build_landmine_sets(
    attempts: Sequence[dict], *, metric: str = "peak", side: Optional[str] = None
) -> List[Dict[str, Any]]:
    """One VBT set per distinct load for one side — the best velocity at that load.

    Unlike the leaderboard, this keeps every load, not only the reference one: the
    whole point of storing it as a VBT profile is that the load-velocity line is
    useful afterwards. `side=None` collects only the attempts logged without a side.
    """
    primary_key = "peak_velocity_ms" if metric == "peak" else "mean_velocity_ms"
    by_load: Dict[float, Dict[str, Any]] = {}

    for attempt in attempts:
        if attempt.get("voided_at") or attempt.get("station") != "landmine":
            continue
        measures = attempt.get("measures") or {}
        if (measures.get("side") or None) != side:
            continue
        try:
            load = float(measures.get("load_kg"))
        except (TypeError, ValueError):
            continue
        if load <= 0:
            continue
        peak = measures.get("peak_velocity_ms")
        mean = measures.get("mean_velocity_ms")
        ranked = measures.get(primary_key)
        if ranked is None:
            ranked = peak if peak is not None else mean
        if ranked is None:
            continue
        current = by_load.get(load)
        if current is None or float(ranked) > current["_ranked"]:
            by_load[load] = {
                "_ranked": float(ranked),
                "load_kg": load,
                "peak_velocity_ms": float(peak) if peak is not None else None,
                "mean_velocity_ms": float(mean) if mean is not None else None,
            }

    sets: List[Dict[str, Any]] = []
    for index, load in enumerate(sorted(by_load), start=1):
        row = dict(by_load[load])
        row.pop("_ranked")
        row["set_number"] = index
        sets.append(row)
    return sets


def build_air_bike_sprints(attempts: Sequence[dict]) -> List[Dict[str, Any]]:
    """Best effort per sprint number, ranked on 7s power."""
    by_sprint: Dict[int, Dict[str, Any]] = {}
    for attempt in attempts:
        if attempt.get("voided_at") or attempt.get("station") != "air_bike":
            continue
        measures = attempt.get("measures") or {}
        try:
            sprint_number = int(measures.get("sprint_number"))
            power_7s = float(measures.get("power_7s"))
        except (TypeError, ValueError):
            continue
        if sprint_number not in (1, 2):
            continue
        current = by_sprint.get(sprint_number)
        if current is None or power_7s > current["power_7s"]:
            by_sprint[sprint_number] = {
                "sprint_number": sprint_number,
                "power_7s": power_7s,
                "power_17s": measures.get("power_17s"),
                "power_27s": measures.get("power_27s"),
                "blood_lactate_mmol": measures.get("blood_lactate_mmol"),
            }
    return [by_sprint[n] for n in sorted(by_sprint)]


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def promote_participant(
    client,
    *,
    event: dict,
    participant: dict,
    attempts: Sequence[dict],
    merge: bool = True,
    station: Optional[str] = None,
) -> List[str]:
    """Write this participant's bests into the real tables.

    `merge=True` with a `station` is the station-save path: only that station is
    written, and only its keys are merged, atomically. `merge=False` rebuilds every
    station, which is what a void, a correction or a manual sync needs so that a
    station with no surviving attempts is cleared.

    Never raises — a promotion failure must not lose the attempt, which is already
    safely stored. Returns the targets that could not be written (names from
    `PROMOTION_TARGETS`); empty means everything landed. `POST /sync` repairs the
    drift, and the count reaches the console so a failure shows up on the day rather
    than at the end of it.
    """
    try:
        return _promote_participant(
            client,
            event=event,
            participant=participant,
            attempts=attempts,
            merge=merge,
            station=station,
        )
    except Exception:
        logger.exception(
            "Combine promotion failed for participant %s in event %s",
            participant.get("id"),
            event.get("id"),
        )
        return list(PROMOTION_TARGETS)


def _promote_participant(
    client,
    *,
    event: dict,
    participant: dict,
    attempts: Sequence[dict],
    merge: bool,
    station: Optional[str],
) -> List[str]:
    athlete_id = str(participant["athlete_id"])
    event_id = str(event["id"])
    event_date = str(event["event_date"])
    participant_id = str(participant["id"])

    # Only a full rebuild can clear a station whose attempts have all been voided,
    # so the cold path ignores whichever station it was told about.
    if not merge:
        station = None

    # Withdrawing takes someone off the board; it does not unmake the results they
    # set before pulling out, so promotion scores them as if they were still in.
    scored_participant = {**participant, "withdrawn_at": None}

    bests = best_per_participant(
        attempts, participants_by_id={participant_id: scored_participant}, event=event
    ).get(participant_id, {})

    targets: List[Tuple[str, Callable[[], None]]] = []

    if station is None or station in EVENT_METRIC_KEYS:
        stations = (station,) if station else tuple(EVENT_METRIC_KEYS)
        metrics = build_event_metrics(bests, stations=stations)
        metrics["test_type"] = "Combine"
        targets.append(
            (
                "event_metrics",
                lambda: _write_event_metrics(
                    client,
                    athlete_id=athlete_id,
                    event_date=event_date,
                    event_id=event_id,
                    metrics=metrics,
                    merge=merge,
                ),
            )
        )
    if station is None or station == "landmine":
        targets.append(
            ("landmine", lambda: _promote_landmine(client, event, scored_participant, attempts))
        )
    if station is None or station == "air_bike":
        targets.append(
            ("air_bike", lambda: _promote_air_bike(client, event, scored_participant, attempts))
        )

    failed: List[str] = []
    for name, write in targets:
        # One target at a time: a landmine conflict must not also skip the air bike.
        try:
            write()
        except Exception:
            logger.exception(
                "Combine %s promotion failed for athlete %s in event %s",
                name,
                athlete_id,
                event_id,
            )
            failed.append(name)
    return failed


def _skip_if_conflict(exc: Exception, *, what: str, athlete_id: str) -> None:
    """Swallow a unique-violation on a row the combine does not own; re-raise the rest.

    A 23505 here means the athlete already has their own profile or test for this
    date — their coach tested them that morning. Editing or deleting it would destroy
    real data, so the station is skipped. That is a warning rather than a failure:
    re-syncing would only reach the same conflict again.
    """
    if str(getattr(exc, "code", "")) != UNIQUE_VIOLATION:
        raise exc
    logger.warning(
        "Combine promotion skipped %s for athlete %s — the athlete already has a row of "
        "their own for that date: %s",
        what,
        athlete_id,
        exc,
    )


def _write_event_metrics(
    client,
    *,
    athlete_id: str,
    event_date: str,
    event_id: str,
    metrics: dict,
    merge: bool,
) -> None:
    """Merge one station's keys into the combine's row, or rebuild the row wholesale."""
    if not merge:
        _replace_event_metrics(client, athlete_id, event_date, event_id, metrics)
        return

    # `test_type` on its own is a shell row: the station just saved keeps its results
    # in its own table, or its attempt could not be ranked. Either way, nothing to merge.
    if len(metrics) <= 1:
        return

    client.rpc(
        "combine_upsert_event_metrics",
        {
            "p_athlete_id": athlete_id,
            "p_event_date": event_date,
            "p_combine_event_id": event_id,
            "p_metrics": metrics,
        },
    ).execute()


def _replace_event_metrics(
    client, athlete_id: str, event_date: str, event_id: str, metrics: dict
) -> None:
    """Rebuild the combine's performance_events row wholesale."""
    existing = (
        client.table("performance_events")
        .select("id")
        .eq("athlete_id", athlete_id)
        .eq("combine_event_id", event_id)
        .execute()
    )
    rows = existing.data or []
    # Only test_type left means nothing survived; drop the row rather than leave a shell.
    if len(metrics) <= 1:
        for row in rows:
            client.table("performance_events").delete().eq("id", row["id"]).execute()
        return
    if rows:
        client.table("performance_events").update({"metrics": metrics}).eq(
            "id", rows[0]["id"]
        ).execute()
    else:
        client.table("performance_events").insert(
            {
                "athlete_id": athlete_id,
                "event_date": event_date,
                "metrics": metrics,
                "combine_event_id": event_id,
            }
        ).execute()


def _promote_landmine(client, event: dict, participant: dict, attempts: Sequence[dict]) -> None:
    """One VBT profile per side thrown, each tagged with the event."""
    athlete_id = str(participant["athlete_id"])
    base_name = event.get("landmine_exercise_name") or "Landmine Punch Throw"
    metric = event.get("landmine_velocity_metric") or "peak"

    for side, suffix in LANDMINE_PROFILE_SIDES:
        exercise_name = f"{base_name}{suffix}"
        try:
            _write_landmine_profile(
                client,
                athlete_id=athlete_id,
                event_id=str(event["id"]),
                profile_date=str(event["event_date"]),
                exercise_name=exercise_name,
                sets=build_landmine_sets(attempts, metric=metric, side=side),
            )
        except Exception as exc:
            # Per side, so one arm's conflict does not cost the other.
            _skip_if_conflict(exc, what=f"landmine '{exercise_name}'", athlete_id=athlete_id)


def _write_landmine_profile(
    client,
    *,
    athlete_id: str,
    event_id: str,
    profile_date: str,
    exercise_name: str,
    sets: List[Dict[str, Any]],
) -> None:
    """Replace this side's tagged profile, or delete it once nothing survives."""
    existing = (
        client.table("vbt_profiles")
        .select("id")
        .eq("athlete_id", athlete_id)
        .eq("exercise_name", exercise_name)
        .eq("profile_date", profile_date)
        .eq("combine_event_id", event_id)
        .execute()
    )
    rows = existing.data or []

    if not sets:
        for row in rows:
            client.table("vbt_profiles").delete().eq("id", row["id"]).execute()
        return

    if rows:
        profile_id = rows[0]["id"]
    else:
        created = (
            client.table("vbt_profiles")
            .insert(
                {
                    "athlete_id": athlete_id,
                    "exercise_name": exercise_name,
                    "profile_date": profile_date,
                    "combine_event_id": event_id,
                }
            )
            .execute()
        )
        if not created.data:
            return
        profile_id = created.data[0]["id"]

    # Replace-all: the profile is derived from the attempts, so it is rebuilt each time.
    client.table("vbt_sets").delete().eq("profile_id", profile_id).execute()
    client.table("vbt_sets").insert(
        [{**s, "profile_id": profile_id} for s in sets]
    ).execute()


def _promote_air_bike(client, event: dict, participant: dict, attempts: Sequence[dict]) -> None:
    try:
        _write_air_bike_test(client, event, participant, attempts)
    except Exception as exc:
        _skip_if_conflict(
            exc, what="air bike", athlete_id=str(participant["athlete_id"])
        )


def _write_air_bike_test(
    client, event: dict, participant: dict, attempts: Sequence[dict]
) -> None:
    """Replace the combine's own air bike test, or delete it once nothing survives."""
    sprints = build_air_bike_sprints(attempts)
    athlete_id = str(participant["athlete_id"])
    event_id = str(event["id"])
    test_date = str(event["event_date"])

    existing = (
        client.table("air_bike_tests")
        .select("id")
        .eq("athlete_id", athlete_id)
        .eq("test_date", test_date)
        .eq("combine_event_id", event_id)
        .execute()
    )
    rows = existing.data or []

    if not sprints:
        for row in rows:
            client.table("air_bike_tests").delete().eq("id", row["id"]).execute()
        return

    body_mass = participant.get("body_mass_kg")
    if body_mass is None:
        # air_bike_tests.body_mass_kg is NOT NULL; without it there is nothing to store.
        # The weigh-in re-promotes, which is when the test gets created.
        return

    if rows:
        test_id = rows[0]["id"]
        client.table("air_bike_tests").update(
            {"body_mass_kg": body_mass, "split_scheme": "7_17_27"}
        ).eq("id", test_id).execute()
    else:
        created = (
            client.table("air_bike_tests")
            .insert(
                {
                    "athlete_id": athlete_id,
                    "test_date": test_date,
                    "body_mass_kg": body_mass,
                    "split_scheme": "7_17_27",
                    "combine_event_id": event_id,
                }
            )
            .execute()
        )
        if not created.data:
            return
        test_id = created.data[0]["id"]

    client.table("air_bike_sprints").delete().eq("test_id", test_id).execute()
    client.table("air_bike_sprints").insert(
        [{**s, "test_id": test_id} for s in sprints]
    ).execute()


def promote_event(
    client, *, event: dict, participants: Sequence[dict], attempts: Sequence[dict]
) -> int:
    """Re-promote every participant. Idempotent; used by POST /sync.

    Returns how many participants had at least one target fail, which the console
    shows as the unsynced count — a promotion that silently wrote nothing is the one
    failure mode a re-sync button cannot help with.
    """
    by_participant: Dict[str, List[dict]] = {}
    for attempt in attempts:
        by_participant.setdefault(str(attempt.get("participant_id")), []).append(attempt)

    unsynced = 0
    for participant in participants:
        failed = promote_participant(
            client,
            event=event,
            participant=participant,
            attempts=by_participant.get(str(participant["id"]), []),
            merge=False,
        )
        if failed:
            unsynced += 1
    return unsynced
