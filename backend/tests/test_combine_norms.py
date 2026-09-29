"""Tests for the Boxing Science norm snapshot.

The snapshot is what the public board bands against, so three things matter here:
the aggregation is right (one value per athlete, the event's own boxers left out),
the split by gender exists (a mixed pool marks a strong girl DEVELOPING in red on a
public wall), and nothing but aggregates ever reaches the event row.
"""

import pytest

from app.services.combine_norms import (
    SCORE_KEYS,
    compute_bs_norms,
    coverage_from_snapshot,
    fetch_all_rows,
    norms_from_rows,
)
from tests.fake_supabase import FakeSupabase

ADMIN_ID = "admin-1"

EVENT = {
    "id": "event-1",
    "event_date": "2026-09-19",
    "landmine_exercise_name": "Landmine Punch Throw",
    "landmine_reference_load_kg": 20.0,
    "landmine_reference_tolerance_kg": 1.0,
    "landmine_velocity_metric": "peak",
}


def event_row(athlete_id: str, index: int, **metrics) -> dict:
    return {
        "id": f"pe-{index:05d}",
        "athlete_id": athlete_id,
        "event_date": "2026-01-01",
        "metrics": metrics,
    }


def store(*, athletes, **tables) -> FakeSupabase:
    """An admin pool of `athletes`, plus whatever reference rows the test needs."""
    return FakeSupabase(
        profiles=[{"id": ADMIN_ID, "role": "admin"}],
        athletes=[{**a, "coach_id": ADMIN_ID} for a in athletes],
        performance_events=tables.pop("performance_events", []),
        vbt_profiles=tables.pop("vbt_profiles", []),
        vbt_sets=tables.pop("vbt_sets", []),
        air_bike_tests=tables.pop("air_bike_tests", []),
        air_bike_sprints=tables.pop("air_bike_sprints", []),
        **tables,
    )


class TestNormsFromRows:
    def test_one_value_per_athlete(self):
        """An athlete tested ten times counts once, at their best."""
        snapshot = norms_from_rows(
            events=[
                event_row("a1", 1, height_cm=40.0),
                event_row("a1", 2, height_cm=44.0),
                event_row("a1", 3, height_cm=42.0),
                event_row("a2", 4, height_cm=30.0),
            ],
            vbt_sets=[],
            air_bike=[],
            gender_by_athlete={"a1": "male", "a2": "male"},
        )
        assert snapshot["height_cm"]["n"] == 2
        assert snapshot["height_cm"]["mean"] == 37.0  # (44 + 30) / 2

    def test_grip_takes_the_better_side(self):
        snapshot = norms_from_rows(
            events=[
                event_row("a1", 1, grip_strength_left_kg=45.0, grip_strength_right_kg=52.0),
            ],
            vbt_sets=[],
            air_bike=[],
            gender_by_athlete={"a1": "male"},
        )
        assert snapshot["grip_best_kg"]["mean"] == 52.0

    def test_numeric_strings_from_postgrest_are_coerced(self):
        snapshot = norms_from_rows(
            events=[event_row("a1", 1, height_cm="41.2")],
            vbt_sets=[],
            air_bike=[],
            gender_by_athlete={"a1": "male"},
        )
        assert snapshot["height_cm"]["mean"] == 41.2

    def test_splits_by_gender(self):
        snapshot = norms_from_rows(
            events=[
                event_row("m1", 1, height_cm=40.0),
                event_row("m2", 2, height_cm=44.0),
                event_row("f1", 3, height_cm=30.0),
                event_row("f2", 4, height_cm=34.0),
            ],
            vbt_sets=[],
            air_bike=[],
            gender_by_athlete={"m1": "male", "m2": "male", "f1": "female", "f2": "female"},
        )
        height = snapshot["height_cm"]
        assert height["n"] == 4
        # StatEngine reports the population SD, as it does for every other benchmark.
        assert height["by_gender"]["male"] == {"mean": 42.0, "sd": 2.0, "n": 2}
        assert height["by_gender"]["female"]["mean"] == 32.0

    def test_unknown_gender_counts_in_the_pool_but_bands_nobody(self):
        snapshot = norms_from_rows(
            events=[
                event_row("m1", 1, height_cm=40.0),
                event_row("x1", 2, height_cm=44.0),
            ],
            vbt_sets=[],
            air_bike=[],
            gender_by_athlete={"m1": "male", "x1": None},
        )
        assert snapshot["height_cm"]["n"] == 2
        assert snapshot["height_cm"]["by_gender"]["male"]["n"] == 1
        assert "female" not in snapshot["height_cm"]["by_gender"]

    def test_nothing_to_summarise_leaves_the_key_out(self):
        snapshot = norms_from_rows(
            events=[], vbt_sets=[], air_bike=[], gender_by_athlete={}
        )
        assert snapshot == {}


class TestComputeBsNorms:
    def test_excludes_the_events_own_participants(self):
        """40 teenagers tested this morning must not move the norms they are measured against."""
        client = store(
            athletes=[
                {"id": "a1", "gender": "male"},
                {"id": "a2", "gender": "male"},
            ],
            performance_events=[
                event_row("a1", 1, height_cm=40.0),
                event_row("a2", 2, height_cm=60.0),
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids={"a2"})
        assert snapshot["height_cm"]["n"] == 1
        assert snapshot["height_cm"]["mean"] == 40.0

    def test_empty_pool_gives_an_empty_snapshot(self):
        client = store(athletes=[{"id": "a1", "gender": "male"}], performance_events=[])
        assert compute_bs_norms(client, event=EVENT, exclude_athlete_ids={"a1"}) == {}

    def test_landmine_only_counts_the_reference_load_window(self):
        client = store(
            athletes=[{"id": "a1", "gender": "male"}, {"id": "a2", "gender": "male"}],
            vbt_profiles=[
                {"id": "pr1", "athlete_id": "a1", "exercise_name": "Landmine Punch Throw"},
                {"id": "pr2", "athlete_id": "a2", "exercise_name": "Landmine Punch Throw"},
            ],
            vbt_sets=[
                # a1: inside the 20 ± 1 kg window
                {"id": "s1", "profile_id": "pr1", "load_kg": 20.5, "peak_velocity_ms": 4.2},
                # a2: a valid throw, but not at the load the board compares
                {"id": "s2", "profile_id": "pr2", "load_kg": 30.0, "peak_velocity_ms": 5.0},
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())
        assert snapshot["landmine_velocity_ms"]["n"] == 1
        assert snapshot["landmine_velocity_ms"]["mean"] == 4.2

    def test_landmine_pools_both_sides_into_one_value_per_athlete(self):
        """Promotion writes '(Left)' and '(Right)' profiles — the norm is the better arm."""
        client = store(
            athletes=[{"id": "a1", "gender": "male"}],
            vbt_profiles=[
                {"id": "pl", "athlete_id": "a1", "exercise_name": "Landmine Punch Throw (Left)"},
                {"id": "pr", "athlete_id": "a1", "exercise_name": "Landmine Punch Throw (Right)"},
            ],
            vbt_sets=[
                {"id": "s1", "profile_id": "pl", "load_kg": 20.0, "peak_velocity_ms": 3.8},
                {"id": "s2", "profile_id": "pr", "load_kg": 20.0, "peak_velocity_ms": 4.4},
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())
        assert snapshot["landmine_velocity_ms"]["n"] == 1
        assert snapshot["landmine_velocity_ms"]["mean"] == 4.4

    def test_landmine_ignores_a_profile_for_another_exercise(self):
        client = store(
            athletes=[{"id": "a1", "gender": "male"}],
            vbt_profiles=[
                {"id": "pr1", "athlete_id": "a1", "exercise_name": "Back Squat"},
            ],
            vbt_sets=[
                {"id": "s1", "profile_id": "pr1", "load_kg": 20.0, "peak_velocity_ms": 4.2},
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())
        assert "landmine_velocity_ms" not in snapshot

    def test_landmine_does_not_fall_back_to_the_other_velocity_metric(self):
        """A peak-ranked event must not quietly band a mean velocity."""
        client = store(
            athletes=[{"id": "a1", "gender": "male"}],
            vbt_profiles=[
                {"id": "pr1", "athlete_id": "a1", "exercise_name": "Landmine Punch Throw"},
            ],
            vbt_sets=[
                {"id": "s1", "profile_id": "pr1", "load_kg": 20.0, "mean_velocity_ms": 2.8},
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())
        assert "landmine_velocity_ms" not in snapshot

    def test_air_bike_needs_body_mass(self):
        client = store(
            athletes=[{"id": "a1", "gender": "male"}, {"id": "a2", "gender": "male"}],
            air_bike_tests=[
                {"id": "t1", "athlete_id": "a1", "body_mass_kg": 57.0},
                {"id": "t2", "athlete_id": "a2", "body_mass_kg": None},
            ],
            air_bike_sprints=[
                {"id": "sp1", "test_id": "t1", "power_7s": 855.0},
                {"id": "sp2", "test_id": "t2", "power_7s": 900.0},
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())
        assert snapshot["air_bike_power_7s_wkg"]["n"] == 1
        assert snapshot["air_bike_power_7s_wkg"]["mean"] == 15.0

    def test_snapshot_holds_aggregates_only(self):
        """What lands on the event row is read by an unauthenticated request."""
        client = store(
            athletes=[{"id": "a1", "gender": "male"}, {"id": "a2", "gender": "female"}],
            performance_events=[
                event_row("a1", 1, height_cm=40.0),
                event_row("a2", 2, height_cm=36.0),
            ],
        )
        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())

        for entry in snapshot.values():
            assert set(entry) <= {"mean", "sd", "n", "by_gender"}
            for per_gender in entry["by_gender"].values():
                assert set(per_gender) == {"mean", "sd", "n"}
        assert "a1" not in repr(snapshot)
        assert "athlete" not in repr(snapshot)

    def test_reads_past_the_postgrest_row_cap(self):
        """PostgREST truncates unpaginated selects at db-max-rows, silently."""
        athlete = {"id": "a1", "gender": "male"}
        events = [event_row("a1", i, height_cm=30.0 + i * 0.01) for i in range(1, 1201)]
        client = store(athletes=[athlete], performance_events=events)
        client.max_rows = 1000

        snapshot = compute_bs_norms(client, event=EVENT, exclude_athlete_ids=set())
        # The best jump is the last row; a truncated read would report 39.99.
        assert snapshot["height_cm"]["mean"] == pytest.approx(42.0, abs=0.001)


class TestFetchAllRows:
    def test_pages_until_a_short_page(self):
        rows = [{"id": f"r-{i:05d}", "value": i} for i in range(2500)]
        client = FakeSupabase(max_rows=1000, widgets=rows)

        fetched = fetch_all_rows(lambda: client.table("widgets").select("*"))

        assert len(fetched) == 2500
        assert fetched[-1]["value"] == 2499

    def test_exact_multiple_of_the_page_size_stops(self):
        rows = [{"id": f"r-{i:05d}", "value": i} for i in range(20)]
        client = FakeSupabase(widgets=rows)

        assert len(fetch_all_rows(lambda: client.table("widgets").select("*"), page_size=10)) == 20

    def test_empty_table(self):
        client = FakeSupabase(widgets=[])
        assert fetch_all_rows(lambda: client.table("widgets").select("*")) == []


class TestCoverage:
    def test_counts_per_key_per_gender(self):
        snapshot = {
            "height_cm": {
                "mean": 40.0,
                "sd": 5.0,
                "n": 44,
                "by_gender": {
                    "male": {"mean": 41.0, "sd": 5.0, "n": 30},
                    "female": {"mean": 36.0, "sd": 4.0, "n": 14},
                },
            }
        }
        assert coverage_from_snapshot(snapshot)["height_cm"] == {"male": 30, "female": 14}

    def test_carries_no_means_or_sds(self):
        snapshot = {"height_cm": {"mean": 40.0, "sd": 5.0, "n": 44, "by_gender": {"male": {"mean": 41.0, "sd": 5.0, "n": 30}}}}
        assert "41.0" not in repr(coverage_from_snapshot(snapshot))

    def test_a_key_with_no_norms_at_all_reports_zero(self):
        """A station the pool cannot band is the one the console must warn about.

        Omitting it reads on screen exactly like a station that is fully covered.
        """
        snapshot = {
            "height_cm": {
                "mean": 38.0,
                "sd": 5.0,
                "n": 44,
                "by_gender": {"male": {"mean": 38.0, "sd": 5.0, "n": 30}},
            }
        }
        coverage = coverage_from_snapshot(snapshot)

        assert set(coverage) == set(SCORE_KEYS)
        assert coverage["air_bike_power_7s_wkg"] == {"male": 0, "female": 0}

    def test_a_gender_with_no_norms_reports_zero(self):
        snapshot = {"height_cm": {"by_gender": {"male": {"n": 30}}}}
        assert coverage_from_snapshot(snapshot)["height_cm"] == {"male": 30, "female": 0}

    def test_legacy_snapshot_without_a_split_reports_zero_everywhere(self):
        """A split-less snapshot bands nobody, so every key is genuinely at zero."""
        assert coverage_from_snapshot({"height_cm": {"mean": 40.0, "sd": 5.0, "n": 44}}) == {
            key: {"male": 0, "female": 0} for key in SCORE_KEYS
        }

    def test_empty_snapshot(self):
        assert coverage_from_snapshot({}) == {}
        assert coverage_from_snapshot(None) == {}
