"""Tests for air bike BLE recording endpoints."""

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
def sample_recording_data(sample_athlete_id):
    """Sample air bike recording data."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "test_date": "2024-06-15",
        "duration_s": 60,
        "avg_power_w": "150.0",
        "peak_power_w": "200.0",
        "total_work_j": "9000.0",
        "avg_cadence_rpm": "70.0",
        "peak_cadence_rpm": "85.0",
        "avg_speed_kmh": "25.50",
        "total_distance_m": "500.0",
        "total_calories_kcal": "15.0",
        "samples": [
            {"elapsed_ms": i * 1000, "watts": 150 + (i % 5) * 10, "cadence_rpm": 70, "speed_kmh": 25.5, "distance_m": i * 8.3, "calories_kcal": i * 0.25}
            for i in range(60)
        ],
        "notes": "60s recording",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _make_recording_payload():
    """Build a recording creation payload."""
    return {
        "test_date": "2024-06-15",
        "duration_s": 60,
        "samples": [
            {"elapsed_ms": i * 1000, "watts": 150, "cadence_rpm": 70, "speed_kmh": 25.5, "distance_m": i * 8.3, "calories_kcal": i * 0.25}
            for i in range(60)
        ],
        "notes": "60s recording",
    }


class TestCreateRecording:
    """Test POST /api/v1/air-bike/recordings"""

    def test_create_with_samples(self, mock_supabase, sample_recording_data, sample_athlete_id):
        """Should create recording with computed summary stats."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Athlete ownership check
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        mock_table.insert.return_value.execute.return_value.data = [sample_recording_data]

        response = client.post(
            f"/api/v1/air-bike/recordings?athlete_id={sample_athlete_id}",
            json=_make_recording_payload(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["avg_power_w"] is not None
        assert data["peak_power_w"] is not None
        assert data["total_work_j"] is not None


class TestListRecordings:
    """Test GET /api/v1/air-bike/recordings/athlete/{athlete_id}"""

    def test_list_recordings(self, mock_supabase, sample_athlete_id, sample_recording_data):
        """Should return list of recordings."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:
                compact = {
                    "id": sample_recording_data["id"],
                    "athlete_id": sample_recording_data["athlete_id"],
                    "test_date": sample_recording_data["test_date"],
                    "duration_s": sample_recording_data["duration_s"],
                    "avg_power_w": sample_recording_data["avg_power_w"],
                    "peak_power_w": sample_recording_data["peak_power_w"],
                    "total_work_j": sample_recording_data["total_work_j"],
                    "notes": sample_recording_data["notes"],
                    "created_at": sample_recording_data["created_at"],
                    "updated_at": sample_recording_data["updated_at"],
                }
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [compact]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/air-bike/recordings/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestGetRecording:
    """Test GET /api/v1/air-bike/recordings/{recording_id}"""

    def test_get_with_samples(self, mock_supabase, sample_recording_data):
        """Should return full recording with samples."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "air_bike_recordings":
                data_with_join = {
                    **sample_recording_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/air-bike/recordings/{sample_recording_data['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["samples"] is not None
        assert len(data["samples"]) == 60

    def test_get_not_found(self, mock_supabase):
        """Should return 404 when recording not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/air-bike/recordings/{uuid4()}")
        assert response.status_code == 404


class TestDeleteRecording:
    """Test DELETE /api/v1/air-bike/recordings/{recording_id}"""

    def test_delete_success(self, mock_supabase, sample_recording_data):
        """Should delete recording and return 204."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "air_bike_recordings":
                data_with_join = {
                    **sample_recording_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/air-bike/recordings/{sample_recording_data['id']}")
        assert response.status_code == 204

    def test_delete_not_found(self, mock_supabase):
        """Should return 404 when recording not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/air-bike/recordings/{uuid4()}")
        assert response.status_code == 404


class TestOwnership:
    """Test ownership/authorization."""

    def test_unauthorized_athlete(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not owned by coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/air-bike/recordings/athlete/{sample_athlete_id}")
        assert response.status_code == 404
