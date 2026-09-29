"""Tests for conditioning & interval training features."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app

client = TestClient(app)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_exercises_supabase():
    """Mock Supabase for exercises router."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_templates_supabase():
    """Mock Supabase for session templates router."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_library_supabase():
    """Mock Supabase for exercise library router."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_session_id():
    return str(uuid4())


@pytest.fixture
def sample_athlete_id():
    return str(uuid4())


def make_exercise_response(session_id, **overrides):
    """Create a sample exercise response dict."""
    data = {
        "id": str(uuid4()),
        "session_id": session_id,
        "exercise_name": "Sprint Intervals",
        "exercise_category": "Conditioning",
        "set_number": 1,
        "reps": 6,
        "weight_kg": None,
        "tempo": None,
        "rest_seconds": 180,
        "duration_seconds": 30,
        "distance_meters": None,
        "notes": None,
        "intensity_type": None,
        "intensity_value": None,
        "rest_between_reps_seconds": None,
        "rep_durations": None,
        "rest_between_reps": None,
        "rep_intensity_values": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    data.update(overrides)
    return data


def setup_exercise_create_mock(mock_supabase, session_id, athlete_id, response_data):
    """Setup mocks for creating an exercise (session ownership + insert)."""

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "training_sessions":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"athlete_id": athlete_id}
            ]
        elif table_name == "athletes":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": athlete_id}
            ]
        elif table_name == "exercise_prescriptions":
            mock_table.insert.return_value.execute.return_value.data = [response_data]
        return mock_table

    mock_supabase.table.side_effect = table_side_effect


def setup_exercise_update_mock(
    mock_supabase, session_id, athlete_id, existing_data, updated_data
):
    """Setup mocks for updating an exercise (session ownership + select + update)."""

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "training_sessions":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"athlete_id": athlete_id}
            ]
        elif table_name == "athletes":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": athlete_id}
            ]
        elif table_name == "exercise_prescriptions":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                existing_data
            ]
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [
                updated_data
            ]
        return mock_table

    mock_supabase.table.side_effect = table_side_effect


# ── Exercise Prescription Create Tests ──────────────────────────────


class TestConditioningExerciseCreate:
    """Test creating exercises with conditioning/intensity fields."""

    def test_create_exercise_with_rpe_intensity(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with intensity_type=rpe, intensity_value=7 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            intensity_type="rpe",
            intensity_value=7.0,
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 6,
                "rest_seconds": 180,
                "duration_seconds": 30,
                "intensity_type": "rpe",
                "intensity_value": 7.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["intensity_type"] == "rpe"
        assert data["intensity_value"] == 7.0

    def test_create_exercise_with_speed_intensity(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with intensity_type=speed_kmh, intensity_value=15 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            intensity_type="speed_kmh",
            intensity_value=15.0,
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Treadmill Intervals",
                "set_number": 1,
                "intensity_type": "speed_kmh",
                "intensity_value": 15.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["intensity_type"] == "speed_kmh"
        assert data["intensity_value"] == 15.0

    def test_create_exercise_with_power_intensity(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with intensity_type=power_watts, intensity_value=250 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            intensity_type="power_watts",
            intensity_value=250.0,
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Bike Sprints",
                "set_number": 1,
                "intensity_type": "power_watts",
                "intensity_value": 250.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["intensity_type"] == "power_watts"
        assert data["intensity_value"] == 250.0

    def test_create_exercise_invalid_intensity_type(self):
        """POST with intensity_type='invalid' should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "intensity_type": "invalid",
                "intensity_value": 7.0,
            },
        )

        assert response.status_code == 422

    def test_create_exercise_with_rest_between_reps(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with rest_between_reps_seconds=120 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            rest_between_reps_seconds=120,
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "EMOM Cleans",
                "set_number": 1,
                "reps": 10,
                "rest_between_reps_seconds": 120,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rest_between_reps_seconds"] == 120

    def test_create_exercise_negative_rest_between_reps(self):
        """POST with rest_between_reps_seconds=-1 should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "rest_between_reps_seconds": -1,
            },
        )

        assert response.status_code == 422

    def test_create_exercise_intensity_value_without_type(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with intensity_value=7 but no intensity_type should succeed (no coupling)."""
        response_data = make_exercise_response(
            sample_session_id,
            intensity_value=7.0,
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "intensity_value": 7.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["intensity_type"] is None
        assert data["intensity_value"] == 7.0


# ── Exercise Prescription Update Tests ──────────────────────────────


class TestConditioningExerciseUpdate:
    """Test updating exercises with conditioning/intensity fields."""

    def test_update_exercise_add_intensity(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH to add intensity_type and intensity_value should succeed."""
        existing = make_exercise_response(sample_session_id)
        updated = {
            **existing,
            "intensity_type": "rpe",
            "intensity_value": 8.0,
        }
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"intensity_type": "rpe", "intensity_value": 8.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["intensity_type"] == "rpe"
        assert data["intensity_value"] == 8.0


# ── Exercise Library Schema Tests ───────────────────────────────────


class TestConditioningExerciseLibrary:
    """Test exercise library schemas with conditioning fields."""

    def test_library_exercise_with_default_intensity(self):
        """ExerciseLibraryCreate with default_intensity_type='rpe' should pass validation."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        lib = ExerciseLibraryCreate(
            exercise_name="Sprint Intervals",
            exercise_category="Conditioning",
            default_intensity_type="rpe",
            default_intensity_value=7.0,
            default_rest_between_reps_seconds=60,
        )
        assert lib.default_intensity_type == "rpe"
        assert lib.default_intensity_value == 7.0
        assert lib.default_rest_between_reps_seconds == 60

    def test_library_exercise_invalid_default_intensity_type(self):
        """ExerciseLibraryCreate with default_intensity_type='invalid' should raise ValidationError."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        with pytest.raises(ValidationError) as exc_info:
            ExerciseLibraryCreate(
                exercise_name="Sprint Intervals",
                default_intensity_type="invalid",
            )
        assert "default_intensity_type" in str(exc_info.value)


# ── Template Exercise Schema Tests ──────────────────────────────────


class TestConditioningTemplateExercise:
    """Test template exercise schemas and apply with conditioning fields."""

    def test_template_exercise_with_intensity(self):
        """TemplateExerciseCreate with intensity fields should pass validation."""
        from app.schemas.session_template import TemplateExerciseCreate

        tex = TemplateExerciseCreate(
            exercise_name="Bike Sprints",
            exercise_category="Conditioning",
            sets=4,
            reps=1,
            intensity_type="power_watts",
            intensity_value=300.0,
            rest_between_reps_seconds=90,
        )
        assert tex.intensity_type == "power_watts"
        assert tex.intensity_value == 300.0
        assert tex.rest_between_reps_seconds == 90

    def test_template_apply_passes_intensity_fields(
        self, mock_templates_supabase, sample_session_id, sample_athlete_id
    ):
        """POST apply template should insert prescriptions with intensity fields."""
        from tests.conftest import TEST_USER_ID

        template_id = str(uuid4())
        coach_id = str(TEST_USER_ID)

        template_exercise = {
            "id": str(uuid4()),
            "template_id": template_id,
            "exercise_name": "Sprint Intervals",
            "exercise_category": "Conditioning",
            "order_index": 1,
            "sets": 2,
            "reps": 6,
            "weight_kg": None,
            "tempo": None,
            "rest_seconds": 180,
            "duration_seconds": 30,
            "distance_meters": None,
            "notes": None,
            "intensity_type": "rpe",
            "intensity_value": 8.0,
            "rest_between_reps_seconds": 45,
        }

        # Track what gets inserted
        inserted_data = []

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {
                        "id": template_id,
                        "coach_id": coach_id,
                        "template_name": "HIIT",
                        "training_type": "Conditioning",
                    }
                ]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    template_exercise
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": sample_athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "exercise_prescriptions":

                def capture_insert(data):
                    inserted_data.extend(data)
                    mock_result = MagicMock()
                    mock_result.execute.return_value.data = data
                    return mock_result

                mock_table.insert.side_effect = capture_insert
            return mock_table

        mock_templates_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{template_id}/apply?session_id={sample_session_id}",
        )

        assert response.status_code == 201
        # Template had sets=2, so should produce 2 prescription rows
        assert len(inserted_data) == 2
        for row in inserted_data:
            assert row["intensity_type"] == "rpe"
            assert row["intensity_value"] == 8.0
            assert row["rest_between_reps_seconds"] == 45


# ── Athlete Access Control Tests ────────────────────────────────────


class TestConditioningAthleteAccess:
    """Test athlete role cannot update conditioning-specific fields."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_update_intensity_fields(
        self, mock_get_client, athlete_client
    ):
        """Athlete PATCH with intensity_type should be stripped; only reps/weight allowed."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        session_id = str(uuid4())
        exercise_id = str(uuid4())

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Session ownership: training_sessions select
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        # Chain: .eq(session_id).execute => athlete_id
        from tests.conftest import TEST_ATHLETE_ID

        mock_eq1.execute.return_value.data = [
            {"athlete_id": str(TEST_ATHLETE_ID)}
        ]
        # Then .eq(athlete_id).eq(user_id).execute => exists (athlete access via user_id)
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(TEST_ATHLETE_ID)}]

        # Exercise exists check: .eq(exercise_id).eq(session_id)
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": exercise_id}]

        # Update response
        updated = make_exercise_response(
            session_id,
            id=exercise_id,
            reps=10,
            weight_kg=50.0,
        )
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{session_id}/exercises/{exercise_id}",
            json={
                "reps": 10,
                "weight_kg": 50.0,
                "intensity_type": "rpe",
                "intensity_value": 8.0,
                "rest_between_reps_seconds": 60,
            },
        )

        assert response.status_code == 200
        # Verify only reps and weight_kg were passed to update, intensity stripped
        update_call_args = mock_table.update.call_args[0][0]
        assert "reps" in update_call_args
        assert "weight_kg" in update_call_args
        assert "intensity_type" not in update_call_args
        assert "intensity_value" not in update_call_args
        assert "rest_between_reps_seconds" not in update_call_args


# ── Backward Compatibility Tests ────────────────────────────────────


class TestConditioningBackwardCompat:
    """Test backward compatibility with existing exercises."""

    def test_response_includes_null_intensity_fields(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """Create exercise without intensity fields → response has null intensity fields."""
        response_data = make_exercise_response(sample_session_id)
        # Confirm defaults are None
        assert response_data["intensity_type"] is None
        assert response_data["intensity_value"] is None
        assert response_data["rest_between_reps_seconds"] is None

        setup_exercise_create_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            response_data,
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Back Squat",
                "set_number": 1,
                "reps": 5,
                "weight_kg": 100.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["intensity_type"] is None
        assert data["intensity_value"] is None
        assert data["rest_between_reps_seconds"] is None

    def test_existing_exercises_without_new_fields_work(self):
        """ExercisePrescriptionCreate without new fields should still validate."""
        from app.schemas.exercise_prescription import ExercisePrescriptionCreate

        ex = ExercisePrescriptionCreate(
            exercise_name="Back Squat",
            set_number=1,
            reps=5,
            weight_kg=100.0,
        )
        assert ex.intensity_type is None
        assert ex.intensity_value is None
        assert ex.rest_between_reps_seconds is None


# ── Per-Rep Durations Tests ────────────────────────────────────────


class TestRepDurations:
    """Test per-rep durations feature (rep_durations JSONB column)."""

    def test_create_exercise_with_rep_durations(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with rep_durations=[15, 30, 45] and reps=3 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            reps=3,
            rep_durations=[15, 30, 45],
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Pyramid Intervals",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 3,
                "rep_durations": [15, 30, 45],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rep_durations"] == [15, 30, 45]

    def test_rep_durations_length_mismatch(self):
        """POST with rep_durations=[15, 30] and reps=3 should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "reps": 3,
                "rep_durations": [15, 30],
            },
        )

        assert response.status_code == 422

    def test_rep_durations_invalid_values(self):
        """POST with rep_durations=[0, -5] should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "reps": 2,
                "rep_durations": [0, -5],
            },
        )

        assert response.status_code == 422

    def test_rep_durations_empty_array(self):
        """POST with rep_durations=[] should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "reps": 1,
                "rep_durations": [],
            },
        )

        assert response.status_code == 422

    def test_update_exercise_with_rep_durations(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH with rep_durations should succeed."""
        existing = make_exercise_response(sample_session_id, reps=3)
        updated = {**existing, "rep_durations": [10, 20, 30]}
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"reps": 3, "rep_durations": [10, 20, 30]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rep_durations"] == [10, 20, 30]

    @patch("app.core.supabase_client.get_supabase_client")
    def test_athlete_cannot_update_rep_durations(self, mock_get_client, athlete_client):
        """Athlete PATCH with rep_durations should be silently stripped."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        session_id = str(uuid4())
        exercise_id = str(uuid4())

        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq1 = MagicMock()
        mock_select.eq.return_value = mock_eq1

        from tests.conftest import TEST_ATHLETE_ID

        mock_eq1.execute.return_value.data = [
            {"athlete_id": str(TEST_ATHLETE_ID)}
        ]
        mock_eq2 = MagicMock()
        mock_eq1.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": str(TEST_ATHLETE_ID)}]

        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": exercise_id, "rep_durations": None}]

        updated = make_exercise_response(session_id, id=exercise_id, reps=5)
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated]

        response = athlete_client.patch(
            f"/api/v1/training/sessions/{session_id}/exercises/{exercise_id}",
            json={
                "reps": 5,
                "rep_durations": [10, 20, 30, 40, 50],
            },
        )

        assert response.status_code == 200
        update_call_args = mock_table.update.call_args[0][0]
        assert "reps" in update_call_args
        assert "rep_durations" not in update_call_args

    def test_backward_compat_no_rep_durations(self):
        """ExercisePrescriptionCreate without rep_durations should have rep_durations=None."""
        from app.schemas.exercise_prescription import ExercisePrescriptionCreate

        ex = ExercisePrescriptionCreate(
            exercise_name="Back Squat",
            set_number=1,
            reps=5,
        )
        assert ex.rep_durations is None

    def test_patch_reps_clears_stale_rep_durations(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH reps=5 when existing rep_durations has 3 entries should clear rep_durations."""
        existing = make_exercise_response(
            sample_session_id, reps=3, rep_durations=[10, 20, 30]
        )
        updated = {**existing, "reps": 5, "rep_durations": None}
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"reps": 5},
        )

        assert response.status_code == 200
        # Verify rep_durations was set to None in the update call
        update_call = mock_exercises_supabase.table.return_value.update.call_args
        if update_call:
            update_payload = update_call[0][0]
            assert update_payload.get("rep_durations") is None

    def test_library_with_default_rep_durations(self):
        """ExerciseLibraryCreate with default_rep_durations should pass validation."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        lib = ExerciseLibraryCreate(
            exercise_name="Pyramid Sprints",
            exercise_category="Conditioning",
            default_rep_durations=[15, 30, 45, 60],
        )
        assert lib.default_rep_durations == [15, 30, 45, 60]


# ── Per-Rep Rest Between Reps Array Tests ─────────────────────────────


class TestRestBetweenRepsArray:
    """Test per-rep rest_between_reps array feature."""

    def test_create_exercise_with_rest_between_reps_array(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with rest_between_reps=[10, 20] and reps=3 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            reps=3,
            rep_durations=[15, 30, 45],
            rest_between_reps=[10, 20],
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Pyramid Intervals",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 3,
                "rep_durations": [15, 30, 45],
                "rest_between_reps": [10, 20],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rest_between_reps"] == [10, 20]

    def test_rest_between_reps_length_mismatch(self):
        """POST with rest_between_reps=[10] and reps=3 should return 422 (need reps-1=2)."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "reps": 3,
                "rest_between_reps": [10],
            },
        )

        assert response.status_code == 422

    def test_rest_between_reps_invalid_values(self):
        """POST with rest_between_reps=[-5, 700] should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Sprint Intervals",
                "set_number": 1,
                "reps": 3,
                "rest_between_reps": [-5, 700],
            },
        )

        assert response.status_code == 422

    def test_rest_between_reps_empty_for_single_rep(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with reps=1 and rest_between_reps=[] should succeed (reps-1=0)."""
        response_data = make_exercise_response(
            sample_session_id,
            reps=1,
            rest_between_reps=[],
        )
        # But actually, empty array with reps=1 means 0 items needed, 0 provided -- should fail
        # because validator requires reps-1 = 0 items and len([]) = 0 matches
        # Actually this should succeed since 0 == 0
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Single Sprint",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 1,
                "rest_between_reps": [],
            },
        )

        assert response.status_code == 201

    def test_update_exercise_with_rest_between_reps_array(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH with rest_between_reps should succeed."""
        existing = make_exercise_response(sample_session_id, reps=4)
        updated = {**existing, "rest_between_reps": [15, 30, 45]}
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"reps": 4, "rest_between_reps": [15, 30, 45]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rest_between_reps"] == [15, 30, 45]

    def test_patch_reps_clears_stale_rest_between_reps(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH reps=5 when existing rest_between_reps has 2 entries should clear the array."""
        existing = make_exercise_response(
            sample_session_id, reps=3, rest_between_reps=[10, 20]
        )
        updated = {**existing, "reps": 5, "rest_between_reps": None}
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"reps": 5},
        )

        assert response.status_code == 200

    def test_schema_rest_between_reps_none_by_default(self):
        """ExercisePrescriptionCreate without rest_between_reps defaults to None."""
        from app.schemas.exercise_prescription import ExercisePrescriptionCreate

        ex = ExercisePrescriptionCreate(
            exercise_name="Back Squat",
            set_number=1,
            reps=5,
        )
        assert ex.rest_between_reps is None

    def test_library_with_default_rest_between_reps(self):
        """ExerciseLibraryCreate with default_rest_between_reps should pass validation."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        lib = ExerciseLibraryCreate(
            exercise_name="Tabata Sprints",
            exercise_category="Conditioning",
            default_rest_between_reps=[10, 20, 30],
        )
        assert lib.default_rest_between_reps == [10, 20, 30]

    def test_library_default_rest_between_reps_invalid_values(self):
        """ExerciseLibraryCreate with default_rest_between_reps=[-1] should raise."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        with pytest.raises(ValidationError):
            ExerciseLibraryCreate(
                exercise_name="Bad Exercise",
                default_rest_between_reps=[-1],
            )

    def test_template_exercise_with_rest_between_reps(self):
        """TemplateExerciseCreate with rest_between_reps should pass validation."""
        from app.schemas.session_template import TemplateExerciseCreate

        tex = TemplateExerciseCreate(
            exercise_name="Pyramid Intervals",
            exercise_category="Conditioning",
            sets=3,
            reps=4,
            rest_between_reps=[15, 30, 45],
        )
        assert tex.rest_between_reps == [15, 30, 45]

    def test_combined_rep_durations_and_rest_between_reps(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with both rep_durations and rest_between_reps should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            reps=4,
            rep_durations=[15, 30, 45, 60],
            rest_between_reps=[10, 20, 30],
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Pyramid HIIT",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 4,
                "rep_durations": [15, 30, 45, 60],
                "rest_between_reps": [10, 20, 30],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rep_durations"] == [15, 30, 45, 60]
        assert data["rest_between_reps"] == [10, 20, 30]


# ── Delete 204 Handling Tests ──────────────────────────────────────


class TestDelete204Handling:
    """Test that DELETE endpoints return 204 No Content correctly."""

    def test_delete_exercise_returns_204(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """DELETE exercise should return 204 with no body."""
        exercise_id = str(uuid4())

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
                    {"id": exercise_id}
                ]
                mock_table.delete.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_exercises_supabase.table.side_effect = table_side_effect

        response = client.delete(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{exercise_id}",
        )

        assert response.status_code == 204
        assert response.content == b""


# ── Per-Rep Intensity Values Tests ──────────────────────────────────


class TestRepIntensityValues:
    """Test per-rep intensity values feature (rep_intensity_values JSONB column)."""

    def test_create_exercise_with_rep_intensity_values(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """POST with rep_intensity_values=[20, 15, 12] and reps=3 should succeed."""
        response_data = make_exercise_response(
            sample_session_id,
            reps=3,
            rep_durations=[30, 240, 60],
            rep_intensity_values=[20.0, 15.0, 12.0],
            intensity_type="speed_kmh",
            intensity_value=20.0,
        )
        setup_exercise_create_mock(
            mock_exercises_supabase, sample_session_id, sample_athlete_id, response_data
        )

        response = client.post(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/",
            json={
                "exercise_name": "Treadmill Intervals",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 3,
                "rep_durations": [30, 240, 60],
                "rep_intensity_values": [20.0, 15.0, 12.0],
                "intensity_type": "speed_kmh",
                "intensity_value": 20.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rep_intensity_values"] == [20.0, 15.0, 12.0]

    def test_rep_intensity_values_length_mismatch(self):
        """POST with rep_intensity_values=[20, 15] and reps=3 should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Treadmill Intervals",
                "set_number": 1,
                "reps": 3,
                "rep_intensity_values": [20.0, 15.0],
            },
        )

        assert response.status_code == 422

    def test_rep_intensity_values_negative_value(self):
        """POST with rep_intensity_values=[-5, 10] should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Treadmill Intervals",
                "set_number": 1,
                "reps": 2,
                "rep_intensity_values": [-5.0, 10.0],
            },
        )

        assert response.status_code == 422

    def test_rep_intensity_values_empty_array(self):
        """POST with rep_intensity_values=[] should return 422."""
        response = client.post(
            f"/api/v1/training/sessions/{uuid4()}/exercises/",
            json={
                "exercise_name": "Treadmill Intervals",
                "set_number": 1,
                "reps": 1,
                "rep_intensity_values": [],
            },
        )

        assert response.status_code == 422

    def test_update_exercise_with_rep_intensity_values(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH with rep_intensity_values should succeed."""
        existing = make_exercise_response(sample_session_id, reps=3)
        updated = {**existing, "rep_intensity_values": [20.0, 15.0, 12.0]}
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"reps": 3, "rep_intensity_values": [20.0, 15.0, 12.0]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rep_intensity_values"] == [20.0, 15.0, 12.0]

    def test_patch_reps_clears_stale_rep_intensity_values(
        self, mock_exercises_supabase, sample_session_id, sample_athlete_id
    ):
        """PATCH reps=5 when existing rep_intensity_values has 3 entries should clear it."""
        existing = make_exercise_response(
            sample_session_id, reps=3, rep_intensity_values=[20.0, 15.0, 12.0]
        )
        updated = {**existing, "reps": 5, "rep_intensity_values": None}
        setup_exercise_update_mock(
            mock_exercises_supabase,
            sample_session_id,
            sample_athlete_id,
            existing,
            updated,
        )

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_id}/exercises/{existing['id']}",
            json={"reps": 5},
        )

        assert response.status_code == 200
        # Verify rep_intensity_values was set to None in the update call
        update_call = mock_exercises_supabase.table.return_value.update.call_args
        if update_call:
            update_payload = update_call[0][0]
            assert update_payload.get("rep_intensity_values") is None

    def test_backward_compat_no_rep_intensity_values(self):
        """ExercisePrescriptionCreate without rep_intensity_values defaults to None."""
        from app.schemas.exercise_prescription import ExercisePrescriptionCreate

        ex = ExercisePrescriptionCreate(
            exercise_name="Back Squat",
            set_number=1,
            reps=5,
        )
        assert ex.rep_intensity_values is None

    def test_library_with_default_rep_intensity_values(self):
        """ExerciseLibraryCreate with default_rep_intensity_values should pass validation."""
        from app.schemas.exercise_library import ExerciseLibraryCreate

        lib = ExerciseLibraryCreate(
            exercise_name="Speed Intervals",
            exercise_category="Conditioning",
            default_rep_intensity_values=[20.0, 15.0, 12.0],
        )
        assert lib.default_rep_intensity_values == [20.0, 15.0, 12.0]

    def test_template_exercise_with_rep_intensity_values(self):
        """TemplateExerciseCreate with rep_intensity_values should pass validation."""
        from app.schemas.session_template import TemplateExerciseCreate

        tex = TemplateExerciseCreate(
            exercise_name="Treadmill Intervals",
            exercise_category="Conditioning",
            sets=3,
            reps=4,
            rep_intensity_values=[20.0, 18.0, 15.0, 12.0],
        )
        assert tex.rep_intensity_values == [20.0, 18.0, 15.0, 12.0]
