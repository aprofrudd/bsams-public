"""Tests for lactate test router."""

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
def sample_test_data(sample_athlete_id):
    """Sample lactate test data for tests."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "test_date": "2024-06-15",
        "test_type": "running",
        "lt1_value": None,
        "lt1_lactate": None,
        "lt1_hr": None,
        "lt2_value": None,
        "lt2_lactate": None,
        "lt2_hr": None,
        "notes": "Treadmill test",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_stages_data(sample_test_data):
    """Sample lactate stages data."""
    test_id = sample_test_data["id"]
    return [
        {
            "id": str(uuid4()),
            "test_id": test_id,
            "stage_number": i + 1,
            "intensity_value": intensity,
            "heart_rate_bpm": hr,
            "blood_lactate_mmol": lactate,
            "rpe": None,
            "created_at": datetime.now().isoformat(),
        }
        for i, (intensity, hr, lactate) in enumerate([
            (8.0, 130, 0.8),
            (9.0, 140, 0.9),
            (10.0, 150, 1.2),
            (11.0, 160, 2.0),
            (12.0, 170, 3.5),
            (13.0, 180, 6.0),
            (14.0, 190, 9.0),
        ])
    ]


class TestCreateTest:
    """Test POST /api/v1/lactate/tests"""

    def test_create_success(self, mock_supabase, sample_test_data, sample_athlete_id, sample_stages_data):
        """Should create and return new lactate test."""
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

        # Insert test
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [sample_test_data]

        # Stages insert (second call to insert)
        # We need to handle two inserts: first for test, second for stages
        call_count = [0]
        original_insert = mock_table.insert

        def insert_side_effect(data):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.execute.return_value.data = [sample_test_data]
            else:
                result.execute.return_value.data = sample_stages_data
            return result

        mock_table.insert.side_effect = insert_side_effect

        response = client.post(
            f"/api/v1/lactate/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "test_type": "running",
                "notes": "Treadmill test",
                "stages": [
                    {"intensity_value": 8.0, "blood_lactate_mmol": 0.8, "heart_rate_bpm": 130},
                    {"intensity_value": 9.0, "blood_lactate_mmol": 0.9, "heart_rate_bpm": 140},
                    {"intensity_value": 10.0, "blood_lactate_mmol": 1.2, "heart_rate_bpm": 150},
                    {"intensity_value": 11.0, "blood_lactate_mmol": 2.0, "heart_rate_bpm": 160},
                    {"intensity_value": 12.0, "blood_lactate_mmol": 3.5, "heart_rate_bpm": 170},
                    {"intensity_value": 13.0, "blood_lactate_mmol": 6.0, "heart_rate_bpm": 180},
                    {"intensity_value": 14.0, "blood_lactate_mmol": 9.0, "heart_rate_bpm": 190},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["test_type"] == "running"

    def test_create_duplicate(self, mock_supabase, sample_athlete_id):
        """Should return 409 for duplicate athlete+type+date."""
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
            f"/api/v1/lactate/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "test_type": "running",
                "stages": [
                    {"intensity_value": 8.0, "blood_lactate_mmol": 0.8},
                ],
            },
        )
        assert response.status_code == 409


class TestListTests:
    """Test GET /api/v1/lactate/tests/athlete/{athlete_id}"""

    def test_list_success(self, mock_supabase, sample_athlete_id, sample_test_data, sample_stages_data):
        """Should return list of lactate tests."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.in_.return_value.order.return_value.execute.return_value.data = sample_stages_data
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_test_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/lactate/tests/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["test_type"] == "running"
        assert data[0]["stage_count"] == 7

    def test_list_with_type_filter(self, mock_supabase, sample_athlete_id, sample_test_data):
        """Should apply test_type filter when provided."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.in_.return_value.order.return_value.execute.return_value.data = []
            else:
                mock_query = MagicMock()
                mock_table.select.return_value.eq.return_value.order.return_value = mock_query
                mock_query.eq.return_value.execute.return_value.data = [sample_test_data]
                mock_query.execute.return_value.data = [sample_test_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/lactate/tests/athlete/{sample_athlete_id}?test_type=running"
        )

        assert response.status_code == 200


class TestGetTest:
    """Test GET /api/v1/lactate/tests/{test_id}"""

    def test_get_success(self, mock_supabase, sample_test_data, sample_stages_data):
        """Should return single test with stages and analysis."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "lactate_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_stages_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/lactate/tests/{sample_test_data['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["test_type"] == "running"
        assert len(data["stages"]) == 7
        # With 7 stages, analysis should be present
        assert data["analysis"] is not None

    def test_get_not_found(self, mock_supabase):
        """Should return 404 when test not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/lactate/tests/{uuid4()}")
        assert response.status_code == 404


class TestUpdateTest:
    """Test PATCH /api/v1/lactate/tests/{test_id}"""

    def test_update_fields_only(self, mock_supabase, sample_test_data, sample_stages_data):
        """Should update test fields without touching stages."""
        from tests.conftest import TEST_USER_ID

        updated_data = {**sample_test_data, "notes": "Updated notes"}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "lactate_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_stages_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/lactate/tests/{sample_test_data['id']}",
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200

    def test_update_with_stage_replacement(self, mock_supabase, sample_test_data, sample_stages_data):
        """Should replace stages when stages provided."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "lactate_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_stages_data
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
                mock_table.insert.return_value.execute.return_value.data = sample_stages_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/lactate/tests/{sample_test_data['id']}",
            json={
                "stages": [
                    {"intensity_value": 8.0, "blood_lactate_mmol": 0.8},
                    {"intensity_value": 9.0, "blood_lactate_mmol": 0.9},
                    {"intensity_value": 10.0, "blood_lactate_mmol": 1.2},
                    {"intensity_value": 11.0, "blood_lactate_mmol": 2.0},
                    {"intensity_value": 12.0, "blood_lactate_mmol": 3.5},
                ],
            },
        )

        assert response.status_code == 200


class TestDeleteTest:
    """Test DELETE /api/v1/lactate/tests/{test_id}"""

    def test_delete_success(self, mock_supabase, sample_test_data):
        """Should delete test and return 204."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "lactate_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/lactate/tests/{sample_test_data['id']}")
        assert response.status_code == 204

    def test_delete_not_found(self, mock_supabase):
        """Should return 404 when test not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/lactate/tests/{uuid4()}")
        assert response.status_code == 404


class TestAutoDetect:
    """Test POST /api/v1/lactate/tests/{test_id}/detect"""

    def test_auto_detect_success(self, mock_supabase, sample_test_data, sample_stages_data):
        """Should return analysis with suggested LT1/LT2."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "lactate_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_stages_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(f"/api/v1/lactate/tests/{sample_test_data['id']}/detect")

        assert response.status_code == 200
        data = response.json()
        assert data["analysis"] is not None
        assert data["analysis"]["suggested_lt1_value"] is not None
        assert data["analysis"]["suggested_lt2_value"] is not None
        assert data["analysis"]["suggested_lt1_value"] < data["analysis"]["suggested_lt2_value"]

    def test_auto_detect_insufficient_data(self, mock_supabase, sample_test_data):
        """Should return analysis=None when insufficient stages."""
        from tests.conftest import TEST_USER_ID

        few_stages = [
            {
                "id": str(uuid4()),
                "test_id": sample_test_data["id"],
                "stage_number": i + 1,
                "intensity_value": float(8 + i),
                "heart_rate_bpm": 130 + i * 10,
                "blood_lactate_mmol": 1.0 + i * 0.5,
                "rpe": None,
                "created_at": datetime.now().isoformat(),
            }
            for i in range(3)
        ]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "lactate_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "lactate_stages":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = few_stages
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(f"/api/v1/lactate/tests/{sample_test_data['id']}/detect")

        assert response.status_code == 200
        data = response.json()
        assert data["analysis"] is None


class TestOwnershipVerification:
    """Test ownership verification."""

    def test_athlete_not_owned(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not owned by coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/lactate/tests/athlete/{sample_athlete_id}")
        assert response.status_code == 404
