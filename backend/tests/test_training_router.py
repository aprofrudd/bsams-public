"""Tests for training sessions router."""

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
def sample_athlete_id():
    """Sample athlete ID."""
    return str(uuid4())


@pytest.fixture
def sample_session_data(sample_athlete_id):
    """Sample training session data for tests."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "session_date": "2024-01-15",
        "training_type": "Strength",
        "duration_minutes": 60,
        "rpe": 7,
        "srpe": 420,
        "notes": "Good session",
        "metrics": {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def setup_athlete_ownership_mock(mock_supabase, exists=True):
    """Helper to setup athlete ownership verification mock."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_eq1 = MagicMock()
    mock_select.eq.return_value = mock_eq1
    mock_eq2 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2
    mock_execute = MagicMock()
    mock_eq2.execute.return_value = mock_execute
    mock_execute.data = [{"id": "some-id"}] if exists else []
    return mock_supabase


class TestCreateTrainingSession:
    """Test POST /api/v1/training/sessions/"""

    def test_create_session_success(self, mock_supabase, sample_session_data, sample_athlete_id):
        """Should create and return new training session."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Athlete verification
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        # Insert
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [sample_session_data]

        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": sample_athlete_id,
                "session_date": "2024-01-15",
                "training_type": "Strength",
                "duration_minutes": 60,
                "rpe": 7,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["training_type"] == "Strength"
        assert data["duration_minutes"] == 60
        assert data["rpe"] == 7
        assert data["srpe"] == 420

    def test_create_session_athlete_not_found(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = []

        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": sample_athlete_id,
                "session_date": "2024-01-15",
                "training_type": "Strength",
                "duration_minutes": 60,
                "rpe": 7,
            },
        )

        assert response.status_code == 404

    def test_create_session_invalid_rpe(self):
        """Should return 422 for RPE out of range."""
        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(uuid4()),
                "session_date": "2024-01-15",
                "training_type": "Strength",
                "duration_minutes": 60,
                "rpe": 11,
            },
        )
        assert response.status_code == 422

    def test_create_session_invalid_rpe_zero(self):
        """Should return 422 for RPE below minimum."""
        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(uuid4()),
                "session_date": "2024-01-15",
                "training_type": "Boxing",
                "duration_minutes": 60,
                "rpe": 0,
            },
        )
        assert response.status_code == 422

    def test_create_session_invalid_duration(self):
        """Should return 422 for duration out of range."""
        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(uuid4()),
                "session_date": "2024-01-15",
                "training_type": "Strength",
                "duration_minutes": 0,
                "rpe": 7,
            },
        )
        assert response.status_code == 422

    def test_create_session_empty_training_type(self):
        """Should return 422 for empty training type."""
        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(uuid4()),
                "session_date": "2024-01-15",
                "training_type": "  ",
                "duration_minutes": 60,
                "rpe": 7,
            },
        )
        assert response.status_code == 422

    def test_create_session_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/training/sessions/",
                json={
                    "athlete_id": str(uuid4()),
                    "session_date": "2024-01-15",
                    "training_type": "Strength",
                    "duration_minutes": 60,
                    "rpe": 7,
                },
            )
        assert response.status_code == 503

    def test_create_session_with_notes_and_metrics(self, mock_supabase, sample_athlete_id):
        """Should create session with optional notes and metrics."""
        session_data = {
            "id": str(uuid4()),
            "athlete_id": sample_athlete_id,
            "session_date": "2024-01-15",
            "training_type": "Conditioning",
            "duration_minutes": 45,
            "rpe": 8,
            "srpe": 360,
            "notes": "Morning session",
            "metrics": {"height_cm": 35.0},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [session_data]

        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": sample_athlete_id,
                "session_date": "2024-01-15",
                "training_type": "Conditioning",
                "duration_minutes": 45,
                "rpe": 8,
                "notes": "Morning session",
                "metrics": {"height_cm": 35.0},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["notes"] == "Morning session"
        assert data["metrics"]["height_cm"] == 35.0


class TestListTrainingSessions:
    """Test GET /api/v1/training/sessions/athlete/{athlete_id}"""

    def test_list_sessions_success(self, mock_supabase, sample_athlete_id, sample_session_data):
        """Should return list of training sessions."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                    sample_session_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/training/sessions/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["training_type"] == "Strength"

    def test_list_sessions_athlete_not_found(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = []

        response = client.get(f"/api/v1/training/sessions/athlete/{sample_athlete_id}")

        assert response.status_code == 404

    def test_list_sessions_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(f"/api/v1/training/sessions/athlete/{uuid4()}")
        assert response.status_code == 503

    def test_list_sessions_with_date_filter(self, mock_supabase, sample_athlete_id, sample_session_data):
        """Should accept date filter parameters."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:
                mock_table.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.range.return_value.execute.return_value.data = [
                    sample_session_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/training/sessions/athlete/{sample_athlete_id}?start_date=2024-01-01&end_date=2024-01-31"
        )

        assert response.status_code == 200


class TestGetTrainingSession:
    """Test GET /api/v1/training/sessions/{session_id}"""

    def test_get_session_success(self, mock_supabase, sample_session_data, sample_athlete_id):
        """Should return single training session."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_session_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        response = client.get(f"/api/v1/training/sessions/{sample_session_data['id']}")

        assert response.status_code == 200
        assert response.json()["training_type"] == "Strength"

    def test_get_session_not_found(self, mock_supabase):
        """Should return 404 when session not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.get(f"/api/v1/training/sessions/{uuid4()}")

        assert response.status_code == 404


class TestUpdateTrainingSession:
    """Test PATCH /api/v1/training/sessions/{session_id}"""

    def test_update_session_success(self, mock_supabase, sample_session_data, sample_athlete_id):
        """Should update and return training session."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_session_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        updated_data = {**sample_session_data, "rpe": 8, "srpe": 480}
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated_data]

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_data['id']}",
            json={"rpe": 8},
        )

        assert response.status_code == 200

    def test_update_session_not_found(self, mock_supabase):
        """Should return 404 when session not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.patch(
            f"/api/v1/training/sessions/{uuid4()}",
            json={"rpe": 8},
        )

        assert response.status_code == 404

    def test_update_session_no_fields(self, mock_supabase, sample_session_data, sample_athlete_id):
        """Should return 400 when no fields provided."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_session_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        response = client.patch(
            f"/api/v1/training/sessions/{sample_session_data['id']}",
            json={},
        )

        assert response.status_code == 400


class TestDeleteTrainingSession:
    """Test DELETE /api/v1/training/sessions/{session_id}"""

    def test_delete_session_success(self, mock_supabase, sample_session_data, sample_athlete_id):
        """Should delete session and return 204."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_session_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete_eq = MagicMock()
        mock_delete.eq.return_value = mock_delete_eq
        mock_delete_eq.execute.return_value = None

        response = client.delete(f"/api/v1/training/sessions/{sample_session_data['id']}")

        assert response.status_code == 204

    def test_delete_session_not_found(self, mock_supabase):
        """Should return 404 when session not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.delete(f"/api/v1/training/sessions/{uuid4()}")

        assert response.status_code == 404


class TestTrainingSessionValidation:
    """Test schema validation for training sessions."""

    def test_rpe_min_boundary(self):
        """RPE of 1 should be accepted."""
        from app.schemas.training_session import TrainingSessionCreate

        session = TrainingSessionCreate(
            athlete_id=uuid4(),
            session_date="2024-01-15",
            training_type="Strength",
            duration_minutes=60,
            rpe=1,
        )
        assert session.rpe == 1

    def test_rpe_max_boundary(self):
        """RPE of 10 should be accepted."""
        from app.schemas.training_session import TrainingSessionCreate

        session = TrainingSessionCreate(
            athlete_id=uuid4(),
            session_date="2024-01-15",
            training_type="Strength",
            duration_minutes=60,
            rpe=10,
        )
        assert session.rpe == 10

    def test_duration_max_boundary(self):
        """Duration of 600 should be accepted."""
        from app.schemas.training_session import TrainingSessionCreate

        session = TrainingSessionCreate(
            athlete_id=uuid4(),
            session_date="2024-01-15",
            training_type="Strength",
            duration_minutes=600,
            rpe=5,
        )
        assert session.duration_minutes == 600

    def test_training_type_stripped(self):
        """Training type should be stripped of whitespace."""
        from app.schemas.training_session import TrainingSessionCreate

        session = TrainingSessionCreate(
            athlete_id=uuid4(),
            session_date="2024-01-15",
            training_type="  Boxing  ",
            duration_minutes=60,
            rpe=7,
        )
        assert session.training_type == "Boxing"
