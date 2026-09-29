"""Tests for uploads router."""

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


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """Test Date,Athlete,Body Mass (kg),CMJ Height (cm),CMJ RSI
15/01/2024,John Doe,75.5,45.2,1.25
16/01/2024,John Doe,75.3,46.1,1.30"""


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Create a file-like object for upload."""
    return io.BytesIO(sample_csv_content.encode("utf-8"))


class TestUploadCSV:
    """Test POST /api/v1/uploads/csv"""

    def test_upload_csv_with_athlete_id(self, mock_supabase, sample_csv_content):
        """Should process CSV and store events for specified athlete."""
        athlete_id = str(uuid4())
        coach_id = "00000000-0000-0000-0000-000000000001"

        # Mock athlete verification
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": athlete_id}
        ]

        # Mock event insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": str(uuid4())}
        ]

        response = client.post(
            f"/api/v1/uploads/csv?athlete_id={athlete_id}",
            files={"file": ("test.csv", sample_csv_content, "text/csv")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["processed"] == 2
        assert len(data["errors"]) == 0
        assert data["athlete_id"] == athlete_id

    def test_upload_csv_with_athlete_names(self, mock_supabase, sample_csv_content):
        """Should match athletes by name from CSV (case-insensitive)."""
        athlete_id = str(uuid4())

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                # Athlete lookup: .eq(coach_id).ilike(name)
                mock_table.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            else:
                # Event insert / dedup check
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.insert.return_value.execute.return_value.data = [
                    {"id": str(uuid4())}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", sample_csv_content, "text/csv")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["processed"] == 2

    def test_upload_csv_case_insensitive_athlete_match(self, mock_supabase):
        """Should match existing athlete regardless of case in CSV."""
        athlete_id = str(uuid4())
        csv_content = """Test Date,Athlete,CMJ Height (cm)
15/01/2024,JOHN DOE,45.2
16/01/2024,john doe,46.1"""

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                # ilike lookup finds existing athlete
                mock_table.select.return_value.eq.return_value.ilike.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.insert.return_value.execute.return_value.data = [
                    {"id": str(uuid4())}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 201
        data = response.json()
        # Both rows should resolve to the same athlete (no duplicate created)
        assert data["processed"] == 2

    def test_upload_non_csv_file_rejected(self):
        """Should reject non-CSV files."""
        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.txt", "not,a,csv", "text/plain")},
        )

        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_upload_invalid_utf8_rejected(self):
        """Should reject non-UTF8 encoded files."""
        invalid_content = b"\xff\xfe Invalid UTF-8"
        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", invalid_content, "text/csv")},
        )

        assert response.status_code == 400
        assert "UTF-8" in response.json()["detail"]

    def test_upload_missing_date_column_rejected(self, mock_supabase):
        """Should reject CSV without date column."""
        csv_content = "Athlete,CMJ Height (cm)\nJohn,45.5"

        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 400
        assert "date" in response.json()["detail"].lower()

    def test_upload_empty_csv_rejected(self, mock_supabase):
        """Should reject CSV with no valid data."""
        csv_content = "Test Date,CMJ Height (cm)\n"

        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 400
        assert "No valid data" in response.json()["detail"]

    def test_upload_database_unavailable(self, sample_csv_content):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                f"/api/v1/uploads/csv?athlete_id={uuid4()}",
                files={"file": ("test.csv", sample_csv_content, "text/csv")},
            )

        assert response.status_code == 503

    def test_upload_athlete_not_found_returns_404(self, sample_csv_content):
        """Should return 404 when athlete_id not found."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            # Configure mock to return empty data for athlete check
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

            response = client.post(
                f"/api/v1/uploads/csv?athlete_id={uuid4()}",
                files={"file": ("test.csv", sample_csv_content, "text/csv")},
            )

        assert response.status_code == 404
        assert "Athlete not found" in response.json()["detail"]


class TestUploadCSVDeduplication:
    """Test duplicate detection in CSV upload."""

    def test_upload_csv_skips_duplicates(self):
        """Should skip events that already exist (same athlete + date)."""
        athlete_id = str(uuid4())
        csv_content = """Test Date,CMJ Height (cm)
15/01/2024,45.2
16/01/2024,46.1"""

        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            call_count = {"n": 0}

            def table_side_effect(table_name):
                mock_table = MagicMock()
                if table_name == "athletes":
                    # Athlete verification
                    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id}
                    ]
                elif table_name == "performance_events":
                    if call_count["n"] == 0:
                        # Dedup check: one date already exists
                        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                            {"athlete_id": athlete_id, "event_date": "2024-01-15"},
                        ]
                        call_count["n"] += 1
                    else:
                        # Insert new events
                        mock_table.insert.return_value.execute.return_value.data = [
                            {"id": str(uuid4())}
                        ]
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = client.post(
                f"/api/v1/uploads/csv?athlete_id={athlete_id}",
                files={"file": ("test.csv", csv_content, "text/csv")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["processed"] == 1  # Only the non-duplicate
        # Should have a skip message in errors
        skip_errors = [e for e in data["errors"] if "duplicate" in e["reason"].lower()]
        assert len(skip_errors) == 1
        assert "1" in skip_errors[0]["reason"]

    def test_upload_csv_all_duplicates(self):
        """Should handle case where all events are duplicates."""
        athlete_id = str(uuid4())
        csv_content = """Test Date,CMJ Height (cm)
15/01/2024,45.2"""

        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            def table_side_effect(table_name):
                mock_table = MagicMock()
                if table_name == "athletes":
                    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id}
                    ]
                elif table_name == "performance_events":
                    # All dates already exist
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        {"athlete_id": athlete_id, "event_date": "2024-01-15"},
                    ]
                return mock_table

            mock_client.table.side_effect = table_side_effect

            response = client.post(
                f"/api/v1/uploads/csv?athlete_id={athlete_id}",
                files={"file": ("test.csv", csv_content, "text/csv")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["processed"] == 0  # All skipped


class TestPreviewCSV:
    """Test POST /api/v1/uploads/csv/preview"""

    def test_preview_valid_csv(self, sample_csv_content):
        """Should return preview of CSV data."""
        response = client.post(
            "/api/v1/uploads/csv/preview",
            files={"file": ("test.csv", sample_csv_content, "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "events_preview" in data
        assert "total_events" in data
        assert data["total_events"] == 2
        assert len(data["errors"]) == 0

    def test_preview_csv_with_errors(self):
        """Should return errors in preview."""
        csv_content = """Test Date,CMJ Height (cm)
15/01/2024,45.5
invalid-date,46.0"""

        response = client.post(
            "/api/v1/uploads/csv/preview",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 1
        assert len(data["errors"]) == 1

    def test_preview_csv_with_warnings(self):
        """Should return structure warnings."""
        csv_content = """Test Date,Some Column
15/01/2024,value"""

        response = client.post(
            "/api/v1/uploads/csv/preview",
            files={"file": ("test.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) > 0
