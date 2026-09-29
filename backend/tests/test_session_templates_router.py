"""Tests for session templates router."""

from datetime import datetime
from unittest.mock import MagicMock, patch, call
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
def sample_template_data():
    """Sample session template data."""
    from tests.conftest import TEST_USER_ID
    return {
        "id": str(uuid4()),
        "coach_id": str(TEST_USER_ID),
        "template_name": "Leg Day",
        "training_type": "Strength",
        "notes": "Lower body focus",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_template_exercise():
    """Sample template exercise data."""
    return {
        "id": str(uuid4()),
        "template_id": str(uuid4()),
        "exercise_library_id": None,
        "exercise_name": "Back Squat",
        "exercise_category": "Strength",
        "order_index": 1,
        "sets": 3,
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


class TestCreateTemplate:
    """Test POST /api/v1/session-templates/"""

    def test_create_template_success(self, mock_supabase, sample_template_data):
        """Should create and return new template."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "session_templates":
                mock_table.insert.return_value.execute.return_value.data = [sample_template_data]
            elif table_name == "template_exercises":
                # Load exercises (empty for new template without exercises)
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/session-templates/",
            json={
                "template_name": "Leg Day",
                "training_type": "Strength",
                "notes": "Lower body focus",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["template_name"] == "Leg Day"
        assert data["training_type"] == "Strength"

    def test_create_template_with_exercises(self, mock_supabase, sample_template_data, sample_template_exercise):
        """Should create template with nested exercises."""
        sample_template_exercise["template_id"] = sample_template_data["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.insert.return_value.execute.return_value.data = [sample_template_data]
            elif table_name == "template_exercises":
                # delete (replace-all): no-op return
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
                # insert exercises
                mock_table.insert.return_value.execute.return_value.data = [sample_template_exercise]
                # load exercises
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_template_exercise
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/session-templates/",
            json={
                "template_name": "Leg Day",
                "training_type": "Strength",
                "exercises": [
                    {
                        "exercise_name": "Back Squat",
                        "exercise_category": "Strength",
                        "order_index": 1,
                        "sets": 3,
                        "reps": 5,
                        "weight_kg": 100.0,
                        "tempo": "3-1-1-0",
                        "rest_seconds": 120,
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["template_name"] == "Leg Day"

    def test_create_template_duplicate_409(self, mock_supabase):
        """Should return 409 for duplicate template name."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        response = client.post(
            "/api/v1/session-templates/",
            json={
                "template_name": "Leg Day",
                "training_type": "Strength",
            },
        )

        assert response.status_code == 409

    def test_create_template_empty_name(self):
        """Should return 422 for empty template name."""
        response = client.post(
            "/api/v1/session-templates/",
            json={
                "template_name": "  ",
                "training_type": "Strength",
            },
        )
        assert response.status_code == 422

    def test_create_template_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/session-templates/",
                json={
                    "template_name": "Leg Day",
                    "training_type": "Strength",
                },
            )
        assert response.status_code == 503


class TestListTemplates:
    """Test GET /api/v1/session-templates/"""

    def test_list_templates_success(self, mock_supabase, sample_template_data):
        """Should return list of templates with exercises."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_template_data
                ]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/session-templates/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_name"] == "Leg Day"

    def test_list_templates_empty(self, mock_supabase):
        """Should return empty list when no templates."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/api/v1/session-templates/")

        assert response.status_code == 200
        assert response.json() == []


class TestGetTemplate:
    """Test GET /api/v1/session-templates/{id}"""

    def test_get_template_success(self, mock_supabase, sample_template_data, sample_template_exercise):
        """Should return template with exercises."""
        sample_template_exercise["template_id"] = sample_template_data["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_template_data
                ]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_template_exercise
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/session-templates/{sample_template_data['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["template_name"] == "Leg Day"

    def test_get_template_not_found(self, mock_supabase):
        """Should return 404 when template not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/session-templates/{uuid4()}")

        assert response.status_code == 404


class TestDeleteTemplate:
    """Test DELETE /api/v1/session-templates/{id}"""

    def test_delete_template_success(self, mock_supabase, sample_template_data):
        """Should delete template and return 204."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # Verify ownership
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_template_data
                ]
            else:
                # Delete
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/session-templates/{sample_template_data['id']}")

        assert response.status_code == 204

    def test_delete_template_not_found(self, mock_supabase):
        """Should return 404 when template not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/session-templates/{uuid4()}")

        assert response.status_code == 404


class TestApplyTemplate:
    """Test POST /api/v1/session-templates/{id}/apply"""

    def test_apply_template_success(self, mock_supabase, sample_template_data, sample_template_exercise):
        """Should create exercise prescriptions from template with set expansion."""
        session_id = str(uuid4())
        athlete_id = str(uuid4())
        sample_template_exercise["template_id"] = sample_template_data["id"]
        sample_template_exercise["sets"] = 3

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    sample_template_data
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"athlete_id": athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_template_exercise
                ]
            elif table_name == "exercise_prescriptions":
                # Return 3 prescriptions (one per set)
                mock_table.insert.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "session_id": session_id, "exercise_name": "Back Squat", "set_number": i}
                    for i in range(1, 4)
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{sample_template_data['id']}/apply?session_id={session_id}"
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3

    def test_apply_template_not_found(self, mock_supabase):
        """Should return 404 when template not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.post(
            f"/api/v1/session-templates/{uuid4()}/apply?session_id={uuid4()}"
        )

        assert response.status_code == 404

    def test_apply_template_session_not_found(self, mock_supabase, sample_template_data):
        """Should return 404 when session not found."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    sample_template_data
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{sample_template_data['id']}/apply?session_id={uuid4()}"
        )

        assert response.status_code == 404


class TestSessionTemplateValidation:
    """Test schema validation for session templates."""

    def test_template_name_stripped(self):
        """Template name should be stripped of whitespace."""
        from app.schemas.session_template import SessionTemplateCreate

        t = SessionTemplateCreate(
            template_name="  Leg Day  ",
            training_type="Strength",
        )
        assert t.template_name == "Leg Day"

    def test_exercise_name_stripped(self):
        """Template exercise name should be stripped."""
        from app.schemas.session_template import TemplateExerciseCreate

        ex = TemplateExerciseCreate(exercise_name="  Back Squat  ")
        assert ex.exercise_name == "Back Squat"

    def test_sets_default_to_one(self):
        """Sets should default to 1."""
        from app.schemas.session_template import TemplateExerciseCreate

        ex = TemplateExerciseCreate(exercise_name="Squat")
        assert ex.sets == 1
