"""CSV Ingestion Service for parsing and importing performance data."""

import csv
import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.schemas.upload import CSVColumnMapping, CSVUploadResult, RowError
from app.schemas.metric_registry import METRIC_BY_KEY

# Fallback range limits for metrics not in registry
DEFAULT_METRIC_MIN = 0
DEFAULT_METRIC_MAX = 500
BODY_MASS_MAX = 300

# Regex to strip HTML tags
HTML_TAG_RE = re.compile(r"<[^>]+>")


class CSVIngestionService:
    """Service for parsing and processing CSV performance data."""

    @staticmethod
    def _strip_html(value: str) -> str:
        """Strip HTML tags from a string value."""
        return HTML_TAG_RE.sub("", value)

    def __init__(self, mapping: Optional[CSVColumnMapping] = None):
        """
        Initialize the ingestion service.

        Args:
            mapping: Column mapping configuration. Uses defaults if not provided.
        """
        self.mapping = mapping or CSVColumnMapping()

    def parse_date_ddmmyyyy(self, date_str: str) -> datetime:
        """
        Parse a date string in DD/MM/YYYY format.

        Args:
            date_str: Date string to parse.

        Returns:
            Parsed datetime object.

        Raises:
            ValueError: If date format is invalid.
        """
        date_str = date_str.strip()

        # Try DD/MM/YYYY format first (strict)
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid date format: {date_str}. Expected DD/MM/YYYY")

    def parse_numeric(self, value: str) -> Optional[float]:
        """
        Parse a numeric value from string.

        Args:
            value: String value to parse.

        Returns:
            Float value, or None if empty/invalid.

        Raises:
            ValueError: If value is non-empty but not numeric.
        """
        value = value.strip()
        if not value or value.lower() in ("", "na", "n/a", "-"):
            return None

        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Invalid numeric value: {value}")

    def extract_metrics(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract metrics from a CSV row based on column mapping.

        Args:
            row: Dictionary of column name -> value.

        Returns:
            JSONB-compatible metrics dictionary.
        """
        metrics: Dict[str, Any] = {}

        for csv_column, mapping_info in self.mapping.metric_columns.items():
            if csv_column in row:
                value = row[csv_column]
                try:
                    parsed_value = self.parse_numeric(value)
                    if parsed_value is not None:
                        # Validate metric range using registry (per-metric) or fallback
                        metric_key = mapping_info["metric_key"]
                        metric_def = METRIC_BY_KEY.get(metric_key)
                        if metric_def and metric_def.range:
                            m_min, m_max = metric_def.range
                        else:
                            m_min, m_max = DEFAULT_METRIC_MIN, DEFAULT_METRIC_MAX
                        if parsed_value < m_min or parsed_value > m_max:
                            continue
                        # Set test_type if not already set
                        if "test_type" not in metrics:
                            metrics["test_type"] = mapping_info["test_type"]
                        # Add the metric
                        metrics[mapping_info["metric_key"]] = parsed_value
                except ValueError:
                    # Skip invalid numeric values
                    pass

        return metrics

    def process_csv(
        self,
        csv_content: str,
        athlete_id: Optional[UUID] = None,
    ) -> Tuple[List[Dict[str, Any]], List[RowError]]:
        """
        Process CSV content and extract performance events.

        Args:
            csv_content: Raw CSV string content.
            athlete_id: Optional athlete ID to associate with all rows.
                       If not provided, will look for athlete column in CSV.

        Returns:
            Tuple of (processed_events, errors).
            Each event contains: athlete_id, event_date, body_mass_kg, metrics
        """
        events: List[Dict[str, Any]] = []
        errors: List[RowError] = []

        # Strip BOM if present
        if csv_content.startswith("\ufeff"):
            csv_content = csv_content[1:]

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                event = self._process_row(row, athlete_id)
                if event:
                    events.append(event)
            except ValueError as e:
                errors.append(RowError(row=row_num, reason=str(e)))

        return events, errors

    def _process_row(
        self,
        row: Dict[str, str],
        athlete_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single CSV row.

        Args:
            row: CSV row as dictionary.
            athlete_id: Optional athlete ID override.

        Returns:
            Event dictionary or None if row should be skipped.

        Raises:
            ValueError: If row has invalid data.
        """
        # Parse date (required)
        date_column = self.mapping.date_column
        if date_column not in row or not row[date_column].strip():
            raise ValueError(f"Missing required date column: {date_column}")

        try:
            event_date = self.parse_date_ddmmyyyy(row[date_column])
        except ValueError as e:
            raise ValueError(str(e))

        # Parse body mass (optional but recommended)
        body_mass_kg = None
        mass_column = self.mapping.mass_column
        if mass_column in row and row[mass_column].strip():
            try:
                body_mass_kg = self.parse_numeric(row[mass_column])
                if body_mass_kg is not None and (body_mass_kg < 0 or body_mass_kg > BODY_MASS_MAX):
                    body_mass_kg = None
            except ValueError:
                # Non-fatal: log but continue
                pass

        # Extract metrics
        metrics = self.extract_metrics(row)
        if not metrics:
            # Skip rows with no valid metrics
            return None

        # Add body mass to metrics if available
        if body_mass_kg is not None:
            metrics["body_mass_kg"] = body_mass_kg

        # Build event
        event = {
            "event_date": event_date.date().isoformat(),
            "metrics": metrics,
        }

        # Add athlete info
        if athlete_id:
            event["athlete_id"] = str(athlete_id)
        elif self.mapping.athlete_column and self.mapping.athlete_column in row:
            event["athlete_name"] = self._strip_html(row[self.mapping.athlete_column].strip())[:100]
        elif self.mapping.first_name_column and self.mapping.first_name_column in row:
            # Build name from First Name + Surname columns
            first = self._strip_html(row.get(self.mapping.first_name_column, "").strip())
            surname = self._strip_html(row.get(self.mapping.surname_column or "", "").strip())
            full_name = f"{first} {surname}".strip() if surname else first
            if full_name:
                event["athlete_name"] = full_name[:100]

        # Extract gender if available
        gender_col = self.mapping.gender_column
        if gender_col and gender_col in row:
            gender_val = row[gender_col].strip().lower()
            if gender_val in ("male", "female"):
                event["gender"] = gender_val

        return event

    def validate_csv_structure(self, csv_content: str) -> List[str]:
        """
        Validate CSV structure before processing.

        Args:
            csv_content: Raw CSV string content.

        Returns:
            List of validation warnings/errors.
        """
        warnings: List[str] = []

        # Strip BOM if present
        if csv_content.startswith("\ufeff"):
            csv_content = csv_content[1:]

        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            headers = reader.fieldnames or []

            # Check for required date column
            if self.mapping.date_column not in headers:
                warnings.append(f"Missing date column: {self.mapping.date_column}")

            # Check for at least one metric column
            found_metrics = [
                col for col in self.mapping.metric_columns.keys() if col in headers
            ]
            if not found_metrics:
                warnings.append(
                    f"No recognized metric columns found. Expected one of: {list(self.mapping.metric_columns.keys())}"
                )

            # Check for mass column (warning only)
            if self.mapping.mass_column not in headers:
                warnings.append(
                    f"Missing body mass column: {self.mapping.mass_column} (optional)"
                )

        except csv.Error as e:
            warnings.append(f"CSV parsing error: {e}")

        return warnings
