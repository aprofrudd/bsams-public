"""Tests for events router."""

from datetime import datetime, date
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
def sample_event_data(sample_athlete_id):
    """Sample event data for tests."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "event_date": "2024-01-15",
        "metrics": {"test_type": "CMJ", "height_cm": 45.5, "mass_kg": 75.0},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def setup_athlete_ownership_mock(mock_supabase, exists=True):
    """Helper to setup athlete ownership verification mock."""
    # This sets up the first table().select().eq().eq().execute() call
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


class TestListEventsForAthlete:
    """Test GET /api/v1/events/athlete/{athlete_id}"""

    def test_list_events_success(self, mock_supabase, sample_athlete_id, sample_event_data):
        """Should return list of events."""
        # Setup mock - need to handle both table calls (athletes and performance_events)
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                # Athlete verification - returns that athlete exists
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:  # performance_events
                # Events query chain with pagination (.range())
                mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                    sample_event_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/events/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["metrics"]["test_type"] == "CMJ"

    def test_list_events_athlete_not_found(self, mock_supabase, sample_athlete_id):
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

        response = client.get(f"/api/v1/events/athlete/{sample_athlete_id}")

        assert response.status_code == 404

    def test_list_events_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(f"/api/v1/events/athlete/{uuid4()}")

        assert response.status_code == 503


class TestGetEvent:
    """Test GET /api/v1/events/{event_id}"""

    def test_get_event_success(self, mock_supabase, sample_event_data, sample_athlete_id):
        """Should return single event."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call - get event
        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_event_data]

        # Second call - athlete verification
        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        response = client.get(f"/api/v1/events/{sample_event_data['id']}")

        assert response.status_code == 200
        assert response.json()["metrics"]["test_type"] == "CMJ"

    def test_get_event_not_found(self, mock_supabase):
        """Should return 404 when event not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.get(f"/api/v1/events/{uuid4()}")

        assert response.status_code == 404


class TestCreateEvent:
    """Test POST /api/v1/events/"""

    def test_create_event_success(self, mock_supabase, sample_event_data, sample_athlete_id):
        """Should create and return new event."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call - athlete verification
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        # Second call - insert
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [sample_event_data]

        response = client.post(
            "/api/v1/events/",
            json={
                "athlete_id": sample_athlete_id,
                "event_date": "2024-01-15",
                "metrics": {"test_type": "CMJ", "height_cm": 45.5},
            },
        )

        assert response.status_code == 201
        assert response.json()["metrics"]["test_type"] == "CMJ"

    def test_create_event_athlete_not_found(self, mock_supabase, sample_athlete_id):
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
            "/api/v1/events/",
            json={
                "athlete_id": sample_athlete_id,
                "event_date": "2024-01-15",
                "metrics": {"test_type": "CMJ"},
            },
        )

        assert response.status_code == 404


class TestUpdateEvent:
    """Test PATCH /api/v1/events/{event_id}"""

    def test_update_event_success(self, mock_supabase, sample_event_data, sample_athlete_id):
        """Should update and return event."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call - get existing event
        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_event_data]

        # Second call - athlete verification
        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        # Third call - update
        sample_event_data["metrics"]["height_cm"] = 46.0
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [sample_event_data]

        response = client.patch(
            f"/api/v1/events/{sample_event_data['id']}",
            json={"metrics": {"height_cm": 46.0}},
        )

        assert response.status_code == 200

    def test_update_event_not_found(self, mock_supabase):
        """Should return 404 when event not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.patch(
            f"/api/v1/events/{uuid4()}",
            json={"metrics": {"height_cm": 46.0}},
        )

        assert response.status_code == 404

    def test_update_event_no_fields(self, mock_supabase, sample_event_data, sample_athlete_id):
        """Should return 400 when no fields provided."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Get existing event
        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_event_data]

        # Athlete verification
        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        response = client.patch(
            f"/api/v1/events/{sample_event_data['id']}",
            json={},
        )

        assert response.status_code == 400


class TestDeleteEvent:
    """Test DELETE /api/v1/events/{event_id}"""

    def test_delete_event_success(self, mock_supabase, sample_event_data, sample_athlete_id):
        """Should delete event and return 204."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Get existing event
        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_event_data]

        # Athlete verification
        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        # Delete
        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_delete_eq = MagicMock()
        mock_delete.eq.return_value = mock_delete_eq
        mock_delete_eq.execute.return_value = None

        response = client.delete(f"/api/v1/events/{sample_event_data['id']}")

        assert response.status_code == 204

    def test_delete_event_not_found(self, mock_supabase):
        """Should return 404 when event not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.delete(f"/api/v1/events/{uuid4()}")

        assert response.status_code == 404
