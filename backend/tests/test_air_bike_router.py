"""Tests for air bike sprint test router."""

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
    """Sample air bike test data."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "test_date": "2024-06-15",
        "body_mass_kg": "75.0",
        "notes": "30s sprint test",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_sprints_data(sample_test_data):
    """Sample air bike sprints data (2 sprints)."""
    test_id = sample_test_data["id"]
    return [
        {
            "id": str(uuid4()),
            "test_id": test_id,
            "sprint_number": 1,
            "power_7s": "850.0",
            "power_14s": "720.0",
            "power_27s": "580.0",
            "blood_lactate_mmol": "8.50",
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid4()),
            "test_id": test_id,
            "sprint_number": 2,
            "power_7s": "790.0",
            "power_14s": "680.0",
            "power_27s": "530.0",
            "blood_lactate_mmol": "12.30",
            "created_at": datetime.now().isoformat(),
        },
    ]


class TestCreateTest:
    """Test POST /api/v1/air-bike/tests"""

    def test_create_two_sprints(self, mock_supabase, sample_test_data, sample_athlete_id, sample_sprints_data):
        """Should create and return new air bike test with 2 sprints."""
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

        call_count = [0]

        def insert_side_effect(data):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.execute.return_value.data = [sample_test_data]
            else:
                result.execute.return_value.data = sample_sprints_data
            return result

        mock_table.insert.side_effect = insert_side_effect

        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "notes": "30s sprint test",
                "sprints": [
                    {"sprint_number": 1, "power_7s": 850, "power_14s": 720, "power_27s": 580, "blood_lactate_mmol": 8.5},
                    {"sprint_number": 2, "power_7s": 790, "power_14s": 680, "power_27s": 530, "blood_lactate_mmol": 12.3},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["body_mass_kg"] == 75.0
        assert len(data["sprints"]) == 2

    def test_create_one_sprint(self, mock_supabase, sample_test_data, sample_athlete_id, sample_sprints_data):
        """Should create test with only 1 sprint."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        call_count = [0]

        def insert_side_effect(data):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.execute.return_value.data = [sample_test_data]
            else:
                result.execute.return_value.data = [sample_sprints_data[0]]
            return result

        mock_table.insert.side_effect = insert_side_effect

        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [
                    {"sprint_number": 1, "power_7s": 850, "power_14s": 720, "power_27s": 580},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["sprints"]) == 1

    def test_create_duplicate(self, mock_supabase, sample_athlete_id):
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
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [
                    {"sprint_number": 1, "power_7s": 850, "power_14s": 720, "power_27s": 580},
                ],
            },
        )
        assert response.status_code == 409


class TestListTests:
    """Test GET /api/v1/air-bike/tests/athlete/{athlete_id}"""

    def test_list_populated(self, mock_supabase, sample_athlete_id, sample_test_data, sample_sprints_data):
        """Should return list of air bike tests with max power computed."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.in_.return_value.order.return_value.execute.return_value.data = sample_sprints_data
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    sample_test_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/air-bike/tests/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sprint_count"] == 2
        assert data[0]["max_power_w"] == 850.0

    def test_list_empty(self, mock_supabase, sample_athlete_id):
        """Should return empty list when no tests."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.in_.return_value.order.return_value.execute.return_value.data = []
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/air-bike/tests/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestGetTest:
    """Test GET /api/v1/air-bike/tests/{test_id}"""

    def test_get_success(self, mock_supabase, sample_test_data, sample_sprints_data):
        """Should return single test with sprints."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "air_bike_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_sprints_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/air-bike/tests/{sample_test_data['id']}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sprints"]) == 2
        assert data["body_mass_kg"] == 75.0

    def test_get_not_found(self, mock_supabase):
        """Should return 404 when test not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/air-bike/tests/{uuid4()}")
        assert response.status_code == 404


class TestUpdateTest:
    """Test PATCH /api/v1/air-bike/tests/{test_id}"""

    def test_update_fields_only(self, mock_supabase, sample_test_data, sample_sprints_data):
        """Should update test fields without touching sprints."""
        from tests.conftest import TEST_USER_ID

        updated_data = {**sample_test_data, "notes": "Updated notes"}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "air_bike_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [updated_data]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_sprints_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/air-bike/tests/{sample_test_data['id']}",
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200

    def test_update_with_sprint_replacement(self, mock_supabase, sample_test_data, sample_sprints_data):
        """Should replace sprints when sprints provided."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "air_bike_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = sample_sprints_data
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
                mock_table.insert.return_value.execute.return_value.data = sample_sprints_data
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/air-bike/tests/{sample_test_data['id']}",
            json={
                "sprints": [
                    {"sprint_number": 1, "power_7s": 900, "power_14s": 750, "power_27s": 600},
                    {"sprint_number": 2, "power_7s": 800, "power_14s": 700, "power_27s": 550, "blood_lactate_mmol": 11.0},
                ],
            },
        )

        assert response.status_code == 200


class TestDeleteTest:
    """Test DELETE /api/v1/air-bike/tests/{test_id}"""

    def test_delete_success(self, mock_supabase, sample_test_data):
        """Should delete test and return 204."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "air_bike_tests":
                data_with_join = {
                    **sample_test_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/air-bike/tests/{sample_test_data['id']}")
        assert response.status_code == 204

    def test_delete_not_found(self, mock_supabase):
        """Should return 404 when test not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/air-bike/tests/{uuid4()}")
        assert response.status_code == 404


class TestOwnershipVerification:
    """Test ownership verification."""

    def test_athlete_not_owned(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not owned by coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/air-bike/tests/athlete/{sample_athlete_id}")
        assert response.status_code == 404

    def test_test_not_owned(self, mock_supabase, sample_test_data):
        """Should return 404 when test belongs to another coach's athlete."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        # Return test with different coach_id
        data_with_join = {
            **sample_test_data,
            "athletes": {"coach_id": str(uuid4())},  # Different coach
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]

        response = client.get(f"/api/v1/air-bike/tests/{sample_test_data['id']}")
        assert response.status_code == 404


class TestSplitSchemes:
    """7/17/27 combine protocol alongside the original 7/14/27 sprint test."""

    def _mock_athlete_ownership(self, mock_table, athlete_id):
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": athlete_id}]

    def test_create_with_17s_split(self, mock_supabase, sample_test_data, sample_athlete_id):
        """A 7/17/27 test saves, and the test row records split_scheme='7_17_27'."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        self._mock_athlete_ownership(mock_table, sample_athlete_id)

        sprint_row = {
            "id": str(uuid4()),
            "test_id": sample_test_data["id"],
            "sprint_number": 1,
            "power_7s": "880.0",
            "power_14s": None,
            "power_17s": "700.0",
            "power_27s": "600.0",
            "blood_lactate_mmol": None,
            "created_at": datetime.now().isoformat(),
        }
        inserted = []

        def insert_side_effect(data):
            inserted.append(data)
            result = MagicMock()
            if len(inserted) == 1:
                result.execute.return_value.data = [
                    {**sample_test_data, "split_scheme": "7_17_27"}
                ]
            else:
                result.execute.return_value.data = [sprint_row]
            return result

        mock_table.insert.side_effect = insert_side_effect

        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [
                    {"sprint_number": 1, "power_7s": 880, "power_17s": 700, "power_27s": 600}
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["split_scheme"] == "7_17_27"
        assert data["sprints"][0]["power_17s"] == 700.0
        assert data["sprints"][0]["power_14s"] is None
        # the test row was persisted with the right protocol
        assert inserted[0]["split_scheme"] == "7_17_27"
        assert inserted[1][0]["power_17s"] == 700.0

    def test_create_defaults_to_14s_scheme(self, mock_supabase, sample_test_data, sample_athlete_id, sample_sprints_data):
        """An existing-style 7/14/27 payload is unchanged and tagged '7_14_27'."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        self._mock_athlete_ownership(mock_table, sample_athlete_id)

        inserted = []

        def insert_side_effect(data):
            inserted.append(data)
            result = MagicMock()
            if len(inserted) == 1:
                result.execute.return_value.data = [sample_test_data]
            else:
                result.execute.return_value.data = [sample_sprints_data[0]]
            return result

        mock_table.insert.side_effect = insert_side_effect

        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [
                    {"sprint_number": 1, "power_7s": 850, "power_14s": 720, "power_27s": 580}
                ],
            },
        )

        assert response.status_code == 201
        assert response.json()["split_scheme"] == "7_14_27"
        assert inserted[0]["split_scheme"] == "7_14_27"

    def test_create_rejects_missing_mid_split(self, mock_supabase, sample_athlete_id):
        """No mid split at all is a validation error, not a NULL in the database."""
        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [{"sprint_number": 1, "power_7s": 850, "power_27s": 580}],
            },
        )
        assert response.status_code == 422
        assert "mid split" in response.text

    def test_create_rejects_both_mid_splits(self, mock_supabase, sample_athlete_id):
        """Sending both splits is ambiguous about which protocol was run."""
        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [
                    {
                        "sprint_number": 1,
                        "power_7s": 850,
                        "power_14s": 720,
                        "power_17s": 700,
                        "power_27s": 580,
                    }
                ],
            },
        )
        assert response.status_code == 422
        assert "only one mid split" in response.text.lower()

    def test_create_rejects_mixed_schemes_across_sprints(self, mock_supabase, sample_athlete_id):
        """Both sprints in one test must use the same protocol."""
        response = client.post(
            f"/api/v1/air-bike/tests?athlete_id={sample_athlete_id}",
            json={
                "test_date": "2024-06-15",
                "body_mass_kg": 75.0,
                "sprints": [
                    {"sprint_number": 1, "power_7s": 850, "power_14s": 720, "power_27s": 580},
                    {"sprint_number": 2, "power_7s": 790, "power_17s": 660, "power_27s": 530},
                ],
            },
        )
        assert response.status_code == 422
        assert "same split scheme" in response.text.lower()

    def test_list_max_power_handles_null_mid_split(self, mock_supabase, sample_athlete_id, sample_test_data):
        """REGRESSION: power_14s is now nullable — max_power_w must not raise on NULL."""
        test_row = {**sample_test_data, "split_scheme": "7_17_27"}
        sprint_rows = [
            {
                "id": str(uuid4()),
                "test_id": test_row["id"],
                "sprint_number": 1,
                "power_7s": "880.0",
                "power_14s": None,
                "power_17s": "700.0",
                "power_27s": "600.0",
                "blood_lactate_mmol": None,
                "created_at": datetime.now().isoformat(),
            }
        ]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.in_.return_value.order.return_value.execute.return_value.data = sprint_rows
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [test_row]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/air-bike/tests/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        item = response.json()[0]
        assert item["max_power_w"] == 880.0
        assert item["split_scheme"] == "7_17_27"
