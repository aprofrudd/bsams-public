"""Tests for CSV Ingestion Service."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.schemas.upload import CSVColumnMapping
from app.services.csv_ingestion import CSVIngestionService


@pytest.fixture
def service():
    """Create CSVIngestionService instance."""
    return CSVIngestionService()


@pytest.fixture
def sample_csv():
    """Sample CSV content for testing."""
    return """Test Date,Athlete,Body Mass (kg),CMJ Height (cm),CMJ RSI
15/01/2024,John Doe,75.5,45.2,1.25
16/01/2024,John Doe,75.3,46.1,1.30
17/01/2024,John Doe,75.0,44.8,1.22"""


@pytest.fixture
def sample_csv_with_errors():
    """Sample CSV with some invalid rows."""
    return """Test Date,Athlete,Body Mass (kg),CMJ Height (cm)
15/01/2024,John Doe,75.5,45.2
invalid-date,Jane Doe,70.0,42.0
17/01/2024,Bob Smith,not-a-number,43.5
18/01/2024,Alice Brown,72.0,41.0"""


class TestParseDateDDMMYYYY:
    """Test date parsing."""

    def test_parse_valid_date_slash(self, service):
        """Should parse DD/MM/YYYY format."""
        result = service.parse_date_ddmmyyyy("15/01/2024")
        assert result == datetime(2024, 1, 15)

    def test_parse_valid_date_dash(self, service):
        """Should parse DD-MM-YYYY format."""
        result = service.parse_date_ddmmyyyy("15-01-2024")
        assert result == datetime(2024, 1, 15)

    def test_parse_valid_date_dot(self, service):
        """Should parse DD.MM.YYYY format."""
        result = service.parse_date_ddmmyyyy("15.01.2024")
        assert result == datetime(2024, 1, 15)

    def test_parse_date_with_whitespace(self, service):
        """Should handle whitespace around date."""
        result = service.parse_date_ddmmyyyy("  15/01/2024  ")
        assert result == datetime(2024, 1, 15)

    def test_reject_mmddyyyy_format(self, service):
        """Should reject MM/DD/YYYY format (US-centric)."""
        # 13/01/2024 is clearly DD/MM/YYYY (no month 13)
        result = service.parse_date_ddmmyyyy("13/01/2024")
        assert result.day == 13
        assert result.month == 1

    def test_invalid_date_raises(self, service):
        """Should raise ValueError for invalid date."""
        with pytest.raises(ValueError, match="Invalid date format"):
            service.parse_date_ddmmyyyy("invalid-date")

    def test_wrong_format_raises(self, service):
        """Should raise for YYYY-MM-DD format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            service.parse_date_ddmmyyyy("2024-01-15")


class TestParseNumeric:
    """Test numeric parsing."""

    def test_parse_integer(self, service):
        """Should parse integer values."""
        assert service.parse_numeric("42") == 42.0

    def test_parse_float(self, service):
        """Should parse float values."""
        assert service.parse_numeric("42.5") == 42.5

    def test_parse_with_whitespace(self, service):
        """Should handle whitespace."""
        assert service.parse_numeric("  42.5  ") == 42.5

    def test_empty_string_returns_none(self, service):
        """Should return None for empty string."""
        assert service.parse_numeric("") is None
        assert service.parse_numeric("   ") is None

    def test_na_values_return_none(self, service):
        """Should return None for NA-like values."""
        assert service.parse_numeric("NA") is None
        assert service.parse_numeric("n/a") is None
        assert service.parse_numeric("-") is None

    def test_invalid_value_raises(self, service):
        """Should raise ValueError for non-numeric values."""
        with pytest.raises(ValueError, match="Invalid numeric value"):
            service.parse_numeric("not-a-number")


class TestExtractMetrics:
    """Test metrics extraction."""

    def test_extract_cmj_height(self, service):
        """Should extract CMJ height metric."""
        row = {"CMJ Height (cm)": "45.5"}
        metrics = service.extract_metrics(row)

        assert metrics["test_type"] == "CMJ"
        assert metrics["height_cm"] == 45.5

    def test_extract_multiple_metrics(self, service):
        """Should extract multiple metrics."""
        row = {
            "CMJ Height (cm)": "45.5",
            "CMJ RSI": "1.25",
            "CMJ Flight Time (ms)": "500",
        }
        metrics = service.extract_metrics(row)

        assert metrics["test_type"] == "CMJ"
        assert metrics["height_cm"] == 45.5
        assert metrics["rsi"] == 1.25
        assert metrics["flight_time_ms"] == 500.0

    def test_skip_empty_values(self, service):
        """Should skip empty metric values."""
        row = {"CMJ Height (cm)": "45.5", "CMJ RSI": ""}
        metrics = service.extract_metrics(row)

        assert "height_cm" in metrics
        assert "rsi" not in metrics

    def test_skip_invalid_values(self, service):
        """Should skip invalid numeric values."""
        row = {"CMJ Height (cm)": "invalid", "CMJ RSI": "1.25"}
        metrics = service.extract_metrics(row)

        assert "height_cm" not in metrics
        assert metrics["rsi"] == 1.25

    def test_empty_row_returns_empty_dict(self, service):
        """Should return empty dict for row with no valid metrics."""
        row = {"Some Column": "value"}
        metrics = service.extract_metrics(row)
        assert metrics == {}


class TestProcessCSV:
    """Test full CSV processing."""

    def test_process_valid_csv(self, service, sample_csv):
        """Should process valid CSV and return events."""
        events, errors = service.process_csv(sample_csv)

        assert len(events) == 3
        assert len(errors) == 0

        # Check first event
        event = events[0]
        assert event["event_date"] == "2024-01-15"
        assert event["athlete_name"] == "John Doe"
        assert event["metrics"]["height_cm"] == 45.2
        assert event["metrics"]["rsi"] == 1.25
        assert event["metrics"]["body_mass_kg"] == 75.5

    def test_process_csv_with_athlete_id(self, service, sample_csv):
        """Should use provided athlete_id instead of CSV column."""
        athlete_id = uuid4()
        events, errors = service.process_csv(sample_csv, athlete_id=athlete_id)

        assert len(events) == 3
        assert events[0]["athlete_id"] == str(athlete_id)
        assert "athlete_name" not in events[0]

    def test_process_csv_with_errors(self, service, sample_csv_with_errors):
        """Should collect errors for invalid rows."""
        events, errors = service.process_csv(sample_csv_with_errors)

        assert len(events) == 3  # Rows 1, 3, 4 (row 2 has invalid date)
        assert len(errors) == 1
        assert errors[0].row == 3  # Invalid date row
        assert "Invalid date" in errors[0].reason

    def test_process_empty_csv(self, service):
        """Should handle empty CSV."""
        events, errors = service.process_csv("Test Date,CMJ Height (cm)\n")

        assert len(events) == 0
        assert len(errors) == 0

    def test_skip_rows_without_metrics(self, service):
        """Should skip rows that have no valid metrics."""
        csv_content = """Test Date,Body Mass (kg)
15/01/2024,75.5
16/01/2024,76.0"""

        events, errors = service.process_csv(csv_content)
        assert len(events) == 0  # No metric columns present


class TestValidateCSVStructure:
    """Test CSV structure validation."""

    def test_valid_structure(self, service, sample_csv):
        """Should return no warnings for valid CSV."""
        warnings = service.validate_csv_structure(sample_csv)
        assert len(warnings) == 0

    def test_missing_date_column(self, service):
        """Should warn about missing date column."""
        csv_content = "Athlete,CMJ Height (cm)\nJohn,45.5"
        warnings = service.validate_csv_structure(csv_content)

        assert any("date column" in w.lower() for w in warnings)

    def test_missing_metric_columns(self, service):
        """Should warn about missing metric columns."""
        csv_content = "Test Date,Athlete\n15/01/2024,John"
        warnings = service.validate_csv_structure(csv_content)

        assert any("metric columns" in w.lower() for w in warnings)

    def test_missing_mass_column_warning(self, service):
        """Should warn about missing mass column (but not error)."""
        csv_content = "Test Date,CMJ Height (cm)\n15/01/2024,45.5"
        warnings = service.validate_csv_structure(csv_content)

        mass_warnings = [w for w in warnings if "mass" in w.lower()]
        assert len(mass_warnings) == 1
        assert "optional" in mass_warnings[0].lower()


class TestCustomColumnMapping:
    """Test custom column mapping."""

    def test_custom_date_column(self):
        """Should use custom date column name."""
        mapping = CSVColumnMapping(date_column="Assessment Date")
        service = CSVIngestionService(mapping)

        csv_content = "Assessment Date,CMJ Height (cm)\n15/01/2024,45.5"
        events, errors = service.process_csv(csv_content)

        assert len(events) == 1
        assert events[0]["event_date"] == "2024-01-15"

    def test_custom_metric_mapping(self):
        """Should use custom metric column mapping."""
        mapping = CSVColumnMapping(
            date_column="Date",
            metric_columns={
                "Jump Height": {"test_type": "CMJ", "metric_key": "height_cm"},
            }
        )
        service = CSVIngestionService(mapping)

        csv_content = "Date,Jump Height\n15/01/2024,45.5"
        events, errors = service.process_csv(csv_content)

        assert len(events) == 1
        assert events[0]["metrics"]["height_cm"] == 45.5
