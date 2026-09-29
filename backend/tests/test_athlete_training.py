"""Tests for athlete training session logging, completion, wellness, and exercise updates."""

from datetime import datetime
from unittest.mock import MagicMock, patch, call
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app

# Use TEST_ATHLETE_ID from conftest
from tests.conftest import TEST_ATHLETE_ID, TEST_USER_ID

LINKED_ATHLETE_ID = uuid4()
OTHER_ATHLETE_ID = uuid4()
SESSION_ID = uuid4()
EXERCISE_ID = uuid4()
WELLNESS_ID = uuid4()


def _mock_athlete_access(mock_client, athlete_id, accessible=True):
    """Setup mock for verify_athlete_access — athlete role checks user_id."""
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_eq1 = MagicMock()
    mock_select.eq.return_value = mock_eq1
    mock_eq2 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2
    mock_eq2.execute.return_value.data = [{"id": str(athlete_id)}] if accessible else []
    return mock_table


# ─── Training Session Tests ────────────────────────────────────────────────────


class TestAthleteCreateSession:
    """Tests for athlete creating training sessions."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_creates_own_session(self, mock_get_client, athlete_client):
        """Athlete should be able to log their own training session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # verify_athlete_access returns True
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        session_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "session_date": "2024-06-01",
            "training_type": "Strength",
            "duration_minutes": 60,
            "rpe": 7,
            "srpe": 420,
            "notes": None,
            "metrics": {},
            "status": None,
            "created_by": str(TEST_ATHLETE_ID),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [session_data]

        response = athlete_client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(LINKED_ATHLETE_ID),
                "session_date": "2024-06-01",
                "training_type": "Strength",
                "duration_minutes": 60,
                "rpe": 7,
            },
        )
        assert response.status_code == 201
        assert response.json()["created_by"] == str(TEST_ATHLETE_ID)

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_create_for_other_athlete(self, mock_get_client, athlete_client):
        """Athlete should get 404 when trying to create session for another athlete."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = []  # Not linked

        response = athlete_client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(OTHER_ATHLETE_ID),
                "session_date": "2024-06-01",
                "training_type": "Strength",
                "duration_minutes": 60,
                "rpe": 7,
            },
        )
        assert response.status_code == 404

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_create_assigned_session(self, mock_get_client, athlete_client):
        """Athlete should get 403 when trying to create an assigned session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        response = athlete_client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(LINKED_ATHLETE_ID),
                "session_date": "2024-06-01",
                "training_type": "Strength",
                "status": "assigned",
            },
        )
        assert response.status_code == 403

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_creates_session_without_rpe(self, mock_get_client, athlete_client):
        """Athlete self-logging without RPE/duration should succeed (optional)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        session_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "session_date": "2024-06-01",
            "training_type": "Strength",
            "duration_minutes": None,
            "rpe": None,
            "srpe": None,
            "notes": None,
            "metrics": {},
            "status": None,
            "created_by": str(TEST_ATHLETE_ID),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [session_data]

        response = athlete_client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(LINKED_ATHLETE_ID),
                "session_date": "2024-06-01",
                "training_type": "Strength",
                # No rpe or duration — should succeed
            },
        )
        assert response.status_code == 201


class TestCoachAssignSession:
    """Tests for coach creating assigned sessions."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_coach_creates_assigned_session(self, mock_get_client):
        """Coach should create an assigned session without RPE/duration."""
        client = TestClient(app)
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        session_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "session_date": "2024-06-01",
            "training_type": "Strength",
            "duration_minutes": None,
            "rpe": None,
            "srpe": None,
            "notes": None,
            "metrics": {},
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [session_data]

        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(LINKED_ATHLETE_ID),
                "session_date": "2024-06-01",
                "training_type": "Strength",
                "status": "assigned",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "assigned"
        assert response.json()["rpe"] is None

    @patch("app.core.supabase_client.get_supabase_client")
    def test_coach_regular_session_without_rpe_succeeds(self, mock_get_client):
        """Coach logging a regular session without RPE/duration should succeed."""
        client = TestClient(app)
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        created_session = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "session_date": "2024-06-01",
            "training_type": "Strength",
            "duration_minutes": None,
            "rpe": None,
            "srpe": None,
            "notes": None,
            "metrics": {},
            "status": None,
            "created_by": str(TEST_USER_ID),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [created_session]

        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(LINKED_ATHLETE_ID),
                "session_date": "2024-06-01",
                "training_type": "Strength",
                # No rpe or duration, no status
            },
        )
        assert response.status_code == 201


class TestAthleteCompleteSession:
    """Tests for athlete completing assigned sessions."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_completes_assigned_session(self, mock_get_client, athlete_client):
        """Athlete PATCH with rpe on assigned session should auto-set status=completed."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # First call: fetch existing session
        existing_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "session_date": "2024-06-01",
            "training_type": "Strength",
            "duration_minutes": None,
            "rpe": None,
            "srpe": None,
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
        }

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # For get session: single .eq("id", ...)
        mock_eq1.execute.return_value.data = [existing_data]
        # For verify_athlete_access: double .eq("id",...).eq("user_id",...)
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        # Update return
        updated_data = {
            **existing_data,
            "rpe": 7,
            "duration_minutes": 60,
            "srpe": 420,
            "status": "completed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "notes": None,
            "metrics": {},
        }
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated_data]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{SESSION_ID}",
            json={"rpe": 7, "duration_minutes": 60},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


class TestAthleteUpdateSession:
    """Tests for athlete updating their own sessions."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_strips_session_date_on_assigned(self, mock_get_client, athlete_client):
        """Athlete cannot change session_date on an assigned/completed session — field is stripped."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        existing_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
        }

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq1.execute.return_value.data = [existing_data]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        updated_data = {
            **existing_data,
            "rpe": 7,
            "duration_minutes": 60,
            "srpe": 420,
            "status": "completed",
            "session_date": "2024-06-01",
            "training_type": "Strength",
            "notes": None,
            "metrics": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated_data]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{SESSION_ID}",
            json={"session_date": "2024-12-25", "rpe": 7, "duration_minutes": 60},
        )
        assert response.status_code == 200
        # Verify session_date was stripped from update call
        update_call_args = mock_table.update.call_args[0][0]
        assert "session_date" not in update_call_args


class TestAthleteDeleteSession:
    """Tests for athlete deleting sessions."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_deletes_own_session(self, mock_get_client, athlete_client):
        """Athlete should be able to delete their own self-logged session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        existing_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": None,
            "created_by": str(TEST_ATHLETE_ID),
        }

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq1.execute.return_value.data = [existing_data]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete_eq = MagicMock()
        mock_delete.eq.return_value = mock_delete_eq
        mock_delete_eq.execute.return_value.data = []

        response = athlete_client.delete(f"/api/v1/training/sessions/{SESSION_ID}")
        assert response.status_code == 204

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_delete_assigned_session(self, mock_get_client, athlete_client):
        """Athlete should get 403 when trying to delete coach-assigned session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        existing_data = {
            "id": str(SESSION_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
        }

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq1.execute.return_value.data = [existing_data]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        response = athlete_client.delete(f"/api/v1/training/sessions/{SESSION_ID}")
        assert response.status_code == 403


# ─── Exercise Prescription Tests ────────────────────────────────────────────────


class TestAthleteExerciseUpdate:
    """Tests for athlete updating exercise prescriptions."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_updates_reps_and_weight(self, mock_get_client, athlete_client):
        """Athlete should be able to update reps and weight_kg on exercises."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Session ownership check: training_sessions select
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Chain: .eq(session_id).execute => athlete_id, then .eq(athlete_id).eq(user_id).execute => exists
        mock_eq1.execute.return_value.data = [{"athlete_id": str(LINKED_ATHLETE_ID)}]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        # Exercise exists check
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": str(EXERCISE_ID)}]

        # Update
        updated = {
            "id": str(EXERCISE_ID),
            "session_id": str(SESSION_ID),
            "exercise_name": "Squat",
            "exercise_category": "Strength",
            "set_number": 1,
            "reps": 8,
            "weight_kg": 100.0,
            "tempo": None,
            "rest_seconds": None,
            "duration_seconds": None,
            "distance_meters": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/{EXERCISE_ID}",
            json={"reps": 8, "weight_kg": 100.0, "exercise_name": "Should be stripped"},
        )
        assert response.status_code == 200
        # Verify exercise_name was stripped
        update_call_args = mock_table.update.call_args[0][0]
        assert "exercise_name" not in update_call_args
        assert "reps" in update_call_args

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_create_exercise_on_assigned_session(self, mock_get_client, athlete_client):
        """Athlete should get 403 when trying to create exercise on assigned session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Session details: assigned session created by coach
        mock_eq1.execute.return_value.data = [{
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
        }]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        response = athlete_client.post(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/",
            json={"exercise_name": "Squat", "set_number": 1},
        )
        assert response.status_code == 403

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_delete_exercise_on_assigned_session(self, mock_get_client, athlete_client):
        """Athlete should get 403 when trying to delete exercise on assigned session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Session details: assigned session
        mock_eq1.execute.return_value.data = [{
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
        }]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        response = athlete_client.delete(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/{EXERCISE_ID}",
        )
        assert response.status_code == 403

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_creates_exercise_on_own_session(self, mock_get_client, athlete_client):
        """Athlete should be able to create exercise on their own session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Session details: own session (status=None, created_by=athlete)
        mock_eq1.execute.return_value.data = [{
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": None,
            "created_by": str(TEST_ATHLETE_ID),
        }]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        # Insert return
        exercise_data = {
            "id": str(EXERCISE_ID),
            "session_id": str(SESSION_ID),
            "exercise_name": "Squat",
            "exercise_category": "Strength",
            "set_number": 1,
            "reps": 5,
            "weight_kg": 80.0,
            "tempo": None,
            "rest_seconds": None,
            "duration_seconds": None,
            "distance_meters": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [exercise_data]

        response = athlete_client.post(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/",
            json={"exercise_name": "Squat", "exercise_category": "Strength", "set_number": 1, "reps": 5, "weight_kg": 80.0},
        )
        assert response.status_code == 201

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_deletes_exercise_on_own_session(self, mock_get_client, athlete_client):
        """Athlete should be able to delete exercise on their own session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Session details: own session
        mock_eq1.execute.return_value.data = [{
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": None,
            "created_by": str(TEST_ATHLETE_ID),
        }]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        # Exercise exists
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": str(EXERCISE_ID)}]

        # Delete
        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete_eq = MagicMock()
        mock_delete.eq.return_value = mock_delete_eq
        mock_delete_eq.execute.return_value.data = []

        response = athlete_client.delete(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/{EXERCISE_ID}",
        )
        assert response.status_code == 204

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_fully_edits_exercise_on_own_session(self, mock_get_client, athlete_client):
        """Athlete should be able to update all fields on their own session exercises."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Session details: own session
        mock_eq1.execute.return_value.data = [{
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": None,
            "created_by": str(TEST_ATHLETE_ID),
        }]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        # Exercise exists check
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": str(EXERCISE_ID), "reps": 5}]

        # Update
        updated = {
            "id": str(EXERCISE_ID),
            "session_id": str(SESSION_ID),
            "exercise_name": "Bench Press",
            "exercise_category": "Strength",
            "set_number": 1,
            "reps": 8,
            "weight_kg": 100.0,
            "tempo": None,
            "rest_seconds": 90,
            "duration_seconds": None,
            "distance_meters": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/{EXERCISE_ID}",
            json={"exercise_name": "Bench Press", "reps": 8, "weight_kg": 100.0, "rest_seconds": 90},
        )
        assert response.status_code == 200
        # Verify exercise_name was NOT stripped (own session = full edit)
        update_call_args = mock_table.update.call_args[0][0]
        assert "exercise_name" in update_call_args
        assert "rest_seconds" in update_call_args

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_limited_edit_on_assigned_session(self, mock_get_client, athlete_client):
        """Athlete should only update reps/weight on coach-assigned session exercises."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Session details: assigned session
        mock_eq1.execute.return_value.data = [{
            "athlete_id": str(LINKED_ATHLETE_ID),
            "status": "assigned",
            "created_by": str(TEST_USER_ID),
        }]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        # Exercise exists check
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": str(EXERCISE_ID), "reps": 5}]

        # Update
        updated = {
            "id": str(EXERCISE_ID),
            "session_id": str(SESSION_ID),
            "exercise_name": "Squat",
            "exercise_category": "Strength",
            "set_number": 1,
            "reps": 8,
            "weight_kg": 100.0,
            "tempo": None,
            "rest_seconds": None,
            "duration_seconds": None,
            "distance_meters": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{SESSION_ID}/exercises/{EXERCISE_ID}",
            json={"reps": 8, "weight_kg": 100.0, "exercise_name": "Should be stripped"},
        )
        assert response.status_code == 200
        # Verify exercise_name was stripped (assigned session)
        update_call_args = mock_table.update.call_args[0][0]
        assert "exercise_name" not in update_call_args
        assert "reps" in update_call_args


# ─── Wellness Tests ────────────────────────────────────────────────────────────


class TestAthleteWellness:
    """Tests for athlete managing wellness entries."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_creates_wellness(self, mock_get_client, athlete_client):
        """Athlete should be able to create a wellness entry."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        wellness_data = {
            "id": str(WELLNESS_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
            "entry_date": "2024-06-01",
            "sleep": 5,
            "fatigue": 3,
            "stress": 2,
            "doms": 4,
            "hooper_index": 14,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [wellness_data]

        response = athlete_client.post(
            "/api/v1/wellness/",
            json={
                "athlete_id": str(LINKED_ATHLETE_ID),
                "entry_date": "2024-06-01",
                "sleep": 5,
                "fatigue": 3,
                "stress": 2,
                "doms": 4,
            },
        )
        assert response.status_code == 201

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_updates_wellness(self, mock_get_client, athlete_client):
        """Athlete should be able to update their wellness entry."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        existing = {
            "id": str(WELLNESS_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
        }

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq1.execute.return_value.data = [existing]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        updated = {
            **existing,
            "entry_date": "2024-06-01",
            "sleep": 6,
            "fatigue": 3,
            "stress": 2,
            "doms": 4,
            "hooper_index": 15,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated]

        response = athlete_client.patch(
            f"/api/v1/wellness/{WELLNESS_ID}",
            json={"sleep": 6},
        )
        assert response.status_code == 200

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_deletes_wellness(self, mock_get_client, athlete_client):
        """Athlete should be able to delete their wellness entry."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        existing = {
            "id": str(WELLNESS_ID),
            "athlete_id": str(LINKED_ATHLETE_ID),
        }

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1
        mock_eq1.execute.return_value.data = [existing]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(LINKED_ATHLETE_ID)}]

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete_eq = MagicMock()
        mock_delete.eq.return_value = mock_delete_eq
        mock_delete_eq.execute.return_value.data = []

        response = athlete_client.delete(f"/api/v1/wellness/{WELLNESS_ID}")
        assert response.status_code == 204


# ─── Template Access Tests ────────────────────────────────────────────────────

TEMPLATE_ID = uuid4()
COACH_ID = uuid4()


class TestAthleteTemplateAccess:
    """Tests for athlete accessing coach templates."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_lists_coach_templates(self, mock_get_client, athlete_client):
        """Athlete should see their coach's templates."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        def table_side_effect(table_name):
            t = MagicMock()
            if table_name == "athletes":
                # _get_athlete_coach_id: athletes.user_id lookup
                t.select.return_value.eq.return_value.execute.return_value.data = [
                    {"coach_id": str(COACH_ID)}
                ]
            elif table_name == "session_templates":
                # list templates query
                t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    {
                        "id": str(TEMPLATE_ID),
                        "coach_id": str(COACH_ID),
                        "template_name": "Push Day",
                        "training_type": "Strength",
                        "notes": None,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                    }
                ]
            elif table_name == "template_exercises":
                t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return t

        mock_client.table.side_effect = table_side_effect

        response = athlete_client.get("/api/v1/session-templates/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_name"] == "Push Day"

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_applies_template_to_own_session(self, mock_get_client, athlete_client):
        """Athlete should apply a template to their own session."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        call_count = {"n": 0}

        def table_side_effect(table_name):
            t = MagicMock()
            if table_name == "training_sessions":
                # session details
                t.select.return_value.eq.return_value.execute.return_value.data = [{
                    "athlete_id": str(LINKED_ATHLETE_ID),
                    "status": None,
                    "created_by": str(TEST_ATHLETE_ID),
                }]
            elif table_name == "athletes":
                # First call: verify_athlete_access, second: _get_athlete_coach_id
                call_count["n"] += 1
                if call_count["n"] == 1:
                    t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": str(LINKED_ATHLETE_ID)}
                    ]
                else:
                    t.select.return_value.eq.return_value.execute.return_value.data = [
                        {"coach_id": str(COACH_ID)}
                    ]
            elif table_name == "session_templates":
                t.select.return_value.eq.return_value.execute.return_value.data = [{
                    "id": str(TEMPLATE_ID),
                    "coach_id": str(COACH_ID),
                    "template_name": "Push Day",
                    "training_type": "Strength",
                }]
            elif table_name == "template_exercises":
                t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    {
                        "exercise_name": "Bench Press",
                        "exercise_category": "Strength",
                        "sets": 3,
                        "reps": 8,
                        "weight_kg": 60.0,
                    }
                ]
            elif table_name == "exercise_prescriptions":
                t.insert.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "session_id": str(SESSION_ID), "exercise_name": "Bench Press", "set_number": i}
                    for i in range(1, 4)
                ]
            return t

        mock_client.table.side_effect = table_side_effect

        response = athlete_client.post(
            f"/api/v1/session-templates/{TEMPLATE_ID}/apply?session_id={SESSION_ID}",
        )
        assert response.status_code == 201
