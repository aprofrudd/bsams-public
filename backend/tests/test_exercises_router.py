"""Tests for exercise prescriptions router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

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
def sample_session_id():
    """Sample session ID."""
    return str(uuid4())


@pytest.fixture
def sample_athlete_id():
    """Sample athlete ID."""
    return str(uuid4())


@pytest.fixture
def sample_exercise_data(sample_session_id):
    """Sample exercise data for tests."""
    return {
        "id": str(uuid4()),
        "session_id": sample_session_id,
        "exercise_name": "Back Squat",
        "exercise_category": "Strength",
        "set_number": 1,
        "reps": 5,
        "weight_kg": 100.0,
        "tempo": "3-1-1-0",
        "rest_seconds": 120,
        "duration_seconds": None,
        "distance_meters": None,
        "notes": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def setup_session_ownership_mock(mock_supabase, session_id, athlete_id, exists=True):
    """Helper to setup session ownership verification mock."""
    call_count = [0]

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "training_sessions":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                [{"athlete_id": athlete_id}] if exists else []
            )
        elif table_name == "athletes":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                [{"id": athlete_id}] if exists else []
            )
        return mock_table

    mock_supabase.table.side_effect = table_side_effect
    return mock_supabase


class TestCreateExercise:
    """Test POST /api/v1/training/sessions/{id}/exercises/"""

    def test_create_exercise_success(self, mock_supabase, sample_session_id, sample_athlete_id, sample_exercise_data):
        """Should create and return new exercise."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.insert.return_value.execute.return_value.data = [sample_exercise_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Back Squat",
                "exercise_category": "Strength",
                "set_number": 1,
                "reps": 5,
                "weight_kg": 100.0,
                "tempo": "3-1-1-0",
                "rest_seconds": 120,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["exercise_name"] == "Back Squat"
        assert data["reps"] == 5

    def test_create_exercise_session_not_found(self, mock_supabase, sample_session_id):
        """Should return 404 when session not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Back Squat",
                "set_number": 1,
            },
        )

        assert response.status_code == 404

    def test_create_exercise_empty_name(self):
        """Should return 422 for empty exercise name."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "  ",
                "set_number": 1,
            },
        )
        assert response.status_code == 422

    def test_create_exercise_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                f"/api/v1/training/sessions/{uuid4()}/exercises/",
                json={
                    "exercise_name": "Back Squat",
                    "set_number": 1,
                },
            )
        assert response.status_code == 503


class TestListExercises:
    """Test GET /api/v1/training/sessions/{id}/exercises/"""

    def test_list_exercises_success(self, mock_supabase, sample_session_id, sample_athlete_id, sample_exercise_data):
        """Should return list of exercises."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/training/sessions/{sample_session_id}/exercises/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["exercise_name"] == "Back Squat"

    def test_list_exercises_session_not_found(self, mock_supabase, sample_session_id):
        """Should return 404 when session not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/training/sessions/{sample_session_id}/exercises/")

        assert response.status_code == 404


class TestUpdateExercise:
    """Test PATCH /api/v1/training/sessions/{id}/exercises/{id}"""

    def test_update_exercise_success(self, mock_supabase, sample_session_id, sample_athlete_id, sample_exercise_data):
        """Should update and return exercise."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                # First call: select to verify exists
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
                # Second call: update
                updated = {**sample_exercise_data, "reps": 8}
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [updated]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{sample_exercise_data['id']}",
            json={"reps": 8},
        )

        assert response.status_code == 200

    def test_update_exercise_not_found(self, mock_supabase, sample_session_id, sample_athlete_id):
        """Should return 404 when exercise not found."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{uuid4()}",
            json={"reps": 8},
        )

        assert response.status_code == 404

    def test_update_exercise_no_fields(self, mock_supabase, sample_session_id, sample_athlete_id, sample_exercise_data):
        """Should return 400 when no fields provided."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{sample_exercise_data['id']}",
            json={},
        )

        assert response.status_code == 400


class TestDeleteExercise:
    """Test DELETE /api/v1/training/sessions/{id}/exercises/{id}"""

    def test_delete_exercise_success(self, mock_supabase, sample_session_id, sample_athlete_id, sample_exercise_data):
        """Should delete exercise and return 204."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{sample_exercise_data['id']}"
        )

        assert response.status_code == 204

    def test_delete_exercise_not_found(self, mock_supabase, sample_session_id, sample_athlete_id):
        """Should return 404 when exercise not found."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{uuid4()}"
        )

        assert response.status_code == 404


class TestExerciseValidation:
    """Test schema validation for exercises."""

    def test_exercise_name_stripped(self):
        """Exercise name should be stripped of whitespace."""
        from app.schemas.exercise_prescription import ExercisePrescriptionCreate

        ex = ExercisePrescriptionCreate(
            exercise_name="  Back Squat  ",
            set_number=1,
        )
        assert ex.exercise_name == "Back Squat"

    def test_set_number_boundaries(self):
        """Set number should accept valid ranges."""
        from app.schemas.exercise_prescription import ExercisePrescriptionCreate

        ex = ExercisePrescriptionCreate(
            exercise_name="Squat",
            set_number=1,
        )
        assert ex.set_number == 1

        ex2 = ExercisePrescriptionCreate(
            exercise_name="Squat",
            set_number=20,
        )
        assert ex2.set_number == 20
