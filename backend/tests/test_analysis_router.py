"""Tests for analysis router."""

from datetime import date, datetime
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_ADMIN_ID, TEST_USER_ID

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_athletes():
    """Sample athlete data."""
    return [
        {"id": str(uuid4()), "gender": "male"},
        {"id": str(uuid4()), "gender": "male"},
        {"id": str(uuid4()), "gender": "female"},
    ]


@pytest.fixture
def sample_events():
    """Sample performance events with metrics."""
    return [
        {"metrics": {"height_cm": 45.0, "body_mass_kg": 72.0}},
        {"metrics": {"height_cm": 46.0, "body_mass_kg": 73.0}},
        {"metrics": {"height_cm": 44.0, "body_mass_kg": 71.0}},
        {"metrics": {"height_cm": 47.0, "body_mass_kg": 74.0}},
        {"metrics": {"height_cm": 43.0, "body_mass_kg": 75.0}},
    ]


class TestGetBenchmarks:
    """Test GET /api/v1/analysis/benchmarks"""

    def test_benchmarks_cohort(self, mock_supabase, sample_athletes, sample_events):
        """Should return benchmarks for whole cohort."""

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:  # performance_events
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mean"] == 45.0  # Mean of 45, 46, 44, 47, 43
        assert data["count"] == 5
        assert data["reference_group"] == "cohort"
        assert data["metric"] == "height_cm"

    def test_benchmarks_by_gender(self, mock_supabase, sample_athletes, sample_events):
        """Should filter benchmarks by gender."""
        male_athletes = [a for a in sample_athletes if a["gender"] == "male"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events[:2]  # Only events for male athletes
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "gender", "gender": "male"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reference_group"] == "gender"

    def test_benchmarks_gender_required(self, mock_supabase):
        """Should require gender param when reference_group=gender."""
        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "gender"},
        )

        assert response.status_code == 400
        assert "Gender parameter required" in response.json()["detail"]

    def test_benchmarks_mass_band_required(self, mock_supabase):
        """Should require mass_band param when reference_group=mass_band."""
        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "mass_band"},
        )

        assert response.status_code == 400
        assert "Mass band parameter required" in response.json()["detail"]

    def test_benchmarks_by_mass_band(self, mock_supabase, sample_athletes, sample_events):
        """Should filter benchmarks by mass band."""

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={
                "metric": "height_cm",
                "reference_group": "mass_band",
                "mass_band": "70-74.9kg",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Only events with mass 72, 73, 71, 74 fall in 70-74.9kg band
        assert data["count"] == 4

    def test_benchmarks_no_athletes(self, mock_supabase):
        """Should return zero count when no athletes."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm"},
        )

        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_benchmarks_database_unavailable(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(
                "/api/v1/analysis/benchmarks",
                params={"metric": "height_cm"},
            )

        assert response.status_code == 503


class TestGetAthleteZScore:
    """Test GET /api/v1/analysis/athlete/{athlete_id}/zscore"""

    def test_zscore_cohort(self, mock_supabase, sample_athletes, sample_events):
        """Should calculate Z-score against whole cohort."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                # First call: verify athlete
                # Second call: get all athletes for reference
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                # First call: get athlete's event
                # Second call: get all events for reference
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 47.0, "body_mass_kg": 72.0}}
                ]
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 47.0
        assert "z_score" in data
        assert data["mean"] == 45.0
        assert data["reference_group"] == "cohort"

    def test_zscore_athlete_not_found(self, mock_supabase):
        """Should return 404 when athlete not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.get(
            f"/api/v1/analysis/athlete/{uuid4()}/zscore",
            params={"metric": "height_cm"},
        )

        assert response.status_code == 404

    def test_zscore_no_events(self, mock_supabase, sample_athletes):
        """Should return 404 when no events for athlete."""

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = (
                    []
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{sample_athletes[0]['id']}/zscore",
            params={"metric": "height_cm"},
        )

        assert response.status_code == 404
        assert "No events found" in response.json()["detail"]

    def test_zscore_metric_not_found(self, mock_supabase, sample_athletes):
        """Should return 404 when metric not in event."""

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"other_metric": 10.0}}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{sample_athletes[0]['id']}/zscore",
            params={"metric": "height_cm"},
        )

        assert response.status_code == 404
        assert "not found in event" in response.json()["detail"]

    def test_zscore_database_unavailable(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(
                f"/api/v1/analysis/athlete/{uuid4()}/zscore",
                params={"metric": "height_cm"},
            )

        assert response.status_code == 503


    def test_zscore_includes_percentile_rank(self, mock_supabase, sample_athletes, sample_events):
        """Should include percentile_rank in zscore response."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 47.0, "body_mass_kg": 72.0}}
                ]
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "percentile_rank" in data
        assert 0 <= data["percentile_rank"] <= 100


class TestGetAthleteZScoresBulk:
    """Test GET /api/v1/analysis/athlete/{athlete_id}/zscores"""

    def test_bulk_zscores_returns_dict(self, mock_supabase, sample_athletes, sample_events):
        """Should return a dict mapping event_id to Z-score response."""
        athlete_id = sample_athletes[0]["id"]
        event_ids = [str(uuid4()), str(uuid4())]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                # Athlete events
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": event_ids[0], "metrics": {"height_cm": 45.0, "body_mass_kg": 72.0}},
                    {"id": event_ids[1], "metrics": {"height_cm": 47.0, "body_mass_kg": 74.0}},
                ]
                # Reference events
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscores",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should have entries for both events
        assert len(data) == 2
        for event_id in event_ids:
            assert event_id in data
            assert "z_score" in data[event_id]
            assert "mean" in data[event_id]
            assert "value" in data[event_id]

    def test_bulk_zscores_include_percentile_rank(self, mock_supabase, sample_athletes, sample_events):
        """Should include percentile_rank in each bulk zscore entry."""
        athlete_id = sample_athletes[0]["id"]
        event_ids = [str(uuid4()), str(uuid4())]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": event_ids[0], "metrics": {"height_cm": 45.0, "body_mass_kg": 72.0}},
                    {"id": event_ids[1], "metrics": {"height_cm": 47.0, "body_mass_kg": 74.0}},
                ]
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscores",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        data = response.json()
        for event_id in event_ids:
            assert "percentile_rank" in data[event_id]
            assert 0 <= data[event_id]["percentile_rank"] <= 100

    def test_bulk_zscores_empty_when_no_events(self, mock_supabase, sample_athletes):
        """Should return empty dict when athlete has no events."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscores",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        assert response.json() == {}

    def test_bulk_zscores_skips_events_without_metric(self, mock_supabase, sample_athletes, sample_events):
        """Should skip events that don't contain the requested metric."""
        athlete_id = sample_athletes[0]["id"]
        event_with_metric = str(uuid4())
        event_without_metric = str(uuid4())

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = (
                    sample_athletes
                )
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": event_with_metric, "metrics": {"height_cm": 45.0}},
                    {"id": event_without_metric, "metrics": {"sj_height_cm": 35.0}},
                ]
                mock_table.select.return_value.in_.return_value.execute.return_value.data = (
                    sample_events
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscores",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )

        assert response.status_code == 200
        data = response.json()
        assert event_with_metric in data
        assert event_without_metric not in data

    def test_bulk_zscores_athlete_not_found(self, mock_supabase):
        """Should return 404 when athlete not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.get(
            f"/api/v1/analysis/athlete/{uuid4()}/zscores",
            params={"metric": "height_cm"},
        )

        assert response.status_code == 404

    def test_bulk_zscores_database_unavailable(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(
                f"/api/v1/analysis/athlete/{uuid4()}/zscores",
                params={"metric": "height_cm"},
            )

        assert response.status_code == 503


class TestGetAthleteMetrics:
    """Test GET /api/v1/analysis/athlete/{athlete_id}/metrics"""

    def test_returns_distinct_metric_keys(self, mock_supabase, sample_athletes):
        """Should return sorted list of distinct metric keys, excluding metadata."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"metrics": {"test_type": "CMJ", "height_cm": 45.0, "body_mass_kg": 72.0}},
                    {"metrics": {"test_type": "SJ", "sj_height_cm": 35.0, "body_mass_kg": 72.0}},
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/analysis/athlete/{athlete_id}/metrics")

        assert response.status_code == 200
        data = response.json()
        # Should exclude test_type and body_mass_kg
        assert "test_type" not in data
        assert "body_mass_kg" not in data
        assert "height_cm" in data
        assert "sj_height_cm" in data
        assert data == sorted(data)

    def test_returns_empty_when_no_events(self, mock_supabase, sample_athletes):
        """Should return empty list when athlete has no events."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/analysis/athlete/{athlete_id}/metrics")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_404_for_unknown_athlete(self, mock_supabase):
        """Should return 404 when athlete not found."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        response = client.get(f"/api/v1/analysis/athlete/{uuid4()}/metrics")

        assert response.status_code == 404

    def test_returns_503_when_db_unavailable(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(f"/api/v1/analysis/athlete/{uuid4()}/metrics")

        assert response.status_code == 503


class TestDateFiltering:
    """Test date range filtering on analysis endpoints."""

    def _make_chainable_mock(self):
        """Create a mock that supports Supabase query chaining with tracking."""
        mock = MagicMock()
        mock.select.return_value = mock
        mock.eq.return_value = mock
        mock.in_.return_value = mock
        mock.gte.return_value = mock
        mock.lte.return_value = mock
        mock.order.return_value = mock
        mock.limit.return_value = mock
        return mock

    def test_benchmarks_with_date_range(self, mock_supabase, sample_athletes, sample_events):
        """Should apply both gte and lte when start_date and end_date provided."""
        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = sample_athletes

        events_mock = self._make_chainable_mock()
        events_mock.execute.return_value.data = sample_events

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            return events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={
                "metric": "height_cm",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )

        assert response.status_code == 200
        events_mock.gte.assert_called_with("event_date", "2024-01-01")
        events_mock.lte.assert_called_with("event_date", "2024-12-31")

    def test_benchmarks_with_start_date_only(self, mock_supabase, sample_athletes, sample_events):
        """Should only apply gte when only start_date provided."""
        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = sample_athletes

        events_mock = self._make_chainable_mock()
        events_mock.execute.return_value.data = sample_events

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            return events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "start_date": "2024-06-01"},
        )

        assert response.status_code == 200
        events_mock.gte.assert_called_with("event_date", "2024-06-01")
        events_mock.lte.assert_not_called()

    def test_benchmarks_with_end_date_only(self, mock_supabase, sample_athletes, sample_events):
        """Should only apply lte when only end_date provided."""
        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = sample_athletes

        events_mock = self._make_chainable_mock()
        events_mock.execute.return_value.data = sample_events

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            return events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "end_date": "2024-12-31"},
        )

        assert response.status_code == 200
        events_mock.gte.assert_not_called()
        events_mock.lte.assert_called_with("event_date", "2024-12-31")

    def test_benchmarks_no_dates_backward_compat(self, mock_supabase, sample_athletes, sample_events):
        """Should not apply gte/lte when no dates provided (backward compat)."""
        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = sample_athletes

        events_mock = self._make_chainable_mock()
        events_mock.execute.return_value.data = sample_events

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            return events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm"},
        )

        assert response.status_code == 200
        events_mock.gte.assert_not_called()
        events_mock.lte.assert_not_called()

    def test_bulk_zscores_with_date_range(self, mock_supabase, sample_athletes, sample_events):
        """Should apply date filters to both athlete events and reference events."""
        athlete_id = sample_athletes[0]["id"]
        event_ids = [str(uuid4())]

        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = [sample_athletes[0]]

        # We need separate mocks for athlete events and ref events queries
        athlete_events_mock = self._make_chainable_mock()
        athlete_events_mock.execute.return_value.data = [
            {"id": event_ids[0], "metrics": {"height_cm": 45.0}},
        ]

        ref_events_mock = self._make_chainable_mock()
        ref_events_mock.execute.return_value.data = sample_events

        call_count = {"events": 0}

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            # First events call = athlete events, second = reference events
            call_count["events"] += 1
            if call_count["events"] == 1:
                return athlete_events_mock
            return ref_events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscores",
            params={
                "metric": "height_cm",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )

        assert response.status_code == 200
        # Both athlete events and ref events queries should have date filters
        athlete_events_mock.gte.assert_called_with("event_date", "2024-01-01")
        athlete_events_mock.lte.assert_called_with("event_date", "2024-12-31")
        ref_events_mock.gte.assert_called_with("event_date", "2024-01-01")
        ref_events_mock.lte.assert_called_with("event_date", "2024-12-31")

    def test_zscore_date_filters_reference_only(self, mock_supabase, sample_athletes, sample_events):
        """Date filters should apply to reference events, NOT athlete's own event lookup."""
        athlete_id = sample_athletes[0]["id"]

        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = [sample_athletes[0]]

        # Athlete event query (should NOT be date-filtered)
        athlete_event_mock = self._make_chainable_mock()
        athlete_event_mock.execute.return_value.data = [
            {"metrics": {"height_cm": 47.0, "body_mass_kg": 72.0}}
        ]

        # Reference events query (should be date-filtered)
        ref_events_mock = self._make_chainable_mock()
        ref_events_mock.execute.return_value.data = sample_events

        call_count = {"events": 0}

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            call_count["events"] += 1
            if call_count["events"] == 1:
                return athlete_event_mock
            return ref_events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={
                "metric": "height_cm",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )

        assert response.status_code == 200
        # Athlete event lookup should NOT have date filters
        athlete_event_mock.gte.assert_not_called()
        athlete_event_mock.lte.assert_not_called()
        # Reference events should have date filters
        ref_events_mock.gte.assert_called_with("event_date", "2024-01-01")
        ref_events_mock.lte.assert_called_with("event_date", "2024-12-31")

    def test_metrics_with_date_range(self, mock_supabase, sample_athletes):
        """Should apply date filters to metrics endpoint."""
        athlete_id = sample_athletes[0]["id"]

        athletes_mock = self._make_chainable_mock()
        athletes_mock.execute.return_value.data = [sample_athletes[0]]

        events_mock = self._make_chainable_mock()
        events_mock.execute.return_value.data = [
            {"metrics": {"height_cm": 45.0}},
        ]

        def table_side_effect(table_name):
            if table_name == "athletes":
                return athletes_mock
            return events_mock

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/metrics",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
            },
        )

        assert response.status_code == 200
        events_mock.gte.assert_called_with("event_date", "2024-01-01")
        events_mock.lte.assert_called_with("event_date", "2024-12-31")


class TestBenchmarkSourceAccess:
    """Test access control for benchmark_source parameter."""

    def test_coach_gets_403_for_boxing_science(self, mock_supabase):
        """Coaches should get 403 when requesting boxing_science benchmarks."""
        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "benchmark_source": "boxing_science"},
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_coach_gets_403_for_shared_pool(self, mock_supabase):
        """Coaches should get 403 when requesting shared_pool benchmarks."""
        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "benchmark_source": "shared_pool"},
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    def test_admin_can_use_shared_pool(self, mock_supabase, sample_athletes, sample_events, admin_client):
        """Admin should be able to use shared_pool benchmark source."""
        mock_consents = MagicMock()
        mock_consents.data = [{"coach_id": "coach-1", "data_sharing_enabled": True}]

        mock_admin_profiles = MagicMock()
        mock_admin_profiles.data = [{"id": str(TEST_ADMIN_ID)}]

        mock_athletes = MagicMock()
        mock_athletes.data = sample_athletes

        mock_events_result = MagicMock()
        mock_events_result.data = sample_events

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "coach_consents":
                mock_table.select.return_value.execute.return_value = mock_consents
            elif table_name == "profiles":
                mock_table.select.return_value.eq.return_value.execute.return_value = mock_admin_profiles
            elif table_name == "athletes":
                mock_table.select.return_value.in_.return_value.execute.return_value = mock_athletes
            elif table_name == "performance_events":
                mock_table.select.return_value.in_.return_value.execute.return_value = mock_events_result
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = admin_client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "benchmark_source": "shared_pool"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5
        assert data["mean"] == 45.0

    def test_coach_gets_403_for_shared_pool_zscore(self, mock_supabase, sample_athletes):
        """Coaches should get 403 when requesting shared_pool Z-score."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 47.0}}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={"metric": "height_cm", "benchmark_source": "shared_pool"},
        )
        assert response.status_code == 403

    def test_coach_gets_403_for_shared_pool_zscores_bulk(self, mock_supabase, sample_athletes):
        """Coaches should get 403 when requesting shared_pool bulk Z-scores."""
        athlete_id = sample_athletes[0]["id"]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_athletes[0]
                ]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "metrics": {"height_cm": 45.0}}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscores",
            params={"metric": "height_cm", "benchmark_source": "shared_pool"},
        )
        assert response.status_code == 403
