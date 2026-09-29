"""Tests for the combine leaderboard engine.

Pure maths, no mocks, no database — this is where the ranking correctness lives.
"""

import hashlib
import json
from uuid import uuid4

import pytest

from app.services.combine_engine import (
    MIN_BS_NORM_N,
    MIN_FILTERED_COHORT_N,
    SCORE_CENTRE,
    SCORE_SCALE,
    STATION_SPECS,
    AttemptValue,
    LeaderboardFilters,
    asymmetry_pct,
    best_per_participant,
    bs_band,
    bs_z,
    build_leaderboard,
    cohort_stats,
    cohort_z,
    combine_score,
    display_name,
    overall_basis,
    percentile_score,
    rank_values,
    score_attempt,
    station_percentiles,
)

EVENT = {
    "id": "event-1",
    "event_name": "BS Combine 2026",
    "event_date": "2026-09-10",
    "venue": "Sheffield Hallam",
    "results_updated_at": "2026-09-10T09:00:00Z",
    "public_name_style": "full",
    "show_club": True,
    "show_bs_benchmark": True,
    "landmine_reference_load_kg": 20.0,
    "landmine_reference_tolerance_kg": 1.0,
    "landmine_velocity_metric": "peak",
    "airbike_score_basis": "w_per_kg",
    "min_stations_for_overall": 3,
    "bs_norms_snapshot": {},
}


def norm(*, male=None, female=None, pooled=(38.0, 5.0, 40)):
    """A snapshot entry in the shape `refresh-norms` writes.

    The pooled aggregate is kept for reference, but only the per-gender split is
    ever banded on — hence tests that pass a pooled-only entry and expect nothing.
    """
    entry = {"mean": pooled[0], "sd": pooled[1], "n": pooled[2], "by_gender": {}}
    for gender, values in (("male", male), ("female", female)):
        if values:
            mean, sd, n = values
            entry["by_gender"][gender] = {"mean": mean, "sd": sd, "n": n}
    return entry


def participant(pid, bib, **kwargs):
    base = {
        "id": pid,
        "athlete_id": f"athlete-{pid}",
        "bib": bib,
        "first_name": kwargs.pop("first_name", "Jack"),
        "surname": kwargs.pop("surname", "Reid"),
        "gender": kwargs.pop("gender", "male"),
        "club": kwargs.pop("club", "Repton"),
        "weight_category": kwargs.pop("weight_category", "57kg"),
        "age_group": kwargs.pop("age_group", "junior"),
        "body_mass_kg": kwargs.pop("body_mass_kg", 57.0),
        "squad": kwargs.pop("squad", None),
        "withdrawn_at": kwargs.pop("withdrawn_at", None),
    }
    base.update(kwargs)
    return base


def attempt(aid, pid, station, measures, number=1, voided=None):
    return {
        "id": aid,
        "participant_id": pid,
        "station": station,
        "attempt_number": number,
        "measures": measures,
        "voided_at": voided,
    }


def _keys_anywhere(value):
    """Every dict key in a nested payload, for proving a field never leaks."""
    keys = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(key)
            keys |= _keys_anywhere(nested)
    elif isinstance(value, list):
        for item in value:
            keys |= _keys_anywhere(item)
    return keys


def saturday_cohort():
    """Three boxers through three stations — the fixture the byte-identity guard uses.

    Frozen deliberately: the fingerprints below were taken from the engine as it
    ran before the percentile basis existed, so any drift in the z path shows up
    here rather than on the wall on event day.
    """
    participants = [
        participant("p1", 1, first_name="Jack", surname="Reid"),
        participant("p2", 2, first_name="Sam", surname="Okoro"),
        participant("p3", 3, first_name="Ali", surname="Hassan", weight_category="64kg"),
    ]
    attempts = [
        attempt("a1", "p1", "cmj", {"height_cm": 41.2}),
        attempt("a2", "p2", "cmj", {"height_cm": 38.0}),
        attempt("a3", "p3", "cmj", {"height_cm": 45.0}),
        attempt("a4", "p1", "grip", {"left_kg": 45.0, "right_kg": 50.0}),
        attempt("a5", "p2", "grip", {"left_kg": 40.0, "right_kg": 41.0}),
        attempt("a6", "p3", "grip", {"left_kg": 52.0, "right_kg": 55.0}),
        attempt("a7", "p1", "pogo", {"flight_time_ms": 480.0, "contact_time_ms": 192.0}),
        attempt("a8", "p2", "pogo", {"flight_time_ms": 450.0, "contact_time_ms": 200.0}),
        attempt("a9", "p3", "pogo", {"flight_time_ms": 500.0, "contact_time_ms": 190.0}),
    ]
    return participants, attempts


def fingerprint(board):
    """One hash over the whole payload — every value, to every decimal place."""
    return hashlib.sha256(
        json.dumps(board, sort_keys=True, default=str).encode()
    ).hexdigest()


class TestScoreAttempt:
    def test_cmj_uses_jump_height(self):
        result = score_attempt(
            attempt("a1", "p1", "cmj", {"height_cm": 41.2}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 41.2

    def test_pogo_derives_rsi_from_flight_over_contact(self):
        result = score_attempt(
            attempt("a1", "p1", "pogo", {"flight_time_ms": 480.0, "contact_time_ms": 192.0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 2.5

    def test_pogo_derives_rsi_even_when_one_was_typed(self):
        """The pair is what the operator measured — a typed RSI can be stale or mistyped."""
        result = score_attempt(
            attempt("a1", "p1", "pogo", {"rsi": 3.1, "flight_time_ms": 480.0, "contact_time_ms": 192.0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 2.5

    def test_pogo_uses_the_typed_rsi_when_the_pair_cannot_be_used(self):
        result = score_attempt(
            attempt("a1", "p1", "pogo", {"rsi": 3.1, "flight_time_ms": 480.0, "contact_time_ms": 0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 3.1

    def test_pogo_zero_contact_time_is_unrankable(self):
        assert (
            score_attempt(
                attempt("a1", "p1", "pogo", {"flight_time_ms": 480.0, "contact_time_ms": 0}),
                participant=participant("p1", 1),
                event=EVENT,
            )
            is None
        )

    def test_landmine_only_counts_the_reference_load(self):
        off_load = score_attempt(
            attempt("a1", "p1", "landmine", {"load_kg": 30.0, "peak_velocity_ms": 4.0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert off_load is None

    def test_landmine_reference_load_tolerance(self):
        """20 kg ± 1 kg — a 20.5 kg plate still counts, 22 kg does not."""
        inside = score_attempt(
            attempt("a1", "p1", "landmine", {"load_kg": 20.5, "peak_velocity_ms": 4.2}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        outside = score_attempt(
            attempt("a2", "p1", "landmine", {"load_kg": 22.0, "peak_velocity_ms": 4.2}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert inside.primary == 4.2
        assert outside is None

    def test_landmine_never_falls_back_to_the_other_metric(self):
        """A peak-ranked event beside a mean velocity is not a comparable number."""
        assert (
            score_attempt(
                attempt("a1", "p1", "landmine", {"load_kg": 20.0, "mean_velocity_ms": 2.8}),
                participant=participant("p1", 1),
                event=EVENT,
            )
            is None
        )

    def test_landmine_mean_velocity_event_ranks_mean(self):
        result = score_attempt(
            attempt(
                "a1",
                "p1",
                "landmine",
                {"load_kg": 20.0, "peak_velocity_ms": 4.2, "mean_velocity_ms": 2.8},
            ),
            participant=participant("p1", 1),
            event={**EVENT, "landmine_velocity_metric": "mean"},
        )
        assert result.primary == 2.8

    def test_landmine_carries_the_side_that_threw(self):
        result = score_attempt(
            attempt(
                "a1", "p1", "landmine", {"load_kg": 20.0, "peak_velocity_ms": 4.2, "side": "right"}
            ),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.detail["side"] == "right"

    def test_grip_ranks_the_better_side_and_reports_asymmetry(self):
        result = score_attempt(
            attempt("a1", "p1", "grip", {"left_kg": 45.0, "right_kg": 50.0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 50.0
        assert result.detail["asymmetry_pct"] == 10.0
        assert result.detail["dominant_side"] == "right"

    def test_grip_accepts_one_side_only(self):
        result = score_attempt(
            attempt("a1", "p1", "grip", {"right_kg": 50.0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 50.0
        assert result.detail["asymmetry_pct"] is None

    def test_grip_carries_optional_rfd(self):
        result = score_attempt(
            attempt("a1", "p1", "grip", {"left_kg": 45.0, "right_kg": 50.0, "rfd_right_n_s": 1450.0}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.detail["rfd_right_n_s"] == 1450.0

    def test_air_bike_scales_to_body_mass(self):
        result = score_attempt(
            attempt("a1", "p1", "air_bike", {"sprint_number": 1, "power_7s": 855.0, "power_17s": 700.0, "power_27s": 600.0}),
            participant=participant("p1", 1, body_mass_kg=57.0),
            event=EVENT,
        )
        assert result.primary == 15.0
        assert result.detail["absolute_w"] == 855.0

    def test_air_bike_without_body_mass_is_unrankable(self):
        assert (
            score_attempt(
                attempt("a1", "p1", "air_bike", {"sprint_number": 1, "power_7s": 855.0}),
                participant=participant("p1", 1, body_mass_kg=None),
                event=EVENT,
            )
            is None
        )

    def test_air_bike_zero_body_mass_is_unrankable(self):
        assert (
            score_attempt(
                attempt("a1", "p1", "air_bike", {"sprint_number": 1, "power_7s": 855.0}),
                participant=participant("p1", 1, body_mass_kg=0),
                event=EVENT,
            )
            is None
        )

    def test_a_stray_absolute_basis_still_scores_per_kilogram(self):
        """`absolute_w` is gone from the API, but a pre-034 row must not score watts
        against a W/kg norm — that reads ELITE for everyone and labels watts 'W/kg'."""
        event = {**EVENT, "airbike_score_basis": "absolute_w"}
        result = score_attempt(
            attempt("a1", "p1", "air_bike", {"sprint_number": 1, "power_7s": 855.0}),
            participant=participant("p1", 1, body_mass_kg=57.0),
            event=event,
        )
        assert result.primary == 15.0

    def test_a_stray_absolute_basis_still_needs_body_mass(self):
        event = {**EVENT, "airbike_score_basis": "absolute_w"}
        assert (
            score_attempt(
                attempt("a1", "p1", "air_bike", {"sprint_number": 1, "power_7s": 855.0}),
                participant=participant("p1", 1, body_mass_kg=None),
                event=event,
            )
            is None
        )

    def test_numeric_strings_from_postgrest_are_handled(self):
        result = score_attempt(
            attempt("a1", "p1", "cmj", {"height_cm": "41.2"}),
            participant=participant("p1", 1),
            event=EVENT,
        )
        assert result.primary == 41.2

    def test_unknown_station_is_ignored(self):
        assert (
            score_attempt(
                attempt("a1", "p1", "shuttle_run", {"time_s": 12.0}),
                participant=participant("p1", 1),
                event=EVENT,
            )
            is None
        )


class TestBestPerParticipant:
    def test_takes_the_maximum_when_higher_is_better(self):
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 38.4}, 1),
            attempt("a2", "p1", "cmj", {"height_cm": 41.2}, 2),
            attempt("a3", "p1", "cmj", {"height_cm": 40.0}, 3),
        ]
        bests = best_per_participant(
            attempts, participants_by_id={"p1": participant("p1", 1)}, event=EVENT
        )
        assert bests["p1"]["cmj"].primary == 41.2

    def test_ignores_voided_attempts(self):
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 38.4}, 1),
            attempt("a2", "p1", "cmj", {"height_cm": 99.0}, 2, voided="2026-09-10T10:00:00Z"),
        ]
        bests = best_per_participant(
            attempts, participants_by_id={"p1": participant("p1", 1)}, event=EVENT
        )
        assert bests["p1"]["cmj"].primary == 38.4

    def test_ignores_withdrawn_participants(self):
        attempts = [attempt("a1", "p1", "cmj", {"height_cm": 38.4})]
        bests = best_per_participant(
            attempts,
            participants_by_id={"p1": participant("p1", 1, withdrawn_at="2026-09-10T09:30:00Z")},
            event=EVENT,
        )
        assert bests == {}

    def test_ignores_attempts_for_unknown_participants(self):
        attempts = [attempt("a1", "ghost", "cmj", {"height_cm": 38.4})]
        assert best_per_participant(attempts, participants_by_id={}, event=EVENT) == {}


class TestCohortStats:
    def test_matches_stat_engine(self):
        stats = cohort_stats([10.0, 20.0, 30.0])
        assert stats["n"] == 3
        assert stats["mean"] == 20.0
        assert stats["median"] == 20.0
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["sd"] > 0

    def test_empty_cohort(self):
        stats = cohort_stats([])
        assert stats["n"] == 0
        assert stats["mean"] is None
        assert stats["median"] is None
        assert stats["sd"] is None

    def test_single_value_has_zero_sd(self):
        stats = cohort_stats([42.0])
        assert stats["n"] == 1
        assert stats["mean"] == 42.0
        assert stats["sd"] == 0


class TestRanking:
    def test_competition_ranking_shares_and_skips(self):
        ranks = rank_values({"a": 10.0, "b": 10.0, "c": 8.0}, higher_is_better=True)
        assert ranks == {"a": 1, "b": 1, "c": 3}

    def test_lower_is_better_inverts_the_order(self):
        ranks = rank_values({"a": 190.0, "b": 210.0}, higher_is_better=False)
        assert ranks == {"a": 1, "b": 2}

    def test_empty_input(self):
        assert rank_values({}, higher_is_better=True) == {}


class TestCohortZ:
    def test_sd_zero_returns_zero(self):
        """Everyone jumps 40.0 — nobody is above average, and nothing divides by zero."""
        stats = cohort_stats([40.0, 40.0, 40.0])
        assert stats["sd"] == 0
        assert cohort_z(40.0, stats, higher_is_better=True) == 0.0

    def test_empty_stats_return_zero(self):
        assert cohort_z(40.0, cohort_stats([]), higher_is_better=True) == 0.0

    def test_lower_is_better_flips_the_sign(self):
        stats = cohort_stats([100.0, 200.0, 300.0])
        fast = cohort_z(100.0, stats, higher_is_better=False)
        slow = cohort_z(300.0, stats, higher_is_better=False)
        assert fast > 0 > slow


class TestAsymmetry:
    def test_basic(self):
        assert asymmetry_pct(45.0, 50.0) == 10.0

    def test_symmetrical_is_zero(self):
        assert asymmetry_pct(50.0, 50.0) == 0.0

    def test_missing_side_returns_none(self):
        assert asymmetry_pct(None, 50.0) is None
        assert asymmetry_pct(50.0, None) is None

    def test_zero_max_returns_none(self):
        assert asymmetry_pct(0.0, 0.0) is None


class TestBoxingScienceNorms:
    NORM = norm(male=(38.0, 5.0, 40), female=(33.0, 4.0, 25))

    def test_z_against_the_matching_gender(self):
        assert bs_z(43.0, self.NORM, gender="male") == 1.0
        assert bs_z(37.0, self.NORM, gender="female") == 1.0

    def test_none_without_a_gender(self):
        """A boxer with no recorded gender gets no band rather than the wrong one."""
        assert bs_z(43.0, self.NORM, gender=None) is None

    def test_none_when_that_gender_is_missing_from_the_snapshot(self):
        assert bs_z(43.0, norm(male=(38.0, 5.0, 40)), gender="female") is None

    def test_never_falls_back_to_the_pooled_norm(self):
        """A pre-fix snapshot has no split, so bands stay off until an admin refreshes."""
        assert bs_z(43.0, {"mean": 38.0, "sd": 5.0, "n": 40}, gender="male") is None

    def test_none_when_sample_is_too_small(self):
        small = norm(male=(38.0, 5.0, MIN_BS_NORM_N - 1))
        assert bs_z(43.0, small, gender="male") is None

    def test_none_when_sd_is_zero(self):
        assert bs_z(43.0, norm(male=(38.0, 0.0, 40)), gender="male") is None

    def test_none_when_no_norm_exists(self):
        assert bs_z(43.0, None, gender="male") is None
        assert bs_z(43.0, {}, gender="male") is None

    def test_lower_is_better_flips_the_sign(self):
        assert bs_z(33.0, self.NORM, gender="male", higher_is_better=False) == 1.0

    def test_band_boundaries(self):
        assert bs_band(1.0) == "elite"
        assert bs_band(0.9999) == "above_average"
        assert bs_band(0.25) == "above_average"
        assert bs_band(0.2499) == "average"
        assert bs_band(-0.75) == "average"
        assert bs_band(-0.7501) == "developing"
        assert bs_band(None) is None


class TestCombineScore:
    def test_uses_only_completed_stations(self):
        """A missing station is ignored, not counted as a zero."""
        score, mean_z, completed = combine_score({"cmj": 1.0, "grip": 2.0})
        assert completed == 2
        assert mean_z == 1.5
        assert score == 65.0

    def test_average_boxer_scores_fifty(self):
        score, _, _ = combine_score({"cmj": 0.0, "grip": 0.0})
        assert score == 50.0

    def test_clamped_to_the_zero_hundred_range(self):
        assert combine_score({"cmj": 12.0})[0] == 100.0
        assert combine_score({"cmj": -12.0})[0] == 0.0

    def test_no_completed_stations_returns_none(self):
        assert combine_score({}) is None


class TestDisplayName:
    P = {"first_name": "Jack", "surname": "Reid", "bib": 12}

    def test_full(self):
        assert display_name(self.P, "full") == "Jack Reid"

    def test_first_initial(self):
        assert display_name(self.P, "first_initial") == "Jack R."

    def test_first_only(self):
        assert display_name(self.P, "first_only") == "Jack"

    def test_bib(self):
        assert display_name(self.P, "bib") == "#12"

    def test_falls_back_to_the_combined_name_column(self):
        assert display_name({"name": "Jack Reid", "bib": 12}, "first_initial") == "Jack R."

    def test_falls_back_to_the_bib_when_nameless(self):
        assert display_name({"bib": 12}, "full") == "#12"


class TestBuildLeaderboard:
    def _cohort(self):
        participants = [
            participant("p1", 1, first_name="Jack", surname="Reid", weight_category="57kg"),
            participant("p2", 2, first_name="Sam", surname="Okoro", weight_category="57kg"),
            participant("p3", 3, first_name="Ali", surname="Hassan", weight_category="64kg"),
        ]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 41.2}),
            attempt("a2", "p2", "cmj", {"height_cm": 38.0}),
            attempt("a3", "p3", "cmj", {"height_cm": 45.0}),
            attempt("a4", "p1", "grip", {"left_kg": 45.0, "right_kg": 50.0}),
            attempt("a5", "p2", "grip", {"left_kg": 40.0, "right_kg": 41.0}),
            attempt("a6", "p3", "grip", {"left_kg": 52.0, "right_kg": 55.0}),
        ]
        return participants, attempts

    def test_ranks_each_station(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert [r["display_name"] for r in cmj["results"]] == ["Ali Hassan", "Jack Reid", "Sam Okoro"]
        assert cmj["results"][0]["rank"] == 1
        assert cmj["completed"] == 3

    def test_reports_cohort_stats_per_station(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["stats"]["n"] == 3
        assert cmj["stats"]["median"] == 41.2

    def test_empty_station_has_no_rows(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        bike = next(p for p in board["stations"] if p["station"] == "air_bike")
        assert bike["completed"] == 0
        assert bike["results"] == []
        assert bike["stats"]["n"] == 0

    def test_below_min_stations_the_boxer_appears_but_is_unranked(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        assert len(board["overall"]) == 3
        # min_stations_for_overall is 3 and they have done 2
        assert all(entry["rank"] is None for entry in board["overall"])
        assert all(entry["stations_completed"] == 2 for entry in board["overall"])
        assert all(entry["eligible"] is False for entry in board["overall"])

    def test_overall_ranks_once_the_threshold_is_met(self):
        participants, attempts = self._cohort()
        event = {**EVENT, "min_stations_for_overall": 2}
        board = build_leaderboard(event=event, participants=participants, attempts=attempts)
        assert board["overall"][0]["rank"] == 1
        assert board["overall"][0]["display_name"] == "Ali Hassan"

    def test_withdrawn_participants_are_excluded(self):
        participants, attempts = self._cohort()
        participants[2]["withdrawn_at"] = "2026-09-10T09:30:00Z"
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        assert board["participant_count"] == 2
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert "Ali Hassan" not in [r["display_name"] for r in cmj["results"]]

    def test_filtering_narrows_the_displayed_cohort(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(
            event=EVENT,
            participants=participants,
            attempts=attempts,
            filters=LeaderboardFilters(weight_category="57kg"),
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert [r["display_name"] for r in cmj["results"]] == ["Jack Reid", "Sam Okoro"]

    def test_small_filtered_cohort_falls_back_to_event_stats(self):
        """Two boxers is too few to z-score against, so the panel says so."""
        participants, attempts = self._cohort()
        board = build_leaderboard(
            event=EVENT,
            participants=participants,
            attempts=attempts,
            filters=LeaderboardFilters(weight_category="57kg"),
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["cohort_basis"] == "event"
        assert cmj["stats"]["n"] == 3

    def test_large_filtered_cohort_keeps_its_own_stats(self):
        participants = [
            participant(f"p{i}", i, weight_category="57kg") for i in range(1, MIN_FILTERED_COHORT_N + 1)
        ]
        attempts = [
            attempt(f"a{i}", f"p{i}", "cmj", {"height_cm": 40.0 + i})
            for i in range(1, MIN_FILTERED_COHORT_N + 1)
        ]
        board = build_leaderboard(
            event=EVENT,
            participants=participants,
            attempts=attempts,
            filters=LeaderboardFilters(weight_category="57kg"),
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["cohort_basis"] == "filtered"

    def test_available_filters_come_from_the_roster(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        assert board["filters"]["weight_category"] == ["57kg", "64kg"]
        assert board["filters"]["club"] == ["Repton"]

    def test_attempt_counts_exclude_voided(self):
        participants, attempts = self._cohort()
        attempts.append(attempt("a7", "p1", "cmj", {"height_cm": 99.0}, 2, voided="2026-09-10T10:00:00Z"))
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        jack = next(r for r in cmj["results"] if r["display_name"] == "Jack Reid")
        assert jack["attempts"] == 1
        assert jack["value"] == 41.2

    def test_deterministic_across_runs(self):
        participants, attempts = self._cohort()
        first = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        second = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        assert first == second

    def test_tied_rows_come_back_in_bib_order(self):
        """Ten identical jumps must not shuffle between polls — the ids are random,
        and dict iteration over a set of them follows the per-worker hash seed."""
        participants = [
            participant(str(uuid4()), bib, first_name=f"Boxer{bib}") for bib in range(10, 0, -1)
        ]
        attempts = [
            attempt(str(uuid4()), p["id"], "cmj", {"height_cm": 40.0}) for p in participants
        ]
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert [r["bib"] for r in cmj["results"]] == list(range(1, 11))
        assert {r["rank"] for r in cmj["results"]} == {1}

    def test_ranks_on_the_value_the_board_shows(self):
        """Pogo is shown to 2 dp, so two throws that display 2.50 must share first."""
        participants = [participant("p1", 1), participant("p2", 2, first_name="Sam")]
        attempts = [
            attempt("a1", "p1", "pogo", {"flight_time_ms": 500.2, "contact_time_ms": 200.0}),
            attempt("a2", "p2", "pogo", {"flight_time_ms": 500.8, "contact_time_ms": 200.0}),
        ]
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        pogo = next(p for p in board["stations"] if p["station"] == "pogo")
        assert [r["display_value"] for r in pogo["results"]] == ["2.50", "2.50"]
        assert [r["rank"] for r in pogo["results"]] == [1, 1]
        assert [r["bib"] for r in pogo["results"]] == [1, 2]

    def test_tied_combine_scores_rank_together_in_bib_order(self):
        participants = [
            participant("p1", 2, first_name="Sam"),
            participant("p2", 1, first_name="Jack"),
        ]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 40.0}),
            attempt("a2", "p2", "cmj", {"height_cm": 40.0}),
            attempt("a3", "p1", "grip", {"left_kg": 40.0, "right_kg": 50.0}),
            attempt("a4", "p2", "grip", {"left_kg": 40.0, "right_kg": 50.0}),
        ]
        event = {**EVENT, "min_stations_for_overall": 2}
        board = build_leaderboard(event=event, participants=participants, attempts=attempts)
        assert [e["bib"] for e in board["overall"]] == [1, 2]
        assert [e["rank"] for e in board["overall"]] == [1, 1]

    def test_landmine_rows_carry_the_side(self):
        participants = [participant("p1", 1)]
        attempts = [
            attempt(
                "a1",
                "p1",
                "landmine",
                {"load_kg": 20.0, "peak_velocity_ms": 4.2, "side": "right"},
            )
        ]
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        landmine = next(p for p in board["stations"] if p["station"] == "landmine")
        assert landmine["results"][0]["side"] == "right"

    def test_rows_for_other_stations_have_no_side(self):
        participants, attempts = self._cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["side"] is None

    def test_an_all_voided_station_has_no_rows(self):
        participants = [participant("p1", 1)]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 41.2}, 1, voided="2026-09-10T10:00:00Z"),
            attempt("a2", "p1", "cmj", {"height_cm": 38.0}, 2, voided="2026-09-10T10:05:00Z"),
        ]
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["completed"] == 0
        assert cmj["results"] == []
        assert board["overall"] == []

    def test_four_filtered_boxers_borrow_the_room_five_keep_their_own(self):
        others = [participant("o1", 90, weight_category="64kg"), participant("o2", 91, weight_category="64kg")]
        attempts = [attempt("ao1", "o1", "cmj", {"height_cm": 39.0}), attempt("ao2", "o2", "cmj", {"height_cm": 39.5})]

        def board_for(count):
            people = [participant(f"p{i}", i, weight_category="57kg") for i in range(1, count + 1)]
            jumps = [attempt(f"a{i}", f"p{i}", "cmj", {"height_cm": 40.0 + i}) for i in range(1, count + 1)]
            return build_leaderboard(
                event=EVENT,
                participants=people + others,
                attempts=jumps + attempts,
                filters=LeaderboardFilters(weight_category="57kg"),
            )

        four = next(p for p in board_for(4)["stations"] if p["station"] == "cmj")
        five = next(p for p in board_for(5)["stations"] if p["station"] == "cmj")
        assert four["cohort_basis"] == "event"
        assert five["cohort_basis"] == "filtered"

    def test_gender_never_reaches_the_payload(self):
        """Participants carry gender so the engine can pick a norm; nothing publishes it."""
        participants, attempts = self._cohort()
        participants[0]["gender"] = "female"
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        assert "gender" not in _keys_anywhere(board)


class TestGenderMatchedBands:
    """A mixed pool reads a strong girl as DEVELOPING, in red, on a public wall."""

    SNAPSHOT = {"height_cm": norm(male=(38.0, 5.0, 40), female=(30.0, 4.0, 22))}

    def _band(self, snapshot, **participant_overrides):
        event = {**EVENT, "bs_norms_snapshot": snapshot}
        people = [participant("p1", 1, **participant_overrides)]
        board = build_leaderboard(
            event=event,
            participants=people,
            attempts=[attempt("a1", "p1", "cmj", {"height_cm": 36.0})],
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        return cmj["results"][0]["bs_band"]

    def test_a_female_boxer_is_banded_against_the_female_norm(self):
        # 36 cm is z = +1.5 against the female norm, z = -0.4 against the male one.
        assert self._band(self.SNAPSHOT, gender="female") == "elite"
        assert self._band(self.SNAPSHOT, gender="male") == "average"

    def test_no_band_when_the_gender_is_missing(self):
        assert self._band(self.SNAPSHOT, gender=None) is None

    def test_no_band_below_the_minimum_sample(self):
        snapshot = {"height_cm": norm(female=(30.0, 4.0, MIN_BS_NORM_N - 1))}
        assert self._band(snapshot, gender="female") is None

    def test_no_band_from_a_snapshot_taken_before_the_split(self):
        assert self._band({"height_cm": {"mean": 38.0, "sd": 5.0, "n": 40}}) is None


class TestPublicSanitisation:
    """The public board must never carry identifiers or an invertible benchmark z."""

    def _board(self, **event_overrides):
        event = {
            **EVENT,
            "bs_norms_snapshot": {"height_cm": norm(male=(38.0, 5.0, 40))},
            **event_overrides,
        }
        participants = [participant("p1", 1), participant("p2", 2, first_name="Sam", surname="Okoro")]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 41.2}),
            attempt("a2", "p2", "cmj", {"height_cm": 38.0}),
        ]
        return build_leaderboard(
            event=event, participants=participants, attempts=attempts, public=True
        )

    def test_no_identifiers_in_public_rows(self):
        board = self._board()
        for panel in board["stations"]:
            for row in panel["results"]:
                assert "participant_id" not in row
                assert "athlete_id" not in row
                assert "z_bs" not in row
                assert "detail" not in row
        for entry in board["overall"]:
            assert "participant_id" not in entry
            assert "mean_z" not in entry

    def test_public_shows_a_band_not_a_number(self):
        board = self._board()
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["bs_band"] in {"elite", "above_average", "average", "developing"}

    def test_only_the_leader_carries_a_band(self):
        """A band on every row lets the fixed thresholds bracket the BS mean and SD."""
        board = self._board()
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["rank"] == 1
        assert cmj["results"][0]["bs_band"] is not None
        assert all(row["bs_band"] is None for row in cmj["results"][1:])

    def test_the_authenticated_board_bands_every_row(self):
        event = {**EVENT, "bs_norms_snapshot": {"height_cm": norm(male=(38.0, 5.0, 40))}}
        board = build_leaderboard(
            event=event,
            participants=[participant("p1", 1), participant("p2", 2, first_name="Sam")],
            attempts=[
                attempt("a1", "p1", "cmj", {"height_cm": 43.0}),
                attempt("a2", "p2", "cmj", {"height_cm": 38.0}),
            ],
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert [row["bs_band"] for row in cmj["results"]] == ["elite", "average"]

    def test_authenticated_board_keeps_the_numeric_z(self):
        event = {**EVENT, "bs_norms_snapshot": {"height_cm": norm(male=(38.0, 5.0, 40))}}
        board = build_leaderboard(
            event=event,
            participants=[participant("p1", 1)],
            attempts=[attempt("a1", "p1", "cmj", {"height_cm": 43.0})],
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["z_bs"] == 1.0
        assert cmj["results"][0]["participant_id"] == "p1"

    def test_name_style_is_applied(self):
        board = self._board(public_name_style="first_initial")
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["display_name"] == "Jack R."

    def test_club_can_be_hidden(self):
        board = self._board(show_club=False)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert "club" not in cmj["results"][0]

    def test_benchmark_can_be_hidden(self):
        board = self._board(show_bs_benchmark=False)
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["bs_band"] is None

    def test_hiding_clubs_also_ignores_a_club_filter(self):
        """Otherwise ?club=Repton narrows a board that shows no clubs, which
        enumerates the hidden club membership of named minors."""
        event = {**EVENT, "show_club": False}
        participants = [
            participant("p1", 1, club="Repton"),
            participant("p2", 2, first_name="Sam", club="Islington"),
        ]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 41.2}),
            attempt("a2", "p2", "cmj", {"height_cm": 38.0}),
        ]
        board = build_leaderboard(
            event=event,
            participants=participants,
            attempts=attempts,
            filters=LeaderboardFilters(club="Repton"),
            public=True,
        )
        cmj = next(p for p in board["stations"] if p["station"] == "cmj")
        assert len(cmj["results"]) == 2
        assert board["participant_count"] == 2

    def test_hiding_clubs_also_withholds_the_club_filter_list(self):
        """Nulling the per-row club is not enough — the filter chips leak it too."""
        board = self._board(show_club=False)
        assert "club" not in board["filters"]
        assert "weight_category" in board["filters"]


class TestStationPercentiles:
    """The percentile alternative to a within-cohort z.

    Measured on the project's own 119 athletes the two composites agree almost
    perfectly (Spearman 0.982), and part company exactly where a skewed metric
    inflates a z: on contact time only 1.7% of athletes clear z >= 1.0 where normal
    theory expects 15.9%. A percentile cannot be inflated that way, and a 15-year-old
    can be told what it means.
    """

    def test_a_clean_spread_runs_from_zero_to_one_hundred(self):
        assert station_percentiles(
            {"a": 10.0, "b": 20.0, "c": 30.0}, higher_is_better=True
        ) == {"a": 0.0, "b": 50.0, "c": 100.0}

    def test_ties_take_the_midpoint_of_the_positions_they_span(self):
        """Two boxers tied at the top of three each beat one and tie one."""
        percentiles = station_percentiles(
            {"a": 10.0, "b": 20.0, "c": 20.0}, higher_is_better=True
        )
        assert percentiles["a"] == 0.0
        assert percentiles["b"] == percentiles["c"] == 75.0

    def test_everyone_tied_sits_in_the_middle(self):
        percentiles = station_percentiles(
            {"a": 10.0, "b": 10.0, "c": 10.0}, higher_is_better=True
        )
        assert set(percentiles.values()) == {50.0}

    def test_a_single_participant_scores_fifty(self):
        """The first boxer through a station has beaten nobody and lost to nobody."""
        assert station_percentiles({"a": 10.0}, higher_is_better=True) == {"a": 50.0}

    def test_lower_is_better_inverts_the_scale(self):
        assert station_percentiles(
            {"a": 190.0, "b": 210.0}, higher_is_better=False
        ) == {"a": 100.0, "b": 0.0}

    def test_empty_input(self):
        assert station_percentiles({}, higher_is_better=True) == {}

    def test_a_freak_value_moves_nobody(self):
        """The whole point: one outlier changes the order, never the spacing."""
        modest = station_percentiles(
            {"a": 10.0, "b": 20.0, "c": 30.0}, higher_is_better=True
        )
        freakish = station_percentiles(
            {"a": 10.0, "b": 20.0, "c": 300.0}, higher_is_better=True
        )
        assert modest == freakish


class TestPercentileScore:
    def test_mean_of_the_stations_completed(self):
        assert percentile_score({"cmj": 100.0, "grip": 50.0}) == 75.0

    def test_rounded_to_one_decimal(self):
        assert percentile_score({"cmj": 33.333333, "grip": 0.0}) == 16.7

    def test_no_completed_stations_returns_none(self):
        assert percentile_score({}) is None


class TestOverallBasis:
    def test_a_row_written_before_the_column_existed_reads_as_z(self):
        assert overall_basis({}) == "z"
        assert overall_basis({"overall_score_basis": None}) == "z"

    def test_the_event_column_is_honoured(self):
        assert overall_basis({"overall_score_basis": "percentile"}) == "percentile"
        assert overall_basis({"overall_score_basis": "z"}) == "z"

    def test_an_unrecognised_basis_falls_back_to_z(self):
        """The operator has to switch this deliberately; anything else keeps today."""
        assert overall_basis({"overall_score_basis": "rank"}) == "z"


class TestDefaultBasisIsUnchanged:
    """The guard on event day: nothing moves unless the operator switches it.

    The fingerprints were taken from the engine before the percentile basis existed.
    A failure here means a default event's board changed — which is the one thing
    this work must not do.
    """

    AUTHENTICATED = "060d02b4785daa8091c99811f98d8f2549b4d19c6d49921ea49b0fde25e22240"
    PUBLIC = "8b7f995e42e7152a15cda15e9a02f14cc1dcc7b0c58cfa1a6a5d7f30d7b91881"

    def test_a_default_event_is_byte_identical_to_today(self):
        participants, attempts = saturday_cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        assert board.pop("score_basis") == "z"
        assert fingerprint(board) == self.AUTHENTICATED

    def test_the_public_board_is_byte_identical_to_today(self):
        participants, attempts = saturday_cohort()
        board = build_leaderboard(
            event=EVENT, participants=participants, attempts=attempts, public=True
        )
        assert board.pop("score_basis") == "z"
        assert fingerprint(board) == self.PUBLIC

    def test_an_explicit_z_matches_a_row_written_before_the_column(self):
        participants, attempts = saturday_cohort()
        implicit = build_leaderboard(
            event=EVENT, participants=participants, attempts=attempts
        )
        explicit = build_leaderboard(
            event={**EVENT, "overall_score_basis": "z"},
            participants=participants,
            attempts=attempts,
        )
        assert implicit == explicit

    def test_the_score_is_still_the_t_score(self):
        participants, attempts = saturday_cohort()
        board = build_leaderboard(event=EVENT, participants=participants, attempts=attempts)
        for entry in board["overall"]:
            expected = round(SCORE_CENTRE + SCORE_SCALE * entry["mean_z"], 1)
            assert entry["combine_score"] == expected


class TestPercentileBasis:
    """Switching the basis changes one number and nothing else."""

    def _event(self, basis, **overrides):
        return {
            **EVENT,
            "overall_score_basis": basis,
            "min_stations_for_overall": 2,
            **overrides,
        }

    def _skewed(self):
        """One freakish boxer, two tied in the middle, one at the bottom."""
        participants = [
            participant("p1", 1, first_name="Jack", surname="Reid"),
            participant("p2", 2, first_name="Sam", surname="Okoro"),
            participant("p3", 3, first_name="Ali", surname="Hassan"),
            participant("p4", 4, first_name="Omar", surname="Khan"),
        ]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 40.0}),
            attempt("a2", "p2", "cmj", {"height_cm": 40.0}),
            attempt("a3", "p3", "cmj", {"height_cm": 60.0}),
            attempt("a4", "p4", "cmj", {"height_cm": 38.0}),
            attempt("a5", "p1", "grip", {"left_kg": 40.0, "right_kg": 50.0}),
            attempt("a6", "p2", "grip", {"left_kg": 40.0, "right_kg": 50.0}),
            attempt("a7", "p3", "grip", {"left_kg": 60.0, "right_kg": 70.0}),
            attempt("a8", "p4", "grip", {"left_kg": 40.0, "right_kg": 45.0}),
        ]
        return participants, attempts

    def _boards(self):
        participants, attempts = self._skewed()
        return (
            build_leaderboard(
                event=self._event("z"), participants=participants, attempts=attempts
            ),
            build_leaderboard(
                event=self._event("percentile"),
                participants=participants,
                attempts=attempts,
            ),
        )

    def test_the_board_declares_which_basis_it_used(self):
        z_board, percentile_board = self._boards()
        assert z_board["score_basis"] == "z"
        assert percentile_board["score_basis"] == "percentile"

    def test_the_score_becomes_the_percentile_composite(self):
        _, board = self._boards()
        by_bib = {e["bib"]: e["combine_score"] for e in board["overall"]}
        # Both stations rank 38/40/40/60 and 45/50/50/70 the same way, so the tied
        # pair take the midpoint of positions 1 and 2 on each.
        assert by_bib == {3: 100.0, 1: 50.0, 2: 50.0, 4: 0.0}

    def test_the_score_actually_changes(self):
        """A freak 60 cm jump drags the mean and the SD, so the z path is not this."""
        z_board, percentile_board = self._boards()
        z_scores = {e["bib"]: e["combine_score"] for e in z_board["overall"]}
        percentiles = {e["bib"]: e["combine_score"] for e in percentile_board["overall"]}
        assert z_scores != percentiles

    def test_ranking_and_tie_order_are_untouched(self):
        z_board, percentile_board = self._boards()
        assert [e["bib"] for e in z_board["overall"]] == [3, 1, 2, 4]
        assert [e["bib"] for e in percentile_board["overall"]] == [3, 1, 2, 4]
        assert [e["rank"] for e in percentile_board["overall"]] == [1, 2, 2, 4]
        assert [e["rank"] for e in z_board["overall"]] == [1, 2, 2, 4]

    def test_the_eligibility_gate_is_untouched(self):
        """Two stations done, three required — unranked under either basis."""
        participants, attempts = self._skewed()
        event = self._event("percentile", min_stations_for_overall=3)
        board = build_leaderboard(
            event=event, participants=participants, attempts=attempts
        )
        assert len(board["overall"]) == 4
        assert all(e["eligible"] is False for e in board["overall"])
        assert all(e["rank"] is None for e in board["overall"])
        assert all(e["stations_completed"] == 2 for e in board["overall"])

    def test_mean_z_still_means_mean_z(self):
        """It is the coach's diagnostic, not the displayed score — it must not move."""
        z_board, percentile_board = self._boards()
        z_entries = {e["bib"]: e for e in z_board["overall"]}
        percentile_entries = {e["bib"]: e for e in percentile_board["overall"]}
        for bib, entry in z_entries.items():
            assert percentile_entries[bib]["mean_z"] == entry["mean_z"]
        assert percentile_entries[1]["combine_score"] != z_entries[1]["combine_score"]

    def test_mean_z_stays_off_the_public_board(self):
        participants, attempts = self._skewed()
        board = build_leaderboard(
            event=self._event("percentile"),
            participants=participants,
            attempts=attempts,
            public=True,
        )
        assert board["score_basis"] == "percentile"
        for entry in board["overall"]:
            assert "mean_z" not in entry
            assert "participant_id" not in entry

    def test_only_the_stations_a_boxer_completed_are_averaged(self):
        """The timetable must not punish anyone — the same rule as the z path."""
        participants = [
            participant("p1", 1, first_name="Jack"),
            participant("p2", 2, first_name="Sam"),
            participant("p3", 3, first_name="Ali"),
        ]
        attempts = [
            attempt("a1", "p1", "cmj", {"height_cm": 45.0}),
            attempt("a2", "p2", "cmj", {"height_cm": 40.0}),
            attempt("a3", "p3", "cmj", {"height_cm": 38.0}),
            # Only the other two have reached the grip station.
            attempt("a4", "p2", "grip", {"left_kg": 52.0, "right_kg": 55.0}),
            attempt("a5", "p3", "grip", {"left_kg": 40.0, "right_kg": 41.0}),
        ]
        board = build_leaderboard(
            event=self._event("percentile", min_stations_for_overall=1),
            participants=participants,
            attempts=attempts,
        )
        jack = next(e for e in board["overall"] if e["bib"] == 1)
        assert jack["stations_completed"] == 1
        # Top of the only station he has done, not a third of it.
        assert jack["combine_score"] == 100.0
        assert jack["rank"] == 1

    def test_a_station_nobody_has_reached_scores_nobody(self):
        participants, attempts = self._skewed()
        board = build_leaderboard(
            event=self._event("percentile"), participants=participants, attempts=attempts
        )
        assert all(e["stations_completed"] == 2 for e in board["overall"])

    def test_percentiles_never_reach_the_payload_per_station(self):
        """The composite is published; the per-station percentile is working state."""
        participants, attempts = self._skewed()
        board = build_leaderboard(
            event=self._event("percentile"),
            participants=participants,
            attempts=attempts,
            public=True,
        )
        assert "percentile" not in _keys_anywhere(board)
