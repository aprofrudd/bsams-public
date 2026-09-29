"""Tests for exercise library router."""

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
def sample_exercise_data():
    """Sample exercise library data for tests."""
    return {
        "id": str(uuid4()),
        "coach_id": str(uuid4()),
        "exercise_name": "Back Squat",
        "exercise_category": "Strength",
        "default_reps": 5,
        "default_weight_kg": 100.0,
        "default_tempo": "3-1-1-0",
        "default_rest_seconds": 120,
        "default_duration_seconds": None,
        "default_distance_meters": None,
        "notes": "Main compound lift",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


class TestCreateExerciseLibrary:
    """Test POST /api/v1/exercise-library/"""

    def test_create_exercise_success(self, mock_supabase, sample_exercise_data):
        """Should create and return new library exercise."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [sample_exercise_data]

        response = client.post(
            "/api/v1/exercise-library/",
            json={
                "exercise_name": "Back Squat",
                "exercise_category": "Strength",
                "default_reps": 5,
                "default_weight_kg": 100.0,
                "default_tempo": "3-1-1-0",
                "default_rest_seconds": 120,
                "notes": "Main compound lift",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["exercise_name"] == "Back Squat"
        assert data["default_reps"] == 5

    def test_create_exercise_duplicate_409(self, mock_supabase):
        """Should return 409 when exercise name already exists for this coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        response = client.post(
            "/api/v1/exercise-library/",
            json={"exercise_name": "Back Squat"},
        )

        assert response.status_code == 409

    def test_create_exercise_empty_name(self):
        """Should return 422 for empty exercise name."""
        response = client.post(
            "/api/v1/exercise-library/",
            json={"exercise_name": "  "},
        )
        assert response.status_code == 422

    def test_create_exercise_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/exercise-library/",
                json={"exercise_name": "Back Squat"},
            )
        assert response.status_code == 503


class TestListExerciseLibrary:
    """Test GET /api/v1/exercise-library/"""

    def test_list_exercises_success(self, mock_supabase, sample_exercise_data):
        """Should return list of exercises."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_exercise_data
        ]

        response = client.get("/api/v1/exercise-library/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["exercise_name"] == "Back Squat"

    def test_list_exercises_with_search(self, mock_supabase, sample_exercise_data):
        """Should filter exercises by search term."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.ilike.return_value.order.return_value.execute.return_value.data = [
            sample_exercise_data
        ]

        response = client.get("/api/v1/exercise-library/?search=squat")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_exercises_with_category(self, mock_supabase, sample_exercise_data):
        """Should filter exercises by category."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_exercise_data
        ]

        response = client.get("/api/v1/exercise-library/?category=Strength")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_exercises_empty(self, mock_supabase):
        """Should return empty list when no exercises."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/api/v1/exercise-library/")

        assert response.status_code == 200
        assert response.json() == []


class TestUpdateExerciseLibrary:
    """Test PATCH /api/v1/exercise-library/{id}"""

    def test_update_exercise_success(self, mock_supabase, sample_exercise_data):
        """Should update and return exercise."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: verify ownership
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
            else:
                # Second call: update
                updated = {**sample_exercise_data, "default_reps": 8}
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [updated]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/exercise-library/{sample_exercise_data['id']}",
            json={"default_reps": 8},
        )

        assert response.status_code == 200
        assert response.json()["default_reps"] == 8

    def test_update_exercise_not_found(self, mock_supabase):
        """Should return 404 when exercise not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.patch(
            f"/api/v1/exercise-library/{uuid4()}",
            json={"default_reps": 8},
        )

        assert response.status_code == 404

    def test_update_exercise_no_fields(self, mock_supabase, sample_exercise_data):
        """Should return 400 when no fields provided."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            sample_exercise_data
        ]

        response = client.patch(
            f"/api/v1/exercise-library/{sample_exercise_data['id']}",
            json={},
        )

        assert response.status_code == 400

    def test_update_exercise_duplicate_name_409(self, mock_supabase, sample_exercise_data):
        """Should return 409 when renaming to existing name."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
            else:
                mock_table.update.return_value.eq.return_value.execute.side_effect = Exception(
                    "duplicate key value violates unique constraint"
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/exercise-library/{sample_exercise_data['id']}",
            json={"exercise_name": "Front Squat"},
        )

        assert response.status_code == 409


class TestDeleteExerciseLibrary:
    """Test DELETE /api/v1/exercise-library/{id}"""

    def test_delete_exercise_success(self, mock_supabase, sample_exercise_data):
        """Should delete exercise and return 204."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
            else:
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(
            f"/api/v1/exercise-library/{sample_exercise_data['id']}"
        )

        assert response.status_code == 204

    def test_delete_exercise_not_found(self, mock_supabase):
        """Should return 404 when exercise not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/exercise-library/{uuid4()}")

        assert response.status_code == 404


class TestExerciseLibraryValidation:
    """Test schema validation for exercise library."""

    def test_exercise_name_stripped(self):
        """Exercise name should be stripped of whitespace."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        ex = ExerciseLibraryCreate(exercise_name="  Back Squat  ")
        assert ex.exercise_name == "Back Squat"

    def test_exercise_name_required(self):
        """Should require exercise name."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        with pytest.raises(Exception):
            ExerciseLibraryCreate(exercise_name="")

    def test_default_reps_range(self):
        """Default reps should accept valid ranges."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        ex = ExerciseLibraryCreate(exercise_name="Squat", default_reps=5)
        assert ex.default_reps == 5

        with pytest.raises(Exception):
            ExerciseLibraryCreate(exercise_name="Squat", default_reps=0)


class TestDefaultSetConfigs:
    """Test default_set_configs validation and API behavior."""

    def test_create_with_set_configs_success(self, mock_supabase, sample_exercise_data):
        """Should create exercise with default_set_configs."""
        response_data = {
            **sample_exercise_data,
            "default_set_configs": [{"reps": 5, "weight_kg": 100.0}, {"reps": 3, "weight_kg": 120.0}],
        }
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [response_data]

        response = client.post(
            "/api/v1/exercise-library/",
            json={
                "exercise_name": "Back Squat",
                "exercise_category": "Strength",
                "default_set_configs": [
                    {"reps": 5, "weight_kg": 100.0},
                    {"reps": 3, "weight_kg": 120.0},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["default_set_configs"] is not None
        assert len(data["default_set_configs"]) == 2
        assert data["default_set_configs"][0]["reps"] == 5
        assert data["default_set_configs"][1]["weight_kg"] == 120.0

    def test_create_with_empty_set_configs_rejected(self):
        """Should reject empty default_set_configs list."""
        response = client.post(
            "/api/v1/exercise-library/",
            json={
                "exercise_name": "Back Squat",
                "default_set_configs": [],
            },
        )
        assert response.status_code == 422

    def test_create_with_too_many_set_configs_rejected(self):
        """Should reject default_set_configs with more than 20 entries."""
        configs = [{"reps": i + 1} for i in range(21)]
        response = client.post(
            "/api/v1/exercise-library/",
            json={
                "exercise_name": "Back Squat",
                "default_set_configs": configs,
            },
        )
        assert response.status_code == 422

    def test_create_with_entry_missing_reps_and_weight_rejected(self):
        """Should reject set config entries with neither reps nor weight_kg."""
        response = client.post(
            "/api/v1/exercise-library/",
            json={
                "exercise_name": "Back Squat",
                "default_set_configs": [{}],
            },
        )
        assert response.status_code == 422

    def test_update_with_set_configs_success(self, mock_supabase, sample_exercise_data):
        """Should update exercise with default_set_configs."""
        call_count = [0]

        updated_data = {
            **sample_exercise_data,
            "default_set_configs": [{"reps": 8, "weight_kg": 80.0}],
        }

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_exercise_data
                ]
            else:
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/exercise-library/{sample_exercise_data['id']}",
            json={"default_set_configs": [{"reps": 8, "weight_kg": 80.0}]},
        )

        assert response.status_code == 200
        assert response.json()["default_set_configs"] == [{"reps": 8, "weight_kg": 80.0}]
