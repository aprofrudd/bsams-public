"""Tests for data export router (GDPR right to portability)."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
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
def mock_access_check():
    """Fixture to mock verify_athlete_access."""
    with patch("app.routers.data_export.verify_athlete_access") as mock:
        yield mock


@pytest.fixture
def sample_athlete_id():
    """Sample athlete ID."""
    return str(uuid4())


def _setup_empty_export(mock_supabase, sample_athlete_id):
    """Helper to set up mocks for an export with data in all tables."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    # All selects return empty
    mock_table.select.return_value.eq.return_value.execute.return_value.data = []
    mock_table.select.return_value.in_.return_value.execute.return_value.data = []

    return mock_table


class TestExportAthleteJson:
    """Test GET /api/v1/export/athlete/{athlete_id}"""

    def test_export_requires_auth(self):
        """Should return 401 when not authenticated."""
        # Remove the dependency override temporarily
        from app.core.security import get_current_user as real_dep

        original = app.dependency_overrides.get(real_dep)
        app.dependency_overrides.pop(real_dep, None)

        try:
            response = client.get(f"/api/v1/export/athlete/{uuid4()}")
            assert response.status_code == 401
        finally:
            if original:
                app.dependency_overrides[real_dep] = original
            else:
                # Re-apply conftest override
                from tests.conftest import override_get_current_user

                app.dependency_overrides[real_dep] = override_get_current_user

    def test_export_athlete_not_found(self, mock_supabase, mock_access_check):
        """Should return 404 when athlete not found or not owned."""
        mock_access_check.return_value = False

        response = client.get(f"/api/v1/export/athlete/{uuid4()}")

        assert response.status_code == 404
        assert "Athlete not found" in response.json()["detail"]

    def test_export_athlete_json_success(
        self, mock_supabase, mock_access_check, sample_athlete_id
    ):
        """Should return JSON export with all data sections."""
        mock_access_check.return_value = True
        _setup_empty_export(mock_supabase, sample_athlete_id)

        # Override athlete table to return a profile
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id, "first_name": "Test", "surname": "Athlete"}
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.select.return_value.in_.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/export/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert "export_date" in data
        assert "athlete" in data
        assert "performance_events" in data
        assert "training_sessions" in data
        assert "wellness_entries" in data
        assert "exercise_prescriptions" in data
        assert "vbt_profiles" in data
        assert "vbt_sets" in data
        assert "movement_assessments" in data
        assert "lactate_tests" in data
        assert "lactate_stages" in data
        assert "air_bike_tests" in data
        assert "air_bike_sprints" in data
        assert data["athlete"]["first_name"] == "Test"


class TestExportAthleteCsv:
    """Test GET /api/v1/export/athlete/{athlete_id}/csv"""

    def test_csv_export_not_found(self, mock_supabase, mock_access_check):
        """Should return 404 for non-existent athlete."""
        mock_access_check.return_value = False

        response = client.get(f"/api/v1/export/athlete/{uuid4()}/csv")

        assert response.status_code == 404

    def test_csv_export_returns_zip(
        self, mock_supabase, mock_access_check, sample_athlete_id
    ):
        """Should return ZIP file with correct content-type."""
        mock_access_check.return_value = True

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id, "first_name": "Test", "surname": "Athlete"}
                ]
            elif table_name == "performance_events":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "athlete_id": sample_athlete_id, "metrics": {"height_cm": 45.5}}
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.select.return_value.in_.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/export/athlete/{sample_athlete_id}/csv")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")


class TestCombineDataInExport:
    """Combine roster entries hold personal data that lives nowhere else."""

    def test_export_includes_combine_participation(self):
        """Bib, club, weight category and body mass must be portable."""
        from unittest.mock import MagicMock, patch
        from uuid import uuid4

        from fastapi.testclient import TestClient

        from app.main import app
        from tests.fake_supabase import FakeSupabase
        from tests.conftest import TEST_USER_ID

        athlete_id = str(uuid4())
        participant_id = str(uuid4())
        store = FakeSupabase(
            athletes=[{"id": athlete_id, "coach_id": str(TEST_USER_ID), "name": "Jack Reid"}],
            performance_events=[],
            training_sessions=[],
            wellness_entries=[],
            exercise_prescriptions=[],
            vbt_profiles=[],
            vbt_sets=[],
            movement_assessments=[],
            lactate_tests=[],
            lactate_stages=[],
            air_bike_tests=[],
            air_bike_sprints=[],
            combine_participants=[
                {
                    "id": participant_id,
                    "athlete_id": athlete_id,
                    "combine_event_id": str(uuid4()),
                    "bib": 12,
                    "club": "Repton",
                    "weight_category": "57kg",
                    "body_mass_kg": 57.2,
                }
            ],
            combine_attempts=[
                {
                    "id": str(uuid4()),
                    "participant_id": participant_id,
                    "station": "cmj",
                    "attempt_number": 1,
                    "measures": {"height_cm": 41.2},
                }
            ],
        )

        with patch("app.core.supabase_client.get_supabase_client", return_value=store):
            response = TestClient(app).get(f"/api/v1/export/athlete/{athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["combine_participants"][0]["bib"] == 12
        assert data["combine_participants"][0]["club"] == "Repton"
        assert data["combine_attempts"][0]["measures"]["height_cm"] == 41.2
