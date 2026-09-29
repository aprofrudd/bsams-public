"""Tests for metabolic profiling router."""

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
def sample_profile_data(sample_athlete_id):
    """Sample metabolic profile data as stored in DB."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "test_date": "2024-06-15",
        "body_mass_kg": "80.0",
        "data_source": "ble",
        "resting_lactate_mmol": "1.00",
        "la_peak_1_mmol": "5.00",
        "la_peak_2_mmol": "8.00",
        "la_peak_3_mmol": "10.00",
        "sprint_1_avg_power_w": "300.0",
        "sprint_2_avg_power_w": "250.0",
        "sprint_3_avg_power_w": "200.0",
        "alactic_capacity_j": "2496.0",
        "max_glycolytic_power_w": "54.3",
        "anaerobic_cost": "0.2172",
        "fatigue_slope_w": "72.5",
        "mech_work_sprint_1_j": "3000.0",
        "mech_work_sprint_2_j": "2500.0",
        "mech_work_sprint_3_j": "2000.0",
        "alactic_1_j": "2496.0",
        "alactic_2_j": "1957.0",
        "alactic_3_j": "1275.0",
        "glycolytic_1_j": "504.0",
        "glycolytic_2_j": "543.0",
        "glycolytic_3_j": "725.0",
        "trim_1_s": "0",
        "trim_2_s": "0",
        "trim_3_s": "0",
        "sprint_1_samples": [{"elapsed_ms": i * 1000, "watts": 300} for i in range(10)],
        "sprint_2_samples": [{"elapsed_ms": (10 + i) * 1000, "watts": 250} for i in range(10)],
        "sprint_3_samples": [{"elapsed_ms": (20 + i) * 1000, "watts": 200} for i in range(10)],
        "notes": "Test profile",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _make_ble_create_payload():
    """Build a BLE profile creation payload."""
    return {
        "test_date": "2024-06-15",
        "body_mass_kg": 80.0,
        "data_source": "ble",
        "resting_lactate_mmol": 1.0,
        "la_peak_1_mmol": 5.0,
        "la_peak_2_mmol": 8.0,
        "la_peak_3_mmol": 10.0,
        "sprint_1_samples": [{"elapsed_ms": i * 1000, "watts": 300} for i in range(10)],
        "sprint_2_samples": [{"elapsed_ms": (10 + i) * 1000, "watts": 250} for i in range(10)],
        "sprint_3_samples": [{"elapsed_ms": (20 + i) * 1000, "watts": 200} for i in range(10)],
        "notes": "Test profile",
    }


def _make_manual_create_payload():
    """Build a manual profile creation payload."""
    return {
        "test_date": "2024-06-15",
        "body_mass_kg": 80.0,
        "data_source": "manual",
        "resting_lactate_mmol": 1.0,
        "la_peak_1_mmol": 5.0,
        "la_peak_2_mmol": 8.0,
        "la_peak_3_mmol": 10.0,
        "sprint_1_avg_power_w": 300,
        "sprint_2_avg_power_w": 250,
        "sprint_3_avg_power_w": 200,
    }


class TestCreateProfile:
    """Test POST /api/v1/metabolic/profiles"""

    def test_create_ble_profile(self, mock_supabase, sample_profile_data, sample_athlete_id):
        """Should create a BLE metabolic profile with computed results."""
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

        # Insert
        mock_table.insert.return_value.execute.return_value.data = [sample_profile_data]

        response = client.post(
            f"/api/v1/metabolic/profiles?athlete_id={sample_athlete_id}",
            json=_make_ble_create_payload(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data_source"] == "ble"
        assert data["alactic_capacity_j"] is not None
        assert data["insights"] is not None

    def test_create_manual_profile(self, mock_supabase, sample_athlete_id):
        """Should create a manual metabolic profile."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        manual_profile = {
            "id": str(uuid4()),
            "athlete_id": sample_athlete_id,
            "test_date": "2024-06-15",
            "body_mass_kg": "80.0",
            "data_source": "manual",
            "resting_lactate_mmol": "1.00",
            "la_peak_1_mmol": "5.00",
            "la_peak_2_mmol": "8.00",
            "la_peak_3_mmol": "10.00",
            "sprint_1_avg_power_w": "300.0",
            "sprint_2_avg_power_w": "250.0",
            "sprint_3_avg_power_w": "200.0",
            "alactic_capacity_j": "2496.0",
            "max_glycolytic_power_w": "54.3",
            "anaerobic_cost": "0.2172",
            "fatigue_slope_w": "72.5",
            "mech_work_sprint_1_j": "3000.0",
            "mech_work_sprint_2_j": "2500.0",
            "mech_work_sprint_3_j": "2000.0",
            "alactic_1_j": "2496.0",
            "alactic_2_j": "1957.0",
            "alactic_3_j": "1275.0",
            "glycolytic_1_j": "504.0",
            "glycolytic_2_j": "543.0",
            "glycolytic_3_j": "725.0",
            "trim_1_s": "0",
            "trim_2_s": "0",
            "trim_3_s": "0",
            "sprint_1_samples": None,
            "sprint_2_samples": None,
            "sprint_3_samples": None,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        mock_table.insert.return_value.execute.return_value.data = [manual_profile]

        response = client.post(
            f"/api/v1/metabolic/profiles?athlete_id={sample_athlete_id}",
            json=_make_manual_create_payload(),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data_source"] == "manual"


class TestListProfiles:
    """Test GET /api/v1/metabolic/profiles/athlete/{athlete_id}"""

    def test_list_populated(self, mock_supabase, sample_athlete_id, sample_profile_data):
        """Should return list of metabolic profiles."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:
                compact = {
                    "id": sample_profile_data["id"],
                    "athlete_id": sample_profile_data["athlete_id"],
                    "test_date": sample_profile_data["test_date"],
                    "body_mass_kg": sample_profile_data["body_mass_kg"],
                    "data_source": sample_profile_data["data_source"],
                    "alactic_capacity_j": sample_profile_data["alactic_capacity_j"],
                    "max_glycolytic_power_w": sample_profile_data["max_glycolytic_power_w"],
                    "created_at": sample_profile_data["created_at"],
                    "updated_at": sample_profile_data["updated_at"],
                }
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [compact]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/metabolic/profiles/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["data_source"] == "ble"

    def test_list_empty(self, mock_supabase, sample_athlete_id):
        """Should return empty list when no profiles."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/metabolic/profiles/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        assert response.json() == []


class TestGetProfile:
    """Test GET /api/v1/metabolic/profiles/{profile_id}"""

    def test_get_success(self, mock_supabase, sample_profile_data):
        """Should return single profile with insights."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "metabolic_profiles":
                data_with_join = {
                    **sample_profile_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/metabolic/profiles/{sample_profile_data['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["alactic_capacity_j"] is not None
        assert data["insights"] is not None

    def test_get_not_found(self, mock_supabase):
        """Should return 404 when profile not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/metabolic/profiles/{uuid4()}")
        assert response.status_code == 404


class TestUpdateProfile:
    """Test PATCH /api/v1/metabolic/profiles/{profile_id}"""

    def test_update_trims_ble(self, mock_supabase, sample_profile_data):
        """Should recalculate on trim update for BLE profiles."""
        from tests.conftest import TEST_USER_ID

        data_with_join = {
            **sample_profile_data,
            "athletes": {"coach_id": str(TEST_USER_ID)},
        }

        # The PATCH endpoint: 1) verify ownership, 2) update, 3) re-fetch for recalc,
        # 4) update computed values, 5) get_profile (verify ownership again + return)
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [sample_profile_data]

        response = client.patch(
            f"/api/v1/metabolic/profiles/{sample_profile_data['id']}",
            json={"trim_1_s": 1.0},
        )

        assert response.status_code == 200

    def test_update_trims_manual_returns_400(self, mock_supabase, sample_profile_data):
        """Should return 400 when updating trims on manual profile."""
        from tests.conftest import TEST_USER_ID

        manual_data = {**sample_profile_data, "data_source": "manual"}
        data_with_join = {
            **manual_data,
            "athletes": {"coach_id": str(TEST_USER_ID)},
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]

        response = client.patch(
            f"/api/v1/metabolic/profiles/{sample_profile_data['id']}",
            json={"trim_1_s": 1.0},
        )

        assert response.status_code == 400

    def test_update_notes_only(self, mock_supabase, sample_profile_data):
        """Should update notes without recalculation."""
        from tests.conftest import TEST_USER_ID

        data_with_join = {
            **sample_profile_data,
            "athletes": {"coach_id": str(TEST_USER_ID)},
        }

        # Uses single mock_table since get_profile re-fetches from same table
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [sample_profile_data]

        response = client.patch(
            f"/api/v1/metabolic/profiles/{sample_profile_data['id']}",
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200


class TestDeleteProfile:
    """Test DELETE /api/v1/metabolic/profiles/{profile_id}"""

    def test_delete_success(self, mock_supabase, sample_profile_data):
        """Should delete profile and return 204."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "metabolic_profiles":
                data_with_join = {
                    **sample_profile_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/metabolic/profiles/{sample_profile_data['id']}")
        assert response.status_code == 204

    def test_delete_not_found(self, mock_supabase):
        """Should return 404 when profile not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/metabolic/profiles/{uuid4()}")
        assert response.status_code == 404


class TestOwnership:
    """Test ownership/authorization."""

    def test_unauthorized_athlete(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not owned by coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/metabolic/profiles/athlete/{sample_athlete_id}")
        assert response.status_code == 404

    def test_athlete_role_cannot_create(self, mock_supabase, sample_athlete_id, athlete_client):
        """Should return 403 when athlete tries to create profile."""
        response = athlete_client.post(
            f"/api/v1/metabolic/profiles?athlete_id={sample_athlete_id}",
            json=_make_ble_create_payload(),
        )
        assert response.status_code == 403
