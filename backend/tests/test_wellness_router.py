"""Tests for wellness entries router (Validated Hooper Index)."""

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
def sample_wellness_data(sample_athlete_id):
    """Sample wellness entry data for tests (Hooper Index)."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "entry_date": "2024-01-15",
        "sleep": 3,
        "fatigue": 4,
        "stress": 2,
        "doms": 3,
        "hooper_index": 12,
        "notes": "Feeling good",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


class TestCreateWellnessEntry:
    """Test POST /api/v1/wellness/"""

    def test_create_entry_success(self, mock_supabase, sample_wellness_data, sample_athlete_id):
        """Should create and return new wellness entry."""
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
        mock_insert.execute.return_value.data = [sample_wellness_data]

        response = client.post(
            "/api/v1/wellness/",
            json={
                "athlete_id": sample_athlete_id,
                "entry_date": "2024-01-15",
                "sleep": 3,
                "fatigue": 4,
                "stress": 2,
                "doms": 3,
                "notes": "Feeling good",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sleep"] == 3
        assert data["fatigue"] == 4
        assert data["doms"] == 3
        assert data["hooper_index"] == 12

    def test_create_entry_athlete_not_found(self, mock_supabase, sample_athlete_id):
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
            "/api/v1/wellness/",
            json={
                "athlete_id": sample_athlete_id,
                "entry_date": "2024-01-15",
                "sleep": 3,
                "fatigue": 4,
                "stress": 2,
                "doms": 3,
            },
        )

        assert response.status_code == 404

    def test_create_entry_invalid_score_too_high(self):
        """Should return 422 for score above 7."""
        response = client.post(
            "/api/v1/wellness/",
            json={
                "athlete_id": str(uuid4()),
                "entry_date": "2024-01-15",
                "sleep": 8,
                "fatigue": 3,
                "stress": 2,
                "doms": 3,
            },
        )
        assert response.status_code == 422

    def test_create_entry_invalid_score_too_low(self):
        """Should return 422 for score below 1."""
        response = client.post(
            "/api/v1/wellness/",
            json={
                "athlete_id": str(uuid4()),
                "entry_date": "2024-01-15",
                "sleep": 0,
                "fatigue": 3,
                "stress": 2,
                "doms": 3,
            },
        )
        assert response.status_code == 422

    def test_create_entry_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/wellness/",
                json={
                    "athlete_id": str(uuid4()),
                    "entry_date": "2024-01-15",
                    "sleep": 3,
                    "fatigue": 4,
                    "stress": 2,
                    "doms": 3,
                },
            )
        assert response.status_code == 503

    def test_create_entry_duplicate_date(self, mock_supabase, sample_athlete_id):
        """Should return 409 for duplicate athlete+date."""
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
        mock_insert.execute.side_effect = Exception("duplicate key value violates unique constraint")

        response = client.post(
            "/api/v1/wellness/",
            json={
                "athlete_id": sample_athlete_id,
                "entry_date": "2024-01-15",
                "sleep": 3,
                "fatigue": 4,
                "stress": 2,
                "doms": 3,
            },
        )

        assert response.status_code == 409


class TestListWellnessEntries:
    """Test GET /api/v1/wellness/athlete/{athlete_id}"""

    def test_list_entries_success(self, mock_supabase, sample_athlete_id, sample_wellness_data):
        """Should return list of wellness entries."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                    sample_wellness_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/wellness/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sleep"] == 3
        assert data[0]["hooper_index"] == 12

    def test_list_entries_athlete_not_found(self, mock_supabase, sample_athlete_id):
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

        response = client.get(f"/api/v1/wellness/athlete/{sample_athlete_id}")

        assert response.status_code == 404

    def test_list_entries_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(f"/api/v1/wellness/athlete/{uuid4()}")
        assert response.status_code == 503


class TestGetWellnessEntry:
    """Test GET /api/v1/wellness/{entry_id}"""

    def test_get_entry_success(self, mock_supabase, sample_wellness_data, sample_athlete_id):
        """Should return single wellness entry."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_wellness_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        response = client.get(f"/api/v1/wellness/{sample_wellness_data['id']}")

        assert response.status_code == 200
        assert response.json()["sleep"] == 3

    def test_get_entry_not_found(self, mock_supabase):
        """Should return 404 when entry not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.get(f"/api/v1/wellness/{uuid4()}")

        assert response.status_code == 404


class TestUpdateWellnessEntry:
    """Test PATCH /api/v1/wellness/{entry_id}"""

    def test_update_entry_success(self, mock_supabase, sample_wellness_data, sample_athlete_id):
        """Should update and return wellness entry."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_wellness_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        updated_data = {**sample_wellness_data, "sleep": 5, "hooper_index": 14}
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_update_eq = MagicMock()
        mock_update.eq.return_value = mock_update_eq
        mock_update_eq.execute.return_value.data = [updated_data]

        response = client.patch(
            f"/api/v1/wellness/{sample_wellness_data['id']}",
            json={"sleep": 5},
        )

        assert response.status_code == 200

    def test_update_entry_not_found(self, mock_supabase):
        """Should return 404 when entry not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.patch(
            f"/api/v1/wellness/{uuid4()}",
            json={"sleep": 5},
        )

        assert response.status_code == 404

    def test_update_entry_no_fields(self, mock_supabase, sample_wellness_data, sample_athlete_id):
        """Should return 400 when no fields provided."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_wellness_data]

        mock_select2 = mock_table.select.return_value
        mock_eq2 = MagicMock()
        mock_select2.eq.return_value = mock_eq2
        mock_eq3 = MagicMock()
        mock_eq2.eq.return_value = mock_eq3
        mock_eq3.execute.return_value.data = [{"id": sample_athlete_id}]

        response = client.patch(
            f"/api/v1/wellness/{sample_wellness_data['id']}",
            json={},
        )

        assert response.status_code == 400


class TestDeleteWellnessEntry:
    """Test DELETE /api/v1/wellness/{entry_id}"""

    def test_delete_entry_success(self, mock_supabase, sample_wellness_data, sample_athlete_id):
        """Should delete entry and return 204."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.side_effect = [mock_select, MagicMock()]
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = [sample_wellness_data]

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

        response = client.delete(f"/api/v1/wellness/{sample_wellness_data['id']}")

        assert response.status_code == 204

    def test_delete_entry_not_found(self, mock_supabase):
        """Should return 404 when entry not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.delete(f"/api/v1/wellness/{uuid4()}")

        assert response.status_code == 404


class TestWellnessValidation:
    """Test schema validation for Hooper Index wellness entries."""

    def test_all_scores_at_boundaries(self):
        """All scores at min (1) and max (7) should be accepted."""
        from app.schemas.wellness import WellnessEntryCreate

        entry = WellnessEntryCreate(
            athlete_id=uuid4(),
            entry_date="2024-01-15",
            sleep=1,
            fatigue=1,
            stress=1,
            doms=1,
        )
        assert entry.sleep == 1

        entry2 = WellnessEntryCreate(
            athlete_id=uuid4(),
            entry_date="2024-01-15",
            sleep=7,
            fatigue=7,
            stress=7,
            doms=7,
        )
        assert entry2.doms == 7

    def test_hooper_index_range(self):
        """Hooper Index response should include computed index."""
        from app.schemas.wellness import WellnessEntryResponse

        resp = WellnessEntryResponse(
            id=uuid4(),
            athlete_id=uuid4(),
            entry_date="2024-01-15",
            sleep=2,
            fatigue=3,
            stress=4,
            doms=5,
            hooper_index=14,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.hooper_index == 14
