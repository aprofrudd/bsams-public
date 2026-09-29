"""Tests for athletes router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_athlete_data():
    """Sample athlete data for tests."""
    return {
        "id": str(uuid4()),
        "coach_id": "00000000-0000-0000-0000-000000000001",
        "name": "Test Athlete",
        "gender": "male",
        "date_of_birth": "1995-05-15",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


class TestListAthletes:
    """Test GET /api/v1/athletes/"""

    def test_list_athletes_success(self, mock_supabase, sample_athlete_data):
        """Should return list of athletes."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value.data = [
            sample_athlete_data
        ]

        response = client.get("/api/v1/athletes/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Athlete"

    def test_list_athletes_empty(self, mock_supabase):
        """Should return empty list when no athletes exist."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value.data = (
            []
        )

        response = client.get("/api/v1/athletes/")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_athletes_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get("/api/v1/athletes/")

        assert response.status_code == 503
        assert "Database not configured" in response.json()["detail"]


class TestGetAthlete:
    """Test GET /api/v1/athletes/{athlete_id}"""

    def test_get_athlete_success(self, mock_supabase, sample_athlete_data):
        """Should return single athlete."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            sample_athlete_data
        ]

        response = client.get(f"/api/v1/athletes/{sample_athlete_data['id']}")

        assert response.status_code == 200
        assert response.json()["name"] == "Test Athlete"

    def test_get_athlete_not_found(self, mock_supabase):
        """Should return 404 when athlete not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.get(f"/api/v1/athletes/{uuid4()}")

        assert response.status_code == 404
        assert "Athlete not found" in response.json()["detail"]

    def test_get_athlete_invalid_uuid(self):
        """Should return 422 for invalid UUID."""
        response = client.get("/api/v1/athletes/not-a-uuid")

        assert response.status_code == 422


class TestCreateAthlete:
    """Test POST /api/v1/athletes/"""

    def test_create_athlete_success(self, mock_supabase, sample_athlete_data):
        """Should create and return new athlete."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            sample_athlete_data
        ]

        response = client.post(
            "/api/v1/athletes/",
            json={
                "name": "Test Athlete",
                "gender": "male",
                "date_of_birth": "1995-05-15",
            },
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Test Athlete"

    def test_create_athlete_minimal(self, mock_supabase, sample_athlete_data):
        """Should create athlete with minimal data."""
        sample_athlete_data["date_of_birth"] = None
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            sample_athlete_data
        ]

        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "female"},
        )

        assert response.status_code == 201

    def test_create_athlete_invalid_gender(self):
        """Should return 422 for invalid gender."""
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "invalid"},
        )

        assert response.status_code == 422

    def test_create_athlete_missing_name(self):
        """Should return 422 when name is missing."""
        response = client.post(
            "/api/v1/athletes/",
            json={"gender": "male"},
        )

        assert response.status_code == 422


class TestUpdateAthlete:
    """Test PATCH /api/v1/athletes/{athlete_id}"""

    def test_update_athlete_success(self, mock_supabase, sample_athlete_data):
        """Should update and return athlete."""
        # Mock existence check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_data["id"]}
        ]
        # Mock update
        sample_athlete_data["name"] = "Updated Name"
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            sample_athlete_data
        ]

        response = client.patch(
            f"/api/v1/athletes/{sample_athlete_data['id']}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_update_athlete_not_found(self, mock_supabase):
        """Should return 404 when athlete not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.patch(
            f"/api/v1/athletes/{uuid4()}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    def test_update_athlete_no_fields(self, mock_supabase, sample_athlete_data):
        """Should return 400 when no fields provided."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_data["id"]}
        ]

        response = client.patch(
            f"/api/v1/athletes/{sample_athlete_data['id']}",
            json={},
        )

        assert response.status_code == 400


class TestDeleteAthlete:
    """Test DELETE /api/v1/athletes/{athlete_id}"""

    def test_delete_athlete_success(self, mock_supabase, sample_athlete_data):
        """Should delete athlete and return 204."""
        # Mock existence check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_data["id"]}
        ]
        # Not on any combine roster
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = (
            []
        )
        # Mock delete
        mock_supabase.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = (
            None
        )

        response = client.delete(f"/api/v1/athletes/{sample_athlete_data['id']}")

        assert response.status_code == 204

    def test_delete_athlete_not_found(self, mock_supabase):
        """Should return 404 when athlete not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.delete(f"/api/v1/athletes/{uuid4()}")

        assert response.status_code == 404


    def test_delete_athlete_on_combine_roster_rejected(self, mock_supabase, sample_athlete_data):
        """Should 409 without deleting when the athlete is on a combine roster.

        Both combine FKs cascade from `athletes`, so this DELETE would silently take
        the boxer's participant row and every attempt logged against them at all six
        stations. Attempts are the log of record — nothing re-creates them.
        """
        event_id = str(uuid4())

        athletes_table = MagicMock()
        athletes_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_data["id"], "name": "Jack Smith"}
        ]
        roster_table = MagicMock()
        roster_table.select.return_value.in_.return_value.execute.return_value.data = [
            {
                "id": str(uuid4()),
                "athlete_id": sample_athlete_data["id"],
                "combine_event_id": event_id,
            }
        ]
        events_table = MagicMock()
        events_table.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": event_id, "event_name": "BS Combine 2026"}
        ]
        events_data_table = MagicMock()
        events_data_table.select.return_value.eq.return_value.execute.return_value.data = []
        tables = {
            "athletes": athletes_table,
            "combine_participants": roster_table,
            "combine_events": events_table,
            "performance_events": events_data_table,
        }
        mock_supabase.table.side_effect = lambda name: tables[name]

        response = client.delete(f"/api/v1/athletes/{sample_athlete_data['id']}")

        assert response.status_code == 409
        detail = response.json()["detail"]
        # Names the event and an order that actually works: `delete_participant`
        # itself refuses once attempts exist, so "remove them from the roster" is a
        # dead end on event day.
        assert "BS Combine 2026" in detail
        assert "withdrawn" in detail
        athletes_table.delete.assert_not_called()

    @patch("app.routers.athletes.log_deletion")
    def test_delete_athlete_records_the_combine_check_in_the_audit_trail(
        self, mock_log_deletion, mock_supabase, sample_athlete_data
    ):
        """The audit row says what combine data the athlete carried when deleted."""
        athletes_table = MagicMock()
        athletes_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_data["id"], "name": "Test Athlete"}
        ]
        roster_table = MagicMock()
        roster_table.select.return_value.in_.return_value.execute.return_value.data = []
        events_data_table = MagicMock()
        events_data_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(uuid4())}
        ]
        tables = {
            "athletes": athletes_table,
            "combine_participants": roster_table,
            "performance_events": events_data_table,
        }
        mock_supabase.table.side_effect = lambda name: tables[name]

        response = client.delete(f"/api/v1/athletes/{sample_athlete_data['id']}")

        assert response.status_code == 204
        summary = mock_log_deletion.call_args.kwargs["entity_summary"]
        assert summary["events_count"] == 1
        assert summary["combine_participants_count"] == 0



class TestMergeAthletes:
    """Test POST /api/v1/athletes/merge"""

    def test_merge_athletes_success(self, mock_supabase):
        """Should reassign events and delete the duplicate athlete."""
        keep_id = str(uuid4())
        merge_id = str(uuid4())

        call_count = {"n": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                # Both athlete existence checks return data
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": keep_id}
                ]
                mock_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = (
                    None
                )
            elif table_name == "combine_participants":
                # Not on any combine roster
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    []
                )
            elif table_name == "performance_events":
                if call_count["n"] == 0:
                    # First call: count events for merge_id
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        {"id": str(uuid4())},
                        {"id": str(uuid4())},
                        {"id": str(uuid4())},
                    ]
                    call_count["n"] += 1
                else:
                    # Second call: update events
                    mock_table.update.return_value.eq.return_value.execute.return_value = (
                        None
                    )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/athletes/merge",
            json={"keep_id": keep_id, "merge_id": merge_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["kept_athlete_id"] == keep_id
        assert data["merged_events"] == 3
        assert data["deleted_athlete_id"] == merge_id

    def test_merge_same_athlete_rejected(self, mock_supabase):
        """Should return 400 when keep_id equals merge_id."""
        same_id = str(uuid4())

        response = client.post(
            "/api/v1/athletes/merge",
            json={"keep_id": same_id, "merge_id": same_id},
        )

        assert response.status_code == 400
        assert "must be different" in response.json()["detail"]

    def test_merge_nonexistent_athlete(self, mock_supabase):
        """Should return 404 when an athlete is not found."""
        keep_id = str(uuid4())
        merge_id = str(uuid4())

        # First athlete lookup returns empty (not found)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.post(
            "/api/v1/athletes/merge",
            json={"keep_id": keep_id, "merge_id": merge_id},
        )

        assert response.status_code == 404
        assert "Athlete not found" in response.json()["detail"]

    def test_merge_athlete_on_combine_roster_rejected(self, mock_supabase):
        """Should 409 without writing when merge_id is on a combine roster.

        Deleting the merged-away athlete cascades their combine participant row and
        every attempt logged against it, so the results of a testing day would go
        with them. Events are not reassigned either — the merge is refused first.
        """
        keep_id = str(uuid4())
        merge_id = str(uuid4())

        athletes_table = MagicMock()
        athletes_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": keep_id}
        ]
        events_table = MagicMock()
        events_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(uuid4())}
        ]
        roster_table = MagicMock()
        roster_table.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "athlete_id": merge_id, "combine_event_id": str(uuid4())}
        ]
        tables = {
            "athletes": athletes_table,
            "performance_events": events_table,
            "combine_participants": roster_table,
        }
        mock_supabase.table.side_effect = lambda name: tables[name]

        response = client.post(
            "/api/v1/athletes/merge",
            json={"keep_id": keep_id, "merge_id": merge_id},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "One of these athletes is on a combine roster — remove them from the roster first"
        )
        events_table.update.assert_not_called()
        athletes_table.delete.assert_not_called()


class TestDeleteAllData:
    """Test DELETE /api/v1/athletes/"""

    @patch("app.routers.athletes.log_event")
    @patch("app.routers.athletes.create_client")
    def test_delete_all_data_success(self, mock_create, mock_audit, mock_supabase):
        """Should delete all athletes and events for the coach (requires password)."""
        athlete_id_1 = str(uuid4())
        athlete_id_2 = str(uuid4())

        call_count = {"n": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "profiles":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"email": "coach@example.com"}
                ]
            elif table_name == "athletes":
                if call_count["n"] == 0:
                    # First call: select athlete IDs
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id_1},
                        {"id": athlete_id_2},
                    ]
                    call_count["n"] += 1
                else:
                    # Later call: delete athletes
                    mock_table.delete.return_value.eq.return_value.execute.return_value = None
            elif table_name == "combine_participants":
                # Nobody is on a combine roster
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    []
                )
            elif table_name == "performance_events":
                # Events for each athlete
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4())},
                    {"id": str(uuid4())},
                ]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect
        mock_create.return_value = MagicMock()

        response = client.request(
            "DELETE", "/api/v1/athletes/",
            json={"current_password": "CorrectPass1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_athletes"] == 2
        assert data["deleted_events"] == 4  # 2 events per athlete

    @patch("app.routers.athletes.create_client")
    def test_delete_all_data_empty(self, mock_create, mock_supabase):
        """Should return zeros when no data exists."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "profiles":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"email": "coach@example.com"}
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect
        mock_create.return_value = MagicMock()

        response = client.request(
            "DELETE", "/api/v1/athletes/",
            json={"current_password": "CorrectPass1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_athletes"] == 0
        assert data["deleted_events"] == 0

    def test_delete_all_data_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.request(
                "DELETE", "/api/v1/athletes/",
                json={"current_password": "SomePass1"},
            )

        assert response.status_code == 503


    @patch("app.routers.athletes.create_client")
    def test_delete_all_data_blocked_by_a_combine_roster(self, mock_create, mock_supabase):
        """Should 409 without deleting anything when an athlete is on a roster."""
        athlete_id = str(uuid4())
        event_id = str(uuid4())

        profiles_table = MagicMock()
        profiles_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        athletes_table = MagicMock()
        athletes_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": athlete_id}
        ]
        roster_table = MagicMock()
        roster_table.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "athlete_id": athlete_id, "combine_event_id": event_id}
        ]
        combine_events_table = MagicMock()
        combine_events_table.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": event_id, "event_name": "BS Combine 2026"}
        ]
        perf_table = MagicMock()
        perf_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(uuid4())}
        ]
        tables = {
            "profiles": profiles_table,
            "athletes": athletes_table,
            "combine_participants": roster_table,
            "combine_events": combine_events_table,
            "performance_events": perf_table,
        }
        mock_supabase.table.side_effect = lambda name: tables[name]
        mock_create.return_value = MagicMock()

        response = client.request(
            "DELETE", "/api/v1/athletes/",
            json={"current_password": "CorrectPass1"},
        )

        assert response.status_code == 409
        detail = response.json()["detail"]
        # The coach is not boxed in: the message names the event and the order that
        # unblocks the wipe.
        assert "BS Combine 2026" in detail
        assert "delete" in detail.lower()
        athletes_table.delete.assert_not_called()
        perf_table.delete.assert_not_called()

    @patch("app.routers.athletes.log_event")
    @patch("app.routers.athletes.create_client")
    def test_delete_all_data_checks_the_roster_in_chunks(
        self, mock_create, mock_audit, mock_supabase
    ):
        """A coach with hundreds of athletes must not build one enormous `in_` URL."""
        athlete_ids = [str(uuid4()) for _ in range(1200)]

        profiles_table = MagicMock()
        profiles_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        athletes_table = MagicMock()
        athletes_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": aid} for aid in athlete_ids
        ]
        roster_table = MagicMock()
        roster_table.select.return_value.in_.return_value.execute.return_value.data = []
        perf_table = MagicMock()
        perf_table.select.return_value.eq.return_value.execute.return_value.data = []
        tables = {
            "profiles": profiles_table,
            "athletes": athletes_table,
            "combine_participants": roster_table,
            "performance_events": perf_table,
        }
        mock_supabase.table.side_effect = lambda name: tables[name]
        mock_create.return_value = MagicMock()

        response = client.request(
            "DELETE", "/api/v1/athletes/",
            json={"current_password": "CorrectPass1"},
        )

        assert response.status_code == 200
        calls = roster_table.select.return_value.in_.call_args_list
        chunks = [list(call.args[1]) for call in calls]
        assert [len(chunk) for chunk in chunks] == [500, 500, 200]
        assert [aid for chunk in chunks for aid in chunk] == athlete_ids



class TestAthleteProfileFields:
    """Test new athlete profile fields (first_name, surname, body_mass_kg, etc.)."""

    def test_create_athlete_with_profile_fields(self, mock_supabase):
        """Should create athlete with all new profile fields."""
        athlete_data = {
            "id": str(uuid4()),
            "coach_id": "00000000-0000-0000-0000-000000000001",
            "name": "John Smith",
            "gender": "male",
            "date_of_birth": None,
            "first_name": "John",
            "surname": "Smith",
            "body_mass_kg": 85.5,
            "stature_cm": 180.0,
            "status": "professional",
            "notes": "Right-handed boxer",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [athlete_data]

        response = client.post(
            "/api/v1/athletes/",
            json={
                "name": "John Smith",
                "gender": "male",
                "first_name": "John",
                "surname": "Smith",
                "body_mass_kg": 85.5,
                "stature_cm": 180.0,
                "status": "professional",
                "notes": "Right-handed boxer",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["surname"] == "Smith"
        assert data["body_mass_kg"] == 85.5
        assert data["stature_cm"] == 180.0
        assert data["status"] == "professional"
        assert data["notes"] == "Right-handed boxer"

    def test_update_athlete_profile_fields(self, mock_supabase):
        """Should update athlete with new profile fields."""
        athlete_id = str(uuid4())
        # Mock existence check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": athlete_id}
        ]
        # Mock update response
        updated_data = {
            "id": athlete_id,
            "coach_id": "00000000-0000-0000-0000-000000000001",
            "name": "Test Athlete",
            "gender": "male",
            "date_of_birth": None,
            "first_name": None,
            "surname": None,
            "body_mass_kg": 75.0,
            "stature_cm": 175.5,
            "status": "amateur",
            "notes": "Updated notes",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        response = client.patch(
            f"/api/v1/athletes/{athlete_id}",
            json={
                "body_mass_kg": 75.0,
                "stature_cm": 175.5,
                "status": "amateur",
                "notes": "Updated notes",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["body_mass_kg"] == 75.0
        assert data["stature_cm"] == 175.5
        assert data["status"] == "amateur"
        assert data["notes"] == "Updated notes"

    def test_update_athlete_gender_with_null_fields(self, mock_supabase):
        """Should update gender when payload includes null optional fields."""
        athlete_id = str(uuid4())
        # Mock existence check
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": athlete_id}
        ]
        # Mock update response
        updated_data = {
            "id": athlete_id,
            "coach_id": "00000000-0000-0000-0000-000000000001",
            "name": "Test Athlete",
            "gender": "female",
            "date_of_birth": "2013-03-10",
            "first_name": "Test",
            "surname": None,
            "body_mass_kg": None,
            "stature_cm": None,
            "status": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        # Send only changed fields (what fixed frontend sends)
        response = client.patch(
            f"/api/v1/athletes/{athlete_id}",
            json={"first_name": "Test", "gender": "female"},
        )

        assert response.status_code == 200
        assert response.json()["gender"] == "female"

        # Verify None values are filtered from update sent to Supabase
        update_call = mock_supabase.table.return_value.update
        sent_data = update_call.call_args[0][0]
        assert "gender" in sent_data
        assert sent_data["gender"] == "female"
        # No None values should be in the update payload
        for v in sent_data.values():
            assert v is not None

    def test_create_athlete_invalid_status(self):
        """Should return 422 for invalid status value."""
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "male", "status": "semi-pro"},
        )
        assert response.status_code == 422

    def test_create_athlete_body_mass_too_high(self):
        """Should return 422 when body_mass_kg exceeds 500."""
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "male", "body_mass_kg": 501},
        )
        assert response.status_code == 422

    def test_create_athlete_body_mass_zero(self):
        """Should return 422 when body_mass_kg is 0."""
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "male", "body_mass_kg": 0},
        )
        assert response.status_code == 422

    def test_create_athlete_stature_too_high(self):
        """Should return 422 when stature_cm exceeds 300."""
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "male", "stature_cm": 301},
        )
        assert response.status_code == 422

    def test_create_athlete_first_name_too_long(self):
        """Should return 422 when first_name exceeds 50 characters."""
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Test", "gender": "male", "first_name": "A" * 51},
        )
        assert response.status_code == 422

    def test_list_athletes_includes_profile_fields(self, mock_supabase):
        """Should include new fields in list response."""
        athlete_data = {
            "id": str(uuid4()),
            "coach_id": "00000000-0000-0000-0000-000000000001",
            "name": "Jane Doe",
            "gender": "female",
            "date_of_birth": None,
            "first_name": "Jane",
            "surname": "Doe",
            "body_mass_kg": 65.0,
            "stature_cm": 170.0,
            "status": "amateur",
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value.data = [
            athlete_data
        ]

        response = client.get("/api/v1/athletes/")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["first_name"] == "Jane"
        assert data[0]["body_mass_kg"] == 65.0
        assert data[0]["status"] == "amateur"
