"""Tests for gas analysis router endpoints."""

import csv
import io
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


def _make_csv_bytes(rows):
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


SAMPLE_TEST_ID = str(uuid4())
SAMPLE_ATHLETE_ID = str(uuid4())

SAMPLE_TEST_DATA = {
    "id": SAMPLE_TEST_ID,
    "athlete_id": SAMPLE_ATHLETE_ID,
    "test_date": "2024-06-15",
    "test_type": "cycling",
    "lt1_value": None,
    "lt2_value": None,
    "notes": None,
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
}

CYCLING_CSV_ROWS = [
    ["t", "V'O2", "HR", "FAT", "CHO", "Work Rate (W)"],
    ["60", "2.0", "130", "20.0", "30.0", "80"],
    ["90", "2.1", "132", "21.0", "31.0", "80"],
    ["120", "2.2", "135", "22.0", "32.0", "80"],
    ["150", "2.5", "145", "18.0", "40.0", "120"],
    ["180", "2.6", "148", "17.0", "42.0", "120"],
    ["210", "2.7", "150", "16.0", "44.0", "120"],
]


def _setup_test_ownership(mock_supabase, test_data=None):
    """Setup mocks for test ownership verification."""
    test = test_data or SAMPLE_TEST_DATA

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "lactate_tests":
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_eq = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value.data = [{
                **test,
                "athletes": {"coach_id": "00000000-0000-0000-0000-000000000001", "user_id": None},
            }]
        elif name == "lactate_stages":
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_eq = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_order = MagicMock()
            mock_eq.order.return_value = mock_order
            mock_order.execute.return_value.data = [
                {"intensity_value": 80},
                {"intensity_value": 120},
            ]
        elif name == "gas_analysis_data":
            mock_select = MagicMock()
            mock_table.select.return_value = mock_select
            mock_insert = MagicMock()
            mock_table.insert.return_value = mock_insert
            mock_delete = MagicMock()
            mock_table.delete.return_value = mock_delete

            mock_eq = MagicMock()
            mock_select.eq.return_value = mock_eq
            mock_eq.execute.return_value.data = []

            mock_delete_eq = MagicMock()
            mock_delete.eq.return_value = mock_delete_eq
            mock_delete_eq.execute.return_value.data = []

            mock_insert.execute.return_value.data = [{
                "id": str(uuid4()),
                "test_id": SAMPLE_TEST_ID,
                "interval_seconds": 30,
                "rest_start_seconds": 60,
                "stage_duration_seconds": 180,
                "rest_duration_seconds": 60,
                "averaging_method": "last_60s",
                "samples": [],
                "stage_averages": [
                    {"stage_number": 1, "intensity_value": 80, "avg_fat_gh": 21.0, "data_point_count": 3},
                    {"stage_number": 2, "intensity_value": 120, "avg_fat_gh": 17.0, "data_point_count": 3},
                ],
                "column_mapping": {},
                "max_fat_oxidation_gh": 21.0,
                "fat_max_stage_number": 1,
                "fat_max_intensity": 80,
                "fat_max_hr": None,
                "notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }]
        return mock_table

    mock_supabase.table.side_effect = table_side_effect


class TestPreviewGasAnalysis:
    """Test POST /api/v1/lactate/tests/{test_id}/gas-analysis/preview"""

    def test_preview_success(self, mock_supabase):
        _setup_test_ownership(mock_supabase)
        csv_bytes = _make_csv_bytes(CYCLING_CSV_ROWS)

        response = client.post(
            f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis/preview",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={
                "stage_duration_seconds": "180",
                "rest_duration_seconds": "60",
                "rest_start_seconds": "60",
                "averaging_method": "last_60s",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interval_seconds"] == 30
        assert data["stage_count"] >= 1
        assert data["sample_count"] >= 1
        assert len(data["columns_detected"]) > 0

    def test_preview_invalid_file(self, mock_supabase):
        _setup_test_ownership(mock_supabase)
        response = client.post(
            f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis/preview",
            files={"file": ("test.xml", b"<data/>", "application/xml")},
            data={"averaging_method": "last_60s"},
        )
        assert response.status_code == 400

    def test_preview_test_not_found(self, mock_supabase):
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.post(
            f"/api/v1/lactate/tests/{str(uuid4())}/gas-analysis/preview",
            files={"file": ("test.csv", b"t,V'O2\n60,2.0", "text/csv")},
            data={"averaging_method": "last_60s"},
        )
        assert response.status_code == 404


class TestUploadGasAnalysis:
    """Test POST /api/v1/lactate/tests/{test_id}/gas-analysis"""

    def test_upload_success(self, mock_supabase):
        _setup_test_ownership(mock_supabase)
        csv_bytes = _make_csv_bytes(CYCLING_CSV_ROWS)

        response = client.post(
            f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            data={
                "stage_duration_seconds": "180",
                "rest_duration_seconds": "60",
                "rest_start_seconds": "60",
                "averaging_method": "last_60s",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["test_id"] == SAMPLE_TEST_ID
        assert data["interval_seconds"] == 30

    def test_upload_duplicate_409(self, mock_supabase):
        """Should return 409 when gas analysis already exists."""
        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "lactate_tests":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = [{
                    **SAMPLE_TEST_DATA,
                    "athletes": {"coach_id": "00000000-0000-0000-0000-000000000001", "user_id": None},
                }]
            elif name == "gas_analysis_data":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = [{"id": str(uuid4())}]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis",
            files={"file": ("test.csv", b"t\n60", "text/csv")},
            data={"averaging_method": "last_60s"},
        )
        assert response.status_code == 409


class TestGetGasAnalysis:
    """Test GET /api/v1/lactate/tests/{test_id}/gas-analysis"""

    def test_get_success(self, mock_supabase):
        gas_data = {
            "id": str(uuid4()),
            "test_id": SAMPLE_TEST_ID,
            "interval_seconds": 30,
            "rest_start_seconds": 60,
            "stage_duration_seconds": 180,
            "rest_duration_seconds": 60,
            "averaging_method": "last_60s",
            "samples": [{"elapsed_s": 60, "vo2_l_min": 2.0}],
            "stage_averages": [{"stage_number": 1, "intensity_value": 80, "data_point_count": 3}],
            "column_mapping": {"elapsed_s": "t"},
            "max_fat_oxidation_gh": 25.0,
            "fat_max_stage_number": 2,
            "fat_max_intensity": 120,
            "fat_max_hr": 145,
            "notes": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        call_count = {"n": 0}

        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "lactate_tests":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = [{
                    **SAMPLE_TEST_DATA,
                    "athletes": {"coach_id": "00000000-0000-0000-0000-000000000001", "user_id": None},
                }]
            elif name == "gas_analysis_data":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = [gas_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["max_fat_oxidation_gh"] == 25.0
        assert data["max_fat_oxidation_gh"] == 25.0

    def test_get_not_found(self, mock_supabase):
        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "lactate_tests":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = [{
                    **SAMPLE_TEST_DATA,
                    "athletes": {"coach_id": "00000000-0000-0000-0000-000000000001", "user_id": None},
                }]
            elif name == "gas_analysis_data":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis")
        assert response.status_code == 404


class TestDeleteGasAnalysis:
    """Test DELETE /api/v1/lactate/tests/{test_id}/gas-analysis"""

    def test_delete_success(self, mock_supabase):
        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "lactate_tests":
                mock_select = MagicMock()
                mock_table.select.return_value = mock_select
                mock_eq = MagicMock()
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = [{
                    **SAMPLE_TEST_DATA,
                    "athletes": {"coach_id": "00000000-0000-0000-0000-000000000001", "user_id": None},
                }]
            elif name == "gas_analysis_data":
                mock_delete = MagicMock()
                mock_table.delete.return_value = mock_delete
                mock_eq = MagicMock()
                mock_delete.eq.return_value = mock_eq
                mock_eq.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/lactate/tests/{SAMPLE_TEST_ID}/gas-analysis")
        assert response.status_code == 204

    def test_delete_test_not_found(self, mock_supabase):
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value.data = []

        response = client.delete(f"/api/v1/lactate/tests/{str(uuid4())}/gas-analysis")
        assert response.status_code == 404
