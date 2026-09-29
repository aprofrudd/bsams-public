"""Tests for the authenticated combine endpoints."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import combine_promotion
from tests.conftest import TEST_USER_ID
from tests.fake_supabase import FakeApiError, FakeSupabase

client = TestClient(app)

COACH_ID = str(TEST_USER_ID)
EVENT_DATE = "2026-09-10"


def _future(days: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past(days: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def make_event(**overrides) -> dict:
    event = {
        "id": str(uuid4()),
        "coach_id": COACH_ID,
        "event_name": "BS Combine 2026",
        "event_date": EVENT_DATE,
        "venue": "Sheffield Hallam",
        "status": "draft",
        "share_token": "tok_" + uuid4().hex,
        "share_token_expires_at": _future(),
        "share_revoked_at": None,
        "public_display_consent_confirmed_at": None,
        "public_name_style": "full",
        "show_bs_benchmark": True,
        "show_club": True,
        "landmine_exercise_name": "Landmine Punch Throw",
        "landmine_loads_kg": [10, 15, 20, 25],
        "landmine_reference_load_kg": 20,
        "landmine_reference_tolerance_kg": 1.0,
        "landmine_velocity_metric": "peak",
        "airbike_score_basis": "w_per_kg",
        "overall_score_basis": "z",
        "min_stations_for_overall": 3,
        "bs_norms_snapshot": {},
        "bs_norms_updated_at": None,
        "results_updated_at": datetime.now(timezone.utc).isoformat(),
        "notes": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    event.update(overrides)
    return event


def make_athlete(name="Jack Reid", **overrides) -> dict:
    first, _, surname = name.partition(" ")
    athlete = {
        "id": str(uuid4()),
        "coach_id": COACH_ID,
        "name": name,
        "first_name": first,
        "surname": surname,
        "gender": "male",
        "date_of_birth": None,
        "body_mass_kg": 57.0,
        "status": "amateur",
    }
    athlete.update(overrides)
    return athlete


def make_participant(event, athlete, bib=1, **overrides) -> dict:
    participant = {
        "id": str(uuid4()),
        "combine_event_id": event["id"],
        "athlete_id": athlete["id"],
        "bib": bib,
        "club": "Repton",
        "weight_category": "57kg",
        "age_group": "junior",
        "body_mass_kg": 57.0,
        "squad": None,
        "withdrawn_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    participant.update(overrides)
    return participant


def make_attempt(event, participant, station, measures, attempt_number=1, **overrides) -> dict:
    """An attempt row as the DB holds it — for tests that call promotion directly."""
    attempt = {
        "id": str(uuid4()),
        "combine_event_id": event["id"],
        "participant_id": participant["id"],
        "station": station,
        "attempt_number": attempt_number,
        "measures": measures,
        "voided_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    attempt.update(overrides)
    return attempt


class FailingStore(FakeSupabase):
    """A store where one table is unreachable, to prove failures are reported."""

    def __init__(self, *, failing_table: str, **tables):
        super().__init__(**tables)
        self.failing_table = failing_table

    def table(self, name: str):
        if name == self.failing_table:
            raise RuntimeError("connection reset by peer")
        return super().table(name)


class WriteLog(FakeSupabase):
    """A store that records every write, so a test can assert what a request touched."""

    def __init__(self, **tables):
        super().__init__(**tables)
        self.writes = []

    def table(self, name: str):
        table = super().table(name)
        execute = table.execute

        def record():
            if table.op in ("insert", "update", "delete"):
                self.writes.append((name, table.op))
            return execute()

        table.execute = record
        return table


@pytest.fixture
def db():
    """Patch the Supabase client for the whole request lifecycle."""
    store = FakeSupabase(
        combine_events=[],
        combine_participants=[],
        combine_attempts=[],
        athletes=[],
        performance_events=[],
        vbt_profiles=[],
        vbt_sets=[],
        air_bike_tests=[],
        air_bike_sprints=[],
        profiles=[],
    )
    with patch("app.core.supabase_client.get_supabase_client", return_value=store):
        yield store


class TestEventCrud:
    def test_create_event_mints_a_share_token(self, db):
        response = client.post(
            "/api/v1/combine/events",
            json={"event_name": "BS Combine 2026", "event_date": EVENT_DATE},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["share_token"]) >= 30  # ~144 bits of entropy
        assert data["share_url_path"] == f"/combine/live/{data['share_token']}"
        assert data["status"] == "draft"

    def test_create_event_defaults_are_sensible(self, db):
        response = client.post(
            "/api/v1/combine/events",
            json={"event_name": "BS Combine 2026", "event_date": EVENT_DATE},
        )
        data = response.json()
        assert data["landmine_reference_load_kg"] == 20
        assert data["airbike_score_basis"] == "w_per_kg"
        assert data["min_stations_for_overall"] == 3

    def test_list_events_counts_roster_and_attempts(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)
        db.data["combine_attempts"].append(
            {
                "id": str(uuid4()),
                "combine_event_id": event["id"],
                "participant_id": participant["id"],
                "station": "cmj",
                "attempt_number": 1,
                "measures": {"height_cm": 41.2},
                "voided_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        response = client.get("/api/v1/combine/events")
        assert response.status_code == 200
        item = response.json()[0]
        assert item["participant_count"] == 1
        assert item["attempt_count"] == 1

    def test_another_coachs_event_is_a_404(self, db):
        event = make_event(coach_id=str(uuid4()))
        db.data["combine_events"].append(event)
        assert client.get(f"/api/v1/combine/events/{event['id']}").status_code == 404

    def test_delete_event(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        assert client.delete(f"/api/v1/combine/events/{event['id']}").status_code == 204
        assert db.data["combine_events"] == []


class TestPublicDisplayConsent:
    def test_cannot_go_live_without_confirming_display_consent(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.patch(
            f"/api/v1/combine/events/{event['id']}", json={"status": "live"}
        )
        assert response.status_code == 400
        assert "public screen" in response.json()["detail"]

    def test_can_go_live_once_consent_is_confirmed_in_the_same_call(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={"status": "live", "public_display_consent_confirmed": True},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "live"
        assert response.json()["public_display_consent_confirmed_at"] is not None

    def test_can_go_live_when_consent_was_confirmed_earlier(self, db):
        event = make_event(public_display_consent_confirmed_at=datetime.now(timezone.utc).isoformat())
        db.data["combine_events"].append(event)
        response = client.patch(
            f"/api/v1/combine/events/{event['id']}", json={"status": "live"}
        )
        assert response.status_code == 200


class TestShareToken:
    def test_rotate_issues_a_new_token(self, db):
        event = make_event()
        original_token = event["share_token"]
        db.data["combine_events"].append(event)
        response = client.post(f"/api/v1/combine/events/{event['id']}/rotate-token")
        assert response.status_code == 200
        assert response.json()["share_token"] != original_token
        assert response.json()["share_revoked_at"] is None

    def test_revoke_marks_the_token_dead_without_replacing_it(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.post(f"/api/v1/combine/events/{event['id']}/revoke-token")
        assert response.status_code == 200
        assert response.json()["share_token"] == event["share_token"]
        assert response.json()["share_revoked_at"] is not None

    def test_rotate_clears_a_previous_revocation(self, db):
        event = make_event(share_revoked_at=datetime.now(timezone.utc).isoformat())
        db.data["combine_events"].append(event)
        response = client.post(f"/api/v1/combine/events/{event['id']}/rotate-token")
        assert response.json()["share_revoked_at"] is None


class TestRosterImport:
    ROWS = [
        {"first_name": "Jack", "surname": "Reid", "gender": "male", "weight_category": "57kg"},
        {"first_name": "Sam", "surname": "Okoro", "gender": "female", "weight_category": "60kg"},
    ]

    def test_creates_athletes_and_participants(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": self.ROWS},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_athletes"] == 2
        assert data["participants_added"] == 2
        assert len(db.data["athletes"]) == 2
        assert len(db.data["combine_participants"]) == 2

    def test_gender_is_required_per_row(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": [{"first_name": "Jack", "surname": "Reid"}]},
        )
        assert response.status_code == 422

    def test_dry_run_writes_nothing(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk?dry_run=true",
            json={"rows": self.ROWS},
        )
        assert response.status_code == 200
        assert response.json()["dry_run"] is True
        assert response.json()["participants_added"] == 2
        assert db.data["athletes"] == []
        assert db.data["combine_participants"] == []

    def test_links_to_an_existing_athlete_by_name(self, db):
        event = make_event()
        athlete = make_athlete("Jack Reid")
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": [self.ROWS[0]]},
        )
        data = response.json()
        assert data["linked_athletes"] == 1
        assert data["created_athletes"] == 0
        assert data["results"][0]["action"] == "linked"
        assert len(db.data["athletes"]) == 1

    def test_on_name_match_create_forces_a_new_athlete(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        db.data["athletes"].append(make_athlete("Jack Reid"))

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": [self.ROWS[0]], "on_name_match": "create"},
        )
        assert response.json()["created_athletes"] == 1
        assert len(db.data["athletes"]) == 2

    def test_bibs_auto_assign_and_never_collide(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": self.ROWS},
        )
        bibs = sorted(r["bib"] for r in response.json()["results"])
        assert bibs == [1, 2]

    def test_duplicate_bib_is_reported_not_raised(self, db):
        event = make_event()
        athlete = make_athlete()
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(make_participant(event, athlete, bib=7))

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": [{**self.ROWS[1], "bib": 7}]},
        )
        assert response.status_code == 200
        assert response.json()["results"][0]["action"] == "error"
        assert "Bib already used" in response.json()["results"][0]["reason"]

    def test_already_on_the_roster_is_skipped(self, db):
        event = make_event()
        athlete = make_athlete("Jack Reid")
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(make_participant(event, athlete))

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={"rows": [self.ROWS[0]]},
        )
        assert response.json()["results"][0]["action"] == "skipped"

    def test_row_cap(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        rows = [{"first_name": f"A{i}", "surname": "B", "gender": "male"} for i in range(201)]
        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk", json={"rows": rows}
        )
        assert response.status_code == 422


class TestAttempts:
    @pytest.fixture
    def setup(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)
        return db, event, participant

    def _submit(self, event, participant, measures, **extra):
        return client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={"participant_id": participant["id"], "measures": measures, **extra},
        )

    def test_cmj_attempt(self, setup):
        db, event, participant = setup
        response = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert response.status_code == 201
        assert response.json()["attempt_number"] == 1
        assert response.json()["value"] == 41.2
        assert response.json()["display_value"] == "41.2 cm"

    def test_attempt_numbers_increment(self, setup):
        db, event, participant = setup
        self._submit(event, participant, {"station": "cmj", "height_cm": 38.4})
        second = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert second.json()["attempt_number"] == 2

    def test_pogo_derives_rsi(self, setup):
        db, event, participant = setup
        response = self._submit(
            event,
            participant,
            {"station": "pogo", "flight_time_ms": 480, "contact_time_ms": 192},
        )
        assert response.status_code == 201
        assert response.json()["value"] == 2.5

    def test_pogo_needs_a_pair_or_an_rsi(self, setup):
        db, event, participant = setup
        response = self._submit(event, participant, {"station": "pogo", "flight_time_ms": 480})
        assert response.status_code == 422

    def test_air_bike_uses_the_17s_split(self, setup):
        db, event, participant = setup
        response = self._submit(
            event,
            participant,
            {
                "station": "air_bike",
                "sprint_number": 1,
                "power_7s": 855,
                "power_17s": 700,
                "power_27s": 600,
            },
        )
        assert response.status_code == 201
        assert response.json()["value"] == 15.0  # 855 W / 57 kg

    def test_a_mistyped_decimal_is_rejected_by_the_tight_range(self, setup):
        """The station cap is 90 cm, well under the registry's 200."""
        db, event, participant = setup
        response = self._submit(event, participant, {"station": "cmj", "height_cm": 412})
        assert response.status_code == 422

    def test_unknown_station_is_rejected(self, setup):
        db, event, participant = setup
        response = self._submit(event, participant, {"station": "shuttle", "time_s": 12})
        assert response.status_code == 422

    def test_duplicate_client_attempt_id_is_idempotent(self, setup):
        db, event, participant = setup
        client_id = str(uuid4())
        first = self._submit(
            event, participant, {"station": "cmj", "height_cm": 41.2}, client_attempt_id=client_id
        )
        second = self._submit(
            event, participant, {"station": "cmj", "height_cm": 41.2}, client_attempt_id=client_id
        )
        assert first.json()["id"] == second.json()["id"]
        assert len(db.data["combine_attempts"]) == 1

    def test_submit_bumps_results_updated_at(self, setup):
        db, event, participant = setup
        before = db.data["combine_events"][0]["results_updated_at"]
        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert db.data["combine_events"][0]["results_updated_at"] != before

    def test_attempt_for_a_participant_in_another_event_is_404(self, db):
        event = make_event()
        other_event = make_event()
        athlete = make_athlete()
        participant = make_participant(other_event, athlete)
        db.data["combine_events"].extend([event, other_event])
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={
                "participant_id": participant["id"],
                "measures": {"station": "cmj", "height_cm": 41.2},
            },
        )
        assert response.status_code == 404

    def test_void_keeps_the_row_and_marks_it(self, setup):
        db, event, participant = setup
        created = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        attempt_id = created.json()["id"]

        assert client.delete(f"/api/v1/combine/attempts/{attempt_id}").status_code == 204
        assert len(db.data["combine_attempts"]) == 1
        assert db.data["combine_attempts"][0]["voided_at"] is not None

    def test_hard_delete_removes_the_row(self, setup):
        db, event, participant = setup
        created = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        attempt_id = created.json()["id"]

        assert client.delete(f"/api/v1/combine/attempts/{attempt_id}?hard=true").status_code == 204
        assert db.data["combine_attempts"] == []

    def test_correcting_an_attempt(self, setup):
        db, event, participant = setup
        created = self._submit(event, participant, {"station": "cmj", "height_cm": 4.12})
        attempt_id = created.json()["id"]

        response = client.patch(
            f"/api/v1/combine/attempts/{attempt_id}",
            json={"measures": {"station": "cmj", "height_cm": 41.2}},
        )
        assert response.status_code == 200
        assert response.json()["value"] == 41.2

    def test_an_attempt_cannot_change_station(self, setup):
        db, event, participant = setup
        created = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        response = client.patch(
            f"/api/v1/combine/attempts/{created.json()['id']}",
            json={"measures": {"station": "grip", "left_kg": 45, "right_kg": 50}},
        )
        assert response.status_code == 400

    def test_listing_attempts_excludes_voided_by_default(self, setup):
        db, event, participant = setup
        first = self._submit(event, participant, {"station": "cmj", "height_cm": 38.4})
        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        client.delete(f"/api/v1/combine/attempts/{first.json()['id']}")

        listed = client.get(f"/api/v1/combine/events/{event['id']}/attempts")
        assert len(listed.json()) == 1
        with_voided = client.get(
            f"/api/v1/combine/events/{event['id']}/attempts?include_voided=true"
        )
        assert len(with_voided.json()) == 2


class TestStationRoster:
    def test_todo_first_then_done(self, db):
        event = make_event()
        a1, a2 = make_athlete("Jack Reid"), make_athlete("Sam Okoro")
        p1 = make_participant(event, a1, bib=1)
        p2 = make_participant(event, a2, bib=2)
        db.data["combine_events"].append(event)
        db.data["athletes"].extend([a1, a2])
        db.data["combine_participants"].extend([p1, p2])

        client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={"participant_id": p1["id"], "measures": {"station": "cmj", "height_cm": 41.2}},
        )

        response = client.get(f"/api/v1/combine/events/{event['id']}/stations/cmj/roster")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["done"] == 1
        assert data["entries"][0]["status"] == "todo"
        assert data["entries"][0]["name"] == "Sam Okoro"
        assert data["entries"][1]["best_display"] == "41.2 cm"

    def test_withdrawn_participants_are_off_the_station_list(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(
            event, athlete, withdrawn_at=datetime.now(timezone.utc).isoformat()
        )
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)

        response = client.get(f"/api/v1/combine/events/{event['id']}/stations/cmj/roster")
        assert response.json()["total"] == 0


class TestPromotion:
    @pytest.fixture
    def setup(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)
        return db, event, participant, athlete

    def _submit(self, event, participant, measures):
        return client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={"participant_id": participant["id"], "measures": measures},
        )

    def test_best_cmj_is_promoted_to_performance_events(self, setup):
        db, event, participant, athlete = setup
        self._submit(event, participant, {"station": "cmj", "height_cm": 38.4})
        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        rows = db.data["performance_events"]
        assert len(rows) == 1, "one row per athlete per combine, not one per attempt"
        assert rows[0]["metrics"]["height_cm"] == 41.2
        assert rows[0]["combine_event_id"] == event["id"]

    def test_two_stations_merge_into_one_row(self, setup):
        db, event, participant, athlete = setup
        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        self._submit(event, participant, {"station": "grip", "left_kg": 45, "right_kg": 50})

        assert len(db.data["performance_events"]) == 1
        metrics = db.data["performance_events"][0]["metrics"]
        assert metrics["height_cm"] == 41.2
        assert metrics["grip_strength_right_kg"] == 50
        assert metrics["test_type"] == "Combine"

    def test_pogo_promotes_its_own_keys_not_cmj_rsi(self, setup):
        db, event, participant, athlete = setup
        self._submit(
            event, participant, {"station": "pogo", "flight_time_ms": 480, "contact_time_ms": 192}
        )
        metrics = db.data["performance_events"][0]["metrics"]
        assert metrics["pogo_rsi"] == 2.5
        assert metrics["pogo_flight_time_ms"] == 480
        assert "rsi" not in metrics

    def test_landmine_promotes_a_vbt_profile_with_one_set_per_load(self, setup):
        db, event, participant, athlete = setup
        self._submit(
            event, participant, {"station": "landmine", "load_kg": 15, "peak_velocity_ms": 4.5}
        )
        self._submit(
            event, participant, {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.0}
        )
        self._submit(
            event, participant, {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.2}
        )

        assert len(db.data["vbt_profiles"]) == 1
        sets = db.data["vbt_sets"]
        assert len(sets) == 2
        by_load = {s["load_kg"]: s["peak_velocity_ms"] for s in sets}
        assert by_load == {15.0: 4.5, 20.0: 4.2}

    def test_air_bike_promotes_a_7_17_27_test(self, setup):
        db, event, participant, athlete = setup
        self._submit(
            event,
            participant,
            {
                "station": "air_bike",
                "sprint_number": 1,
                "power_7s": 855,
                "power_17s": 700,
                "power_27s": 600,
            },
        )
        tests = db.data["air_bike_tests"]
        assert len(tests) == 1
        assert tests[0]["split_scheme"] == "7_17_27"
        sprints = db.data["air_bike_sprints"]
        assert sprints[0]["power_17s"] == 700
        assert sprints[0].get("power_14s") is None

    def test_voiding_the_only_attempt_clears_the_promoted_row(self, setup):
        db, event, participant, athlete = setup
        created = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert len(db.data["performance_events"]) == 1

        client.delete(f"/api/v1/combine/attempts/{created.json()['id']}")
        assert db.data["performance_events"] == []

    def test_voiding_the_best_falls_back_to_the_next_best(self, setup):
        db, event, participant, athlete = setup
        self._submit(event, participant, {"station": "cmj", "height_cm": 38.4})
        best = self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        client.delete(f"/api/v1/combine/attempts/{best.json()['id']}")
        assert db.data["performance_events"][0]["metrics"]["height_cm"] == 38.4

    def test_sync_is_idempotent(self, setup):
        db, event, participant, athlete = setup
        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        client.post(f"/api/v1/combine/events/{event['id']}/sync")
        client.post(f"/api/v1/combine/events/{event['id']}/sync")

        assert len(db.data["performance_events"]) == 1
        assert db.data["performance_events"][0]["metrics"]["height_cm"] == 41.2


class TestPromotionLeavesManualRowsAlone:
    """A combine save must never edit or delete a row it did not create.

    Both side tables are unique on (athlete, date), and `vbt_profiles` on
    (athlete, exercise, date). An athlete tested by their own coach on the morning of
    the combine therefore has a row the promotion would otherwise hijack — and a void
    would then delete real data that no re-sync can bring back.
    """

    @pytest.fixture
    def setup(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)
        return db, event, participant, athlete

    def _submit(self, event, participant, measures):
        return client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={"participant_id": participant["id"], "measures": measures},
        )

    @staticmethod
    def _manual_bike_test(db, athlete):
        test = {
            "id": str(uuid4()),
            "athlete_id": athlete["id"],
            "test_date": EVENT_DATE,
            "body_mass_kg": 57.0,
            "split_scheme": "7_14_27",
            "combine_event_id": None,
        }
        db.data["air_bike_tests"].append(test)
        db.data["air_bike_sprints"].append(
            {
                "id": str(uuid4()),
                "test_id": test["id"],
                "sprint_number": 1,
                "power_7s": 700,
                "power_14s": 600,
                "power_27s": 500,
            }
        )
        return test

    @staticmethod
    def _manual_landmine_profile(db, athlete):
        profile = {
            "id": str(uuid4()),
            "athlete_id": athlete["id"],
            "exercise_name": "Landmine Punch Throw",
            "profile_date": EVENT_DATE,
            "combine_event_id": None,
        }
        db.data["vbt_profiles"].append(profile)
        db.data["vbt_sets"].append(
            {
                "id": str(uuid4()),
                "profile_id": profile["id"],
                "set_number": 1,
                "load_kg": 20.0,
                "peak_velocity_ms": 3.9,
            }
        )
        return profile

    def test_a_manual_same_day_bike_test_survives_a_cmj_save(self, setup):
        db, event, participant, athlete = setup
        manual = self._manual_bike_test(db, athlete)

        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        assert db.data["air_bike_tests"] == [manual]
        assert len(db.data["air_bike_sprints"]) == 1

    def test_a_manual_same_day_bike_test_survives_a_bike_save_and_void(self, setup):
        db, event, participant, athlete = setup
        manual = self._manual_bike_test(db, athlete)

        created = self._submit(
            event,
            participant,
            {
                "station": "air_bike",
                "sprint_number": 1,
                "power_7s": 855,
                "power_17s": 700,
                "power_27s": 600,
            },
        )
        assert created.status_code == 201, "the attempt is stored even if promotion cannot land"
        assert db.data["air_bike_tests"] == [manual]
        assert [s["power_7s"] for s in db.data["air_bike_sprints"]] == [700]

        client.delete(f"/api/v1/combine/attempts/{created.json()['id']}")
        assert db.data["air_bike_tests"] == [manual]

    def test_a_manual_landmine_profile_survives_a_landmine_save(self, setup):
        db, event, participant, athlete = setup
        manual = self._manual_landmine_profile(db, athlete)

        created = self._submit(
            event, participant, {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.5}
        )
        assert created.status_code == 201
        assert db.data["vbt_profiles"] == [manual]
        assert [s["peak_velocity_ms"] for s in db.data["vbt_sets"]] == [3.9]

    def test_voiding_a_landmine_attempt_leaves_a_manual_profile_alone(self, setup):
        db, event, participant, athlete = setup
        manual = self._manual_landmine_profile(db, athlete)

        created = self._submit(
            event,
            participant,
            {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.5, "side": "left"},
        )
        assert {p["exercise_name"] for p in db.data["vbt_profiles"]} == {
            "Landmine Punch Throw",
            "Landmine Punch Throw (Left)",
        }

        client.delete(f"/api/v1/combine/attempts/{created.json()['id']}")
        assert db.data["vbt_profiles"] == [manual]

    def test_deleting_the_event_keeps_the_promoted_row_and_clears_the_tag(self, setup):
        db, event, participant, athlete = setup
        self._submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        client.delete(f"/api/v1/combine/events/{event['id']}")

        rows = db.data["performance_events"]
        assert len(rows) == 1, "ON DELETE SET NULL — the athlete keeps their result"
        assert rows[0]["combine_event_id"] is None


class TestLandmineSides:
    """One VBT profile per side, so the two arms are not averaged into one line."""

    @pytest.fixture
    def setup(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)
        return db, event, participant, athlete

    def _throw(self, event, participant, **measures):
        return client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={
                "participant_id": participant["id"],
                "measures": {"station": "landmine", "load_kg": 20, **measures},
            },
        )

    def test_each_side_gets_its_own_profile(self, setup):
        db, event, participant, athlete = setup
        self._throw(event, participant, peak_velocity_ms=4.5, side="left")
        self._throw(event, participant, peak_velocity_ms=4.2, side="right")

        by_name = {p["exercise_name"]: p["id"] for p in db.data["vbt_profiles"]}
        assert set(by_name) == {"Landmine Punch Throw (Left)", "Landmine Punch Throw (Right)"}
        velocities = {
            s["profile_id"]: s["peak_velocity_ms"] for s in db.data["vbt_sets"]
        }
        assert velocities[by_name["Landmine Punch Throw (Left)"]] == 4.5
        assert velocities[by_name["Landmine Punch Throw (Right)"]] == 4.2

    def test_an_attempt_without_a_side_keeps_the_bare_exercise_name(self, setup):
        db, event, participant, athlete = setup
        self._throw(event, participant, peak_velocity_ms=4.5)

        assert [p["exercise_name"] for p in db.data["vbt_profiles"]] == ["Landmine Punch Throw"]

    def test_voiding_a_side_deletes_only_that_sides_profile(self, setup):
        db, event, participant, athlete = setup
        left = self._throw(event, participant, peak_velocity_ms=4.5, side="left")
        self._throw(event, participant, peak_velocity_ms=4.2, side="right")

        client.delete(f"/api/v1/combine/attempts/{left.json()['id']}")

        assert [p["exercise_name"] for p in db.data["vbt_profiles"]] == [
            "Landmine Punch Throw (Right)"
        ]
        assert [s["peak_velocity_ms"] for s in db.data["vbt_sets"]] == [4.2]


class TestStationScopedPromotion:
    """The hot path writes the station just saved, not a stale snapshot of all four.

    Called directly rather than through the API: the router passes the station down,
    and these assert what promotion does with it either way.
    """

    def _seeded(self):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db = FakeSupabase(
            combine_events=[event],
            athletes=[athlete],
            combine_participants=[participant],
            combine_attempts=[],
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
        )
        return db, event, participant

    def test_a_station_save_merges_only_that_stations_keys(self):
        db, event, participant = self._seeded()
        attempts = [
            make_attempt(event, participant, "cmj", {"height_cm": 41.2}),
            make_attempt(event, participant, "grip", {"left_kg": 45, "right_kg": 50}),
        ]

        combine_promotion.promote_participant(
            db, event=event, participant=participant, attempts=attempts, station="grip"
        )

        assert len(db.rpc_calls) == 1
        _, params = db.rpc_calls[0]
        assert set(params["p_metrics"]) == {
            "grip_strength_left_kg",
            "grip_strength_right_kg",
            "test_type",
        }

    def test_a_cmj_save_leaves_the_side_tables_alone(self):
        db, event, participant = self._seeded()
        attempts = [
            make_attempt(event, participant, "cmj", {"height_cm": 41.2}),
            make_attempt(
                event,
                participant,
                "landmine",
                {"load_kg": 20, "peak_velocity_ms": 4.5, "side": "left"},
            ),
            make_attempt(
                event,
                participant,
                "air_bike",
                {"sprint_number": 1, "power_7s": 855, "power_17s": 700, "power_27s": 600},
            ),
        ]
        combine_promotion.promote_participant(
            db, event=event, participant=participant, attempts=attempts, merge=False
        )
        set_ids = {s["id"] for s in db.data["vbt_sets"]}
        sprint_ids = {s["id"] for s in db.data["air_bike_sprints"]}
        assert set_ids and sprint_ids

        combine_promotion.promote_participant(
            db, event=event, participant=participant, attempts=attempts, station="cmj"
        )

        assert {s["id"] for s in db.data["vbt_sets"]} == set_ids
        assert {s["id"] for s in db.data["air_bike_sprints"]} == sprint_ids

    def test_a_bike_save_writes_no_shell_performance_event(self):
        db, event, participant = self._seeded()
        attempts = [
            make_attempt(
                event,
                participant,
                "air_bike",
                {"sprint_number": 1, "power_7s": 855, "power_17s": 700, "power_27s": 600},
            )
        ]

        combine_promotion.promote_participant(
            db, event=event, participant=participant, attempts=attempts, station="air_bike"
        )

        assert db.rpc_calls == []
        assert db.data["performance_events"] == []
        assert len(db.data["air_bike_tests"]) == 1

    def test_a_void_rebuilds_every_station(self):
        db, event, participant = self._seeded()
        cmj = make_attempt(event, participant, "cmj", {"height_cm": 41.2})
        throw = make_attempt(
            event, participant, "landmine", {"load_kg": 20, "peak_velocity_ms": 4.5}
        )
        combine_promotion.promote_participant(
            db, event=event, participant=participant, attempts=[cmj, throw], merge=False
        )
        assert len(db.data["vbt_profiles"]) == 1

        throw["voided_at"] = datetime.now(timezone.utc).isoformat()
        combine_promotion.promote_participant(
            db,
            event=event,
            participant=participant,
            attempts=[cmj, throw],
            merge=False,
            station="cmj",
        )

        assert db.data["vbt_profiles"] == [], "a void must clear a station, whatever it names"


class TestPromotionFailuresAreVisible:
    """A promotion that cannot write says so, instead of failing silently."""

    def _seeded(self, failing_table, participants=1):
        event = make_event()
        athletes = [make_athlete(f"Boxer{i}") for i in range(participants)]
        roster = [make_participant(event, a, bib=i + 1) for i, a in enumerate(athletes)]
        db = FailingStore(
            failing_table=failing_table,
            combine_events=[event],
            athletes=athletes,
            combine_participants=roster,
            combine_attempts=[],
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
        )
        return db, event, roster

    def test_promote_participant_names_the_target_that_failed(self):
        db, event, roster = self._seeded("vbt_profiles")
        participant = roster[0]
        attempts = [
            make_attempt(event, participant, "cmj", {"height_cm": 41.2}),
            make_attempt(
                event, participant, "landmine", {"load_kg": 20, "peak_velocity_ms": 4.5}
            ),
        ]

        failed = combine_promotion.promote_participant(
            db, event=event, participant=participant, attempts=attempts, merge=False
        )

        assert failed == ["landmine"]
        assert db.data["performance_events"][0]["metrics"]["height_cm"] == 41.2

    def test_promote_event_counts_only_the_participants_that_failed(self):
        """One boxer's bike write fails; the other's jump lands, so the count is 1."""
        db, event, roster = self._seeded("air_bike_sprints", participants=2)
        attempts = [
            make_attempt(
                event,
                roster[0],
                "air_bike",
                {"sprint_number": 1, "power_7s": 855, "power_17s": 700, "power_27s": 600},
            ),
            make_attempt(event, roster[1], "cmj", {"height_cm": 41.2}),
        ]

        unsynced = combine_promotion.promote_event(
            db, event=event, participants=roster, attempts=attempts
        )

        assert unsynced == 1
        assert db.data["performance_events"][0]["metrics"]["height_cm"] == 41.2

    def test_a_failed_station_save_is_reported_by_the_next_sync(self):
        """The 201 keeps the attempt safe, and the station screen shows nothing wrong.

        `unsynced_count` on the Re-sync response is therefore the only thing that
        tells a human the bike result never reached the athlete's record.
        """
        db, event, roster = self._seeded("air_bike_sprints")
        participant = roster[0]

        with patch("app.core.supabase_client.get_supabase_client", return_value=db):
            created = client.post(
                f"/api/v1/combine/events/{event['id']}/attempts",
                json={
                    "participant_id": participant["id"],
                    "measures": {
                        "station": "air_bike",
                        "sprint_number": 1,
                        "power_7s": 855,
                        "power_17s": 700,
                        "power_27s": 600,
                    },
                },
            )
            assert created.status_code == 201, "the attempt is stored even if promotion fails"
            assert db.data["air_bike_sprints"] == []

            synced = client.post(f"/api/v1/combine/events/{event['id']}/sync")

        assert synced.status_code == 200
        assert synced.json()["unsynced_count"] == 1


class TestWithdrawnParticipants:
    def test_a_withdrawn_boxer_keeps_their_promoted_results(self, db):
        """Withdrawing takes someone off the board; it does not unmake what they did."""
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)

        for measures in (
            {"station": "cmj", "height_cm": 41.2},
            {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.5, "side": "left"},
            {
                "station": "air_bike",
                "sprint_number": 1,
                "power_7s": 855,
                "power_17s": 700,
                "power_27s": 600,
            },
        ):
            client.post(
                f"/api/v1/combine/events/{event['id']}/attempts",
                json={"participant_id": participant["id"], "measures": measures},
            )

        db.data["combine_participants"][0]["withdrawn_at"] = datetime.now(timezone.utc).isoformat()
        client.post(f"/api/v1/combine/events/{event['id']}/sync")

        assert db.data["performance_events"][0]["metrics"]["height_cm"] == 41.2
        assert len(db.data["vbt_profiles"]) == 1
        assert len(db.data["air_bike_tests"]) == 1


class TestLeaderboardEndpoint:
    def test_authenticated_board_includes_identifiers(self, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)
        client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={
                "participant_id": participant["id"],
                "measures": {"station": "cmj", "height_cm": 41.2},
            },
        )

        response = client.get(f"/api/v1/combine/events/{event['id']}/leaderboard")
        assert response.status_code == 200
        cmj = next(p for p in response.json()["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["participant_id"] == participant["id"]
        assert cmj["results"][0]["display_name"] == "Jack Reid"

    def test_a_loosely_typed_filter_still_narrows_the_board(self, db):
        """`57 KG` is the roster import's own vocabulary; the filter reads it too."""
        event, athlete, participant = seed_event(db)
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        response = client.get(
            f"/api/v1/combine/events/{event['id']}/leaderboard?weight_category=57%20KG"
        )

        assert response.status_code == 200
        cmj = next(p for p in response.json()["stations"] if p["station"] == "cmj")
        assert [r["display_name"] for r in cmj["results"]] == ["Jack Reid"]

    def test_leaderboard_for_another_coachs_event_is_404(self, db):
        event = make_event(coach_id=str(uuid4()))
        db.data["combine_events"].append(event)
        assert (
            client.get(f"/api/v1/combine/events/{event['id']}/leaderboard").status_code == 404
        )


class TestRoleGuards:
    def test_athlete_cannot_create_an_event(self, athlete_client, db):
        response = athlete_client.post(
            "/api/v1/combine/events",
            json={"event_name": "BS Combine 2026", "event_date": EVENT_DATE},
        )
        assert response.status_code == 403

    def test_athlete_cannot_submit_attempts(self, athlete_client, db):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db.data["combine_events"].append(event)
        db.data["athletes"].append(athlete)
        db.data["combine_participants"].append(participant)

        response = athlete_client.post(
            f"/api/v1/combine/events/{event['id']}/attempts",
            json={
                "participant_id": participant["id"],
                "measures": {"station": "cmj", "height_cm": 41.2},
            },
        )
        assert response.status_code == 403

    def test_refresh_norms_requires_admin(self, db):
        event = make_event()
        db.data["combine_events"].append(event)
        response = client.post(f"/api/v1/combine/events/{event['id']}/refresh-norms")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Shared helpers for the event-day hardening tests below
# ---------------------------------------------------------------------------


def seed_event(db, **overrides):
    """An event with one athlete and one boxer on the roster."""
    event = make_event(**overrides)
    athlete = make_athlete()
    participant = make_participant(event, athlete)
    db.data["combine_events"].append(event)
    db.data["athletes"].append(athlete)
    db.data["combine_participants"].append(participant)
    return event, athlete, participant


def submit(event, participant, measures, **extra):
    return client.post(
        f"/api/v1/combine/events/{event['id']}/attempts",
        json={"participant_id": participant["id"], "measures": measures, **extra},
    )


class TestParticipantDeleteGuard:
    """Removing a boxer cascades their attempts away; nothing brings those back."""

    def test_a_boxer_with_attempts_cannot_be_deleted(self, db):
        event, _, participant = seed_event(db)
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        response = client.delete(f"/api/v1/combine/participants/{participant['id']}")

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "This boxer has logged attempts — mark them withdrawn instead"
        )
        assert len(db.data["combine_participants"]) == 1
        assert len(db.data["combine_attempts"]) == 1

    def test_a_voided_attempt_still_blocks_the_delete(self, db):
        """The void is the audit trail of what happened on the day."""
        event, _, participant = seed_event(db)
        created = submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        client.delete(f"/api/v1/combine/attempts/{created.json()['id']}")

        response = client.delete(f"/api/v1/combine/participants/{participant['id']}")
        assert response.status_code == 409

    def test_a_boxer_with_no_attempts_is_still_removable(self, db):
        event, _, participant = seed_event(db)
        assert (
            client.delete(f"/api/v1/combine/participants/{participant['id']}").status_code
            == 204
        )
        assert db.data["combine_participants"] == []


class TestLateWeighIn:
    def test_a_weigh_in_after_a_bike_save_creates_the_test(self, db):
        """`air_bike_tests.body_mass_kg` is NOT NULL, so the sprint had nowhere to go."""
        event, _, participant = seed_event(db)
        db.data["combine_participants"][0]["body_mass_kg"] = None

        created = submit(
            event,
            participant,
            {
                "station": "air_bike",
                "sprint_number": 1,
                "power_7s": 855,
                "power_17s": 700,
                "power_27s": 600,
            },
        )
        assert created.status_code == 201
        assert created.json()["value"] is None
        assert created.json()["display_value"] == "855 W · S1"
        assert db.data["air_bike_tests"] == []

        response = client.patch(
            f"/api/v1/combine/participants/{participant['id']}", json={"body_mass_kg": 57}
        )

        assert response.status_code == 200
        assert len(db.data["air_bike_tests"]) == 1
        assert db.data["air_bike_tests"][0]["body_mass_kg"] == 57
        assert [s["power_7s"] for s in db.data["air_bike_sprints"]] == [855]

    def test_a_weigh_in_does_not_rewrite_the_promoted_metrics_row(self):
        """Body mass only rescales W/kg, so the weigh-in has no business rebuilding
        `performance_events`. That read-modify-write is not atomic against the RPC
        the station saves use, so it can drop a station saved in the same moment."""
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        store = WriteLog(
            combine_events=[event],
            athletes=[athlete],
            combine_participants=[participant],
            combine_attempts=[],
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
            profiles=[],
        )

        with patch("app.core.supabase_client.get_supabase_client", return_value=store):
            submit(event, participant, {"station": "cmj", "height_cm": 41.2})
            store.writes.clear()
            response = client.patch(
                f"/api/v1/combine/participants/{participant['id']}", json={"body_mass_kg": 58}
            )

        assert response.status_code == 200
        assert [w for w in store.writes if w[0] == "performance_events"] == []
        assert store.data["performance_events"][0]["metrics"]["height_cm"] == 41.2


class TestSyncReportsPromotionFailures:
    def test_sync_counts_the_participants_that_did_not_land(self):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        db = FailingStore(
            failing_table="air_bike_sprints",
            combine_events=[event],
            athletes=[athlete],
            combine_participants=[participant],
            combine_attempts=[
                make_attempt(
                    event,
                    participant,
                    "air_bike",
                    {
                        "sprint_number": 1,
                        "power_7s": 855,
                        "power_17s": 700,
                        "power_27s": 600,
                    },
                )
            ],
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
        )

        with patch("app.core.supabase_client.get_supabase_client", return_value=db):
            response = client.post(f"/api/v1/combine/events/{event['id']}/sync")

        assert response.status_code == 200
        assert response.json()["unsynced_count"] == 1

    def test_a_clean_sync_reports_nothing_unsynced(self, db):
        event, _, participant = seed_event(db)
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        response = client.post(f"/api/v1/combine/events/{event['id']}/sync")
        assert response.json()["unsynced_count"] == 0


class TestStationScopedHotPath:
    def test_a_save_merges_only_the_station_just_saved(self, db):
        """Two iPads on two stations must not roll each other's best back."""
        event, _, participant = seed_event(db)
        submit(event, participant, {"station": "grip", "left_kg": 45, "right_kg": 50})
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        _, params = db.rpc_calls[-1]
        assert set(params["p_metrics"]) == {"height_cm", "test_type"}
        metrics = db.data["performance_events"][0]["metrics"]
        assert metrics["height_cm"] == 41.2
        assert metrics["grip_strength_right_kg"] == 50


class RacingStore(FakeSupabase):
    """One insert loses a race with the other uvicorn worker.

    The winning row lands first, then the losing insert raises a 23505 carrying a
    `.code`, exactly as postgrest does — which is what two iPads saving at the same
    moment actually produce.
    """

    def __init__(self, *, winner: dict, **tables):
        super().__init__(**tables)
        self.winner = winner
        self.races_left = 1

    def table(self, name: str):
        handle = super().table(name)
        if name != "combine_attempts":
            return handle
        store = self
        inner = handle.execute

        def execute():
            if handle.op == "insert" and store.races_left:
                store.races_left -= 1
                store.data["combine_attempts"].append(dict(store.winner))
                raise FakeApiError(
                    "23505", "duplicate key value violates unique constraint"
                )
            return inner()

        handle.execute = execute
        return handle


class TestAttemptInsertRaces:
    """A lost race must never cost an attempt, duplicate one, or return a 500."""

    @staticmethod
    def _store(event, athlete, participant, winner):
        return RacingStore(
            winner=winner,
            combine_events=[event],
            athletes=[athlete],
            combine_participants=[participant],
            combine_attempts=[],
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
        )

    def test_the_same_client_id_returns_the_row_the_other_worker_wrote(self):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        client_attempt_id = str(uuid4())
        winner = make_attempt(
            event,
            participant,
            "cmj",
            {"height_cm": 41.2},
            client_attempt_id=client_attempt_id,
        )
        db = self._store(event, athlete, participant, winner)

        with patch("app.core.supabase_client.get_supabase_client", return_value=db):
            response = submit(
                event,
                participant,
                {"station": "cmj", "height_cm": 41.2},
                client_attempt_id=client_attempt_id,
            )

        assert response.status_code == 201
        assert response.json()["id"] == winner["id"]
        assert len(db.data["combine_attempts"]) == 1

    def test_a_taken_attempt_number_is_retried_with_the_next_one(self):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        winner = make_attempt(event, participant, "cmj", {"height_cm": 38.4})
        db = self._store(event, athlete, participant, winner)

        with patch("app.core.supabase_client.get_supabase_client", return_value=db):
            response = submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        assert response.status_code == 201
        assert response.json()["attempt_number"] == 2
        assert len(db.data["combine_attempts"]) == 2


class TestAttemptCap:
    @staticmethod
    def _seed_attempts(db, event, participant, count):
        db.data["combine_attempts"].extend(
            make_attempt(
                event, participant, "cmj", {"height_cm": 30.0}, attempt_number=n + 1
            )
            for n in range(count)
        )

    def test_forty_attempts_are_allowed_at_one_station(self, db):
        """Both landmine sides and a re-run put a real boxer well past twenty."""
        event, _, participant = seed_event(db)
        self._seed_attempts(db, event, participant, 39)

        response = submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert response.status_code == 201
        assert response.json()["attempt_number"] == 40

    def test_the_forty_first_is_refused(self, db):
        event, _, participant = seed_event(db)
        self._seed_attempts(db, event, participant, 40)

        response = submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert response.status_code == 400
        assert "40 attempts" in response.json()["detail"]


class TestPagedReads:
    """PostgREST truncates an unpaginated select at db-max-rows, and says nothing."""

    @staticmethod
    def _id(n: int) -> str:
        """A sortable uuid-shaped id — pages come back ordered by `id`."""
        return f"{n:08x}-0000-4000-8000-000000000000"

    def test_every_attempt_reaches_the_board(self):
        event = make_event()
        athlete = make_athlete()
        participant = make_participant(event, athlete)
        attempts = [
            {
                "id": self._id(n),
                "combine_event_id": event["id"],
                "participant_id": participant["id"],
                "station": "cmj",
                "attempt_number": (n % 40) + 1,
                "measures": {"height_cm": 30.0},
                "voided_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for n in range(2500)
        ]
        attempts[-1]["measures"] = {"height_cm": 61.5}  # the best, on the third page
        db = FakeSupabase(
            max_rows=1000,
            combine_events=[event],
            athletes=[athlete],
            combine_participants=[participant],
            combine_attempts=attempts,
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
        )

        with patch("app.core.supabase_client.get_supabase_client", return_value=db):
            response = client.get(f"/api/v1/combine/events/{event['id']}/leaderboard")

        cmj = next(p for p in response.json()["stations"] if p["station"] == "cmj")
        assert cmj["results"][0]["value"] == 61.5
        assert cmj["results"][0]["attempts"] == 2500

    def test_the_import_sees_athletes_past_the_first_page(self):
        """An admin can own more than 1000 athletes, and the duplicate check is the
        only thing between a paste and forty duplicate athlete records."""
        event = make_event()
        athletes = [
            {**make_athlete(f"Boxer{n} Test"), "id": self._id(n)} for n in range(1200)
        ]
        athletes[-1] = {**make_athlete("Jack Reid"), "id": self._id(1199)}
        db = FakeSupabase(
            max_rows=1000,
            combine_events=[event],
            athletes=athletes,
            combine_participants=[],
            combine_attempts=[],
            performance_events=[],
            vbt_profiles=[],
            vbt_sets=[],
            air_bike_tests=[],
            air_bike_sprints=[],
        )

        with patch("app.core.supabase_client.get_supabase_client", return_value=db):
            response = client.post(
                f"/api/v1/combine/events/{event['id']}/participants/bulk?dry_run=true",
                json={
                    "rows": [
                        {"first_name": "Jack", "surname": "Reid", "gender": "male"}
                    ]
                },
            )

        assert response.json()["results"][0]["action"] == "linked"
        assert response.json()["created_athletes"] == 0


class TestEventDateChanges:
    DATE_CONFLICT = (
        "Results are already logged for this event — the date can no longer change"
    )

    def test_moving_the_date_moves_the_share_link_expiry(self, db):
        event, _, _ = seed_event(
            db,
            status="live",
            public_display_consent_confirmed_at=datetime.now(timezone.utc).isoformat(),
            share_token_expires_at=_past(),
        )
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 404

        new_date = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        response = client.patch(
            f"/api/v1/combine/events/{event['id']}", json={"event_date": new_date}
        )

        assert response.status_code == 200
        assert response.json()["event_date"] == new_date
        assert client.get(f"/api/v1/combine/public/{event['share_token']}").status_code == 200

    def test_the_date_cannot_move_once_attempts_exist(self, db):
        """Promoted rows are keyed on the event date; moving it orphans them."""
        event, _, participant = seed_event(db)
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}", json={"event_date": "2026-09-24"}
        )

        assert response.status_code == 409
        assert response.json()["detail"] == self.DATE_CONFLICT
        assert db.data["combine_events"][0]["event_date"] == EVENT_DATE

    def test_resending_the_same_date_is_not_a_conflict(self, db):
        """The console PATCHes the whole settings form, date included."""
        event, _, participant = seed_event(db)
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={"event_date": EVENT_DATE, "venue": "English Institute of Sport"},
        )
        assert response.status_code == 200
        assert response.json()["venue"] == "English Institute of Sport"


class TestLandmineReferenceLoad:
    """The reference load must stay on the ladder across a partial PATCH.

    The console PATCHes the ladder and the reference load separately, so a merged
    check is the only place that sees both. Everything downstream still works if
    they disagree — throws save, chips fill, VBT profiles are promoted — and only
    the board is silently empty.
    """

    def test_a_new_ladder_that_orphans_the_reference_load_is_refused(self, db):
        event, _, _ = seed_event(db)  # ladder 10/15/20/25, reference 20

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={"landmine_loads_kg": [12, 17, 22, 27]},
        )

        assert response.status_code == 422
        assert "22" in response.json()["detail"]  # names the nearest ladder load
        assert db.data["combine_events"][0]["landmine_loads_kg"] == [10, 15, 20, 25]

    def test_a_reference_load_off_the_current_ladder_is_refused(self, db):
        event, _, _ = seed_event(db)

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={"landmine_reference_load_kg": 22},
        )

        assert response.status_code == 422
        assert db.data["combine_events"][0]["landmine_reference_load_kg"] == 20

    def test_the_ladder_and_the_reference_can_move_together(self, db):
        event, _, _ = seed_event(db)

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={
                "landmine_loads_kg": [12, 17, 22, 27],
                "landmine_reference_load_kg": 22,
            },
        )

        assert response.status_code == 200
        assert response.json()["landmine_loads_kg"] == [12, 17, 22, 27]
        assert response.json()["landmine_reference_load_kg"] == 22

    def test_a_reference_between_two_loads_is_fine_within_tolerance(self, db):
        event, _, _ = seed_event(db)

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={
                "landmine_loads_kg": [12, 17, 22, 27],
                "landmine_reference_load_kg": 22.5,
                "landmine_reference_tolerance_kg": 1,
            },
        )

        assert response.status_code == 200

    def test_a_widened_tolerance_can_keep_the_existing_reference(self, db):
        """|22 - 20| = 2, so a 2 kg tolerance covers the new ladder."""
        event, _, _ = seed_event(db)

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={
                "landmine_loads_kg": [12, 17, 22, 27],
                "landmine_reference_tolerance_kg": 2,
            },
        )

        assert response.status_code == 200

    def test_an_empty_ladder_is_refused(self, db):
        """The station screen would render a ladder with no loads on it."""
        event, _, _ = seed_event(db)

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}", json={"landmine_loads_kg": []}
        )

        assert response.status_code == 422
        assert db.data["combine_events"][0]["landmine_loads_kg"] == [10, 15, 20, 25]

    def test_a_patch_that_leaves_the_landmine_alone_is_not_blocked(self, db):
        """An event already misconfigured must stay editable — including to fix it."""
        event, _, _ = seed_event(
            db, landmine_loads_kg=[12, 17, 22, 27], landmine_reference_load_kg=20
        )

        response = client.patch(
            f"/api/v1/combine/events/{event['id']}", json={"venue": "EIS"}
        )

        assert response.status_code == 200
        assert response.json()["venue"] == "EIS"


class TestNormsCoverage:
    SNAPSHOT = {
        "height_cm": {
            "mean": 38.0,
            "sd": 5.0,
            "n": 46,
            "by_gender": {
                "male": {"mean": 38.5, "sd": 5.0, "n": 30},
                "female": {"mean": 33.0, "sd": 4.0, "n": 16},
            },
        }
    }

    def test_the_event_reports_how_many_athletes_back_each_band(self, db):
        event = make_event(bs_norms_snapshot=self.SNAPSHOT)
        db.data["combine_events"].append(event)

        response = client.get(f"/api/v1/combine/events/{event['id']}")

        coverage = response.json()["bs_norms_coverage"]
        assert coverage["height_cm"] == {"male": 30, "female": 16}
        # A station with no norms at all is what the console most needs to name, so
        # it is reported at zero rather than left out of the answer.
        assert coverage["air_bike_power_7s_wkg"] == {"male": 0, "female": 0}

    def test_coverage_carries_counts_and_never_the_distribution(self, db):
        event = make_event(bs_norms_snapshot=self.SNAPSHOT)
        db.data["combine_events"].append(event)

        response = client.get(f"/api/v1/combine/events/{event['id']}")

        # Timestamps dropped before the scan: `results_updated_at` carries microseconds,
        # so a second ending "38.5" would fail a test about the snapshot's mean.
        values = json.dumps({k: v for k, v in response.json().items() if not k.endswith("_at")})
        assert "38.5" not in values, "the snapshot's mean must not be echoed"
        assert "bs_norms_snapshot" not in response.text


class TestWeightCategories:
    def test_a_loosely_typed_category_is_normalised(self, db):
        event = make_event()
        db.data["combine_events"].append(event)

        client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={
                "rows": [
                    {
                        "first_name": "Jack",
                        "surname": "Reid",
                        "gender": "male",
                        "weight_category": "57 KG",
                    }
                ]
            },
        )

        assert db.data["combine_participants"][0]["weight_category"] == "57kg"

    def test_an_unknown_category_is_an_error_row_in_the_preview(self, db):
        event = make_event()
        db.data["combine_events"].append(event)

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk?dry_run=true",
            json={
                "rows": [
                    {
                        "first_name": "Jack",
                        "surname": "Reid",
                        "gender": "male",
                        "weight_category": "cruiserweight",
                    }
                ]
            },
        )

        row = response.json()["results"][0]
        assert row["action"] == "error"
        assert row["reason"] == "Unknown weight category 'cruiserweight'"
        assert response.json()["participants_added"] == 0

    def test_an_unknown_category_writes_nothing_on_commit(self, db):
        event = make_event()
        db.data["combine_events"].append(event)

        response = client.post(
            f"/api/v1/combine/events/{event['id']}/participants/bulk",
            json={
                "rows": [
                    {
                        "first_name": "Jack",
                        "surname": "Reid",
                        "gender": "male",
                        "weight_category": "91",
                    },
                    {
                        "first_name": "Sam",
                        "surname": "Okoro",
                        "gender": "female",
                        "weight_category": "middleweight",
                    },
                ]
            },
        )

        actions = [r["action"] for r in response.json()["results"]]
        assert actions == ["created", "error"]
        assert db.data["combine_participants"][0]["weight_category"] == "91kg"
        assert len(db.data["athletes"]) == 1


class TestLandmineVelocityIsRequired:
    def test_a_peak_event_rejects_a_mean_only_throw(self, db):
        """No peak↔mean fallback exists downstream: it would save and rank nowhere."""
        event, _, participant = seed_event(db)

        response = submit(
            event,
            participant,
            {"station": "landmine", "load_kg": 20, "mean_velocity_ms": 1.9, "side": "left"},
        )

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "This event ranks landmine on peak velocity — enter it"
        )
        assert db.data["combine_attempts"] == []

    def test_a_mean_event_rejects_a_peak_only_throw(self, db):
        event, _, participant = seed_event(db, landmine_velocity_metric="mean")

        response = submit(
            event,
            participant,
            {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.5},
        )

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "This event ranks landmine on mean velocity — enter it"
        )

    def test_the_configured_metric_saves(self, db):
        event, _, participant = seed_event(db, landmine_velocity_metric="mean")

        response = submit(
            event,
            participant,
            {"station": "landmine", "load_kg": 20, "mean_velocity_ms": 1.9},
        )
        assert response.status_code == 201
        assert response.json()["value"] == 1.9

    def test_a_correction_cannot_drop_the_configured_metric(self, db):
        event, _, participant = seed_event(db)
        created = submit(
            event,
            participant,
            {"station": "landmine", "load_kg": 20, "peak_velocity_ms": 4.5},
        )

        response = client.patch(
            f"/api/v1/combine/attempts/{created.json()['id']}",
            json={
                "measures": {
                    "station": "landmine",
                    "load_kg": 20,
                    "mean_velocity_ms": 1.9,
                }
            },
        )
        assert response.status_code == 422


class TestAttemptDisplay:
    """The chip text on the station screen, which is how an operator checks a save."""

    def test_landmine_shows_velocity_load_and_side(self, db):
        event, _, participant = seed_event(db)
        response = submit(
            event,
            participant,
            {
                "station": "landmine",
                "load_kg": 20,
                "peak_velocity_ms": 3.45,
                "side": "right",
            },
        )
        assert response.json()["display_value"] == "3.45 m/s · 20 kg · R"

    def test_a_throw_off_the_reference_load_still_shows(self, db):
        """It cannot be ranked, but "—" on the chip reads as a lost save."""
        event, _, participant = seed_event(db)
        response = submit(
            event,
            participant,
            {"station": "landmine", "load_kg": 15, "peak_velocity_ms": 3.45},
        )
        assert response.json()["value"] is None
        assert response.json()["display_value"] == "3.45 m/s · 15 kg"

    def test_air_bike_shows_the_sprint_number(self, db):
        event, _, participant = seed_event(db)
        response = submit(
            event,
            participant,
            {
                "station": "air_bike",
                "sprint_number": 1,
                "power_7s": 856,
                "power_17s": 700,
                "power_27s": 600,
            },
        )
        assert response.json()["display_value"] == "15.02 W/kg · S1"

    def test_other_stations_are_unchanged(self, db):
        event, _, participant = seed_event(db)
        response = submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        assert response.json()["display_value"] == "41.2 cm"


class TestOverallScoreBasisSetting:
    """The Combine Score basis is an event setting the operator switches deliberately."""

    def _create(self, **overrides):
        payload = {"event_name": "BS Combine 2026", "event_date": EVENT_DATE}
        payload.update(overrides)
        return client.post("/api/v1/combine/events", json=payload)

    def test_a_new_event_defaults_to_the_z_basis(self, db):
        response = self._create()
        assert response.status_code == 201
        assert response.json()["overall_score_basis"] == "z"
        assert db.data["combine_events"][0]["overall_score_basis"] == "z"

    def test_an_event_can_be_created_on_the_percentile_basis(self, db):
        response = self._create(overall_score_basis="percentile")
        assert response.status_code == 201
        assert response.json()["overall_score_basis"] == "percentile"
        assert db.data["combine_events"][0]["overall_score_basis"] == "percentile"

    def test_the_basis_can_be_switched_after_the_fact(self, db):
        event, _, _ = seed_event(db)
        response = client.patch(
            f"/api/v1/combine/events/{event['id']}",
            json={"overall_score_basis": "percentile"},
        )
        assert response.status_code == 200
        assert response.json()["overall_score_basis"] == "percentile"
        assert db.data["combine_events"][0]["overall_score_basis"] == "percentile"

    def test_an_unknown_basis_is_refused(self, db):
        event, _, _ = seed_event(db)
        assert self._create(overall_score_basis="rank").status_code == 422
        assert (
            client.patch(
                f"/api/v1/combine/events/{event['id']}",
                json={"overall_score_basis": "rank"},
            ).status_code
            == 422
        )

    def test_the_board_declares_the_basis(self, db):
        event, _, participant = seed_event(db)
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        response = client.get(f"/api/v1/combine/events/{event['id']}/leaderboard")
        assert response.status_code == 200
        assert response.json()["score_basis"] == "z"

    def test_a_row_written_before_the_migration_reads_as_z(self, db):
        """The column is new; an event row without it must behave as it did."""
        event, _, participant = seed_event(db)
        db.data["combine_events"][0].pop("overall_score_basis")
        submit(event, participant, {"station": "cmj", "height_cm": 41.2})
        response = client.get(f"/api/v1/combine/events/{event['id']}/leaderboard")
        assert response.json()["score_basis"] == "z"

    def test_a_percentile_event_scores_by_percentile(self, db):
        event, _, jack = seed_event(
            db, overall_score_basis="percentile", min_stations_for_overall=1
        )
        sam_athlete = make_athlete("Sam Okoro")
        sam = make_participant(event, sam_athlete, bib=2)
        db.data["athletes"].append(sam_athlete)
        db.data["combine_participants"].append(sam)
        submit(event, jack, {"station": "cmj", "height_cm": 41.2})
        submit(event, sam, {"station": "cmj", "height_cm": 38.0})

        data = client.get(f"/api/v1/combine/events/{event['id']}/leaderboard").json()

        assert data["score_basis"] == "percentile"
        assert [e["combine_score"] for e in data["overall"]] == [100.0, 0.0]
        leader = data["overall"][0]
        # mean_z stays the coach's diagnostic and still means mean z, so it no longer
        # agrees with the displayed score.
        assert leader["mean_z"] > 0
        assert leader["combine_score"] != round(50 + 10 * leader["mean_z"], 1)
