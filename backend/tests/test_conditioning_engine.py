"""Tests for the conditioning engine."""

from unittest.mock import MagicMock

import pytest

from app.services.conditioning_engine import (
    TIER_RANGES,
    resolve_target_intensity,
    _get_reference_power,
)


@pytest.fixture
def mock_client():
    return MagicMock()


class TestResolveTargetIntensity:
    """Test tier-based intensity resolution."""

    def test_invalid_tier(self, mock_client):
        """Invalid tier returns (None, None, 'invalid_tier')."""
        result = resolve_target_intensity(mock_client, "athlete-1", "elite", "power_watts")
        assert result == (None, None, "invalid_tier")

    def test_rpe_foundation(self, mock_client):
        """RPE foundation tier returns default range."""
        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "foundation", "rpe"
        )
        assert min_val == 5.0
        assert max_val == 6.0
        assert source == "default"

    def test_rpe_intermediate(self, mock_client):
        """RPE intermediate tier returns correct range."""
        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "intermediate", "rpe"
        )
        assert min_val == 6.0
        assert max_val == 8.0
        assert source == "default"

    def test_rpe_advanced(self, mock_client):
        """RPE advanced tier returns correct range."""
        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "advanced", "rpe"
        )
        assert min_val == 8.0
        assert max_val == 10.0
        assert source == "default"

    def test_speed_foundation(self, mock_client):
        """Speed foundation tier returns default range."""
        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "foundation", "speed_kmh"
        )
        assert min_val == 8.0
        assert max_val == 12.0
        assert source == "default"

    def test_speed_intermediate(self, mock_client):
        """Speed intermediate tier returns correct range."""
        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "intermediate", "speed_kmh"
        )
        assert min_val == 12.0
        assert max_val == 16.0
        assert source == "default"

    def test_speed_advanced(self, mock_client):
        """Speed advanced tier returns correct range."""
        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "advanced", "speed_kmh"
        )
        assert min_val == 16.0
        assert max_val == 20.0
        assert source == "default"

    def test_power_from_metabolic_profile(self, mock_client):
        """Power resolution uses metabolic profile as primary source."""
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"sprint_1_avg_power_w": 500.0}
        ]

        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "foundation", "power_watts"
        )
        # foundation = 0.4-0.6, ref=500 -> 200-300
        assert min_val == 200.0
        assert max_val == 300.0
        assert source == "metabolic_profile"

    def test_power_from_air_bike_recording(self, mock_client):
        """Power resolution falls back to BLE recording."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            elif table_name == "air_bike_recordings":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"peak_power_w": 400.0}
                ]
            return mock_table

        mock_client.table.side_effect = table_side_effect

        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "intermediate", "power_watts"
        )
        # intermediate = 0.6-0.8, ref=400 -> 240-320
        assert min_val == 240.0
        assert max_val == 320.0
        assert source == "air_bike_recording"

    def test_power_from_air_bike_sprint(self, mock_client):
        """Power resolution falls back to sprint test."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            elif table_name == "air_bike_recordings":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            elif table_name == "air_bike_tests":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"id": "test-1"}
                ]
            elif table_name == "air_bike_sprints":
                mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                    {"power_7s": 600.0}
                ]
            return mock_table

        mock_client.table.side_effect = table_side_effect

        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "advanced", "power_watts"
        )
        # advanced = 0.8-1.0, ref=600 -> 480-600
        assert min_val == 480.0
        assert max_val == 600.0
        assert source == "air_bike_sprint"

    def test_power_missing_all_sources(self, mock_client):
        """Returns missing when no athlete data available."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            elif table_name == "air_bike_recordings":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            elif table_name == "air_bike_tests":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            return mock_table

        mock_client.table.side_effect = table_side_effect

        min_val, max_val, source = resolve_target_intensity(
            mock_client, "athlete-1", "foundation", "power_watts"
        )
        assert min_val is None
        assert max_val is None
        assert source == "missing"

    def test_unknown_intensity_type(self, mock_client):
        """Unknown intensity type returns unknown_type."""
        result = resolve_target_intensity(
            mock_client, "athlete-1", "foundation", "heart_rate"
        )
        assert result == (None, None, "unknown_type")


class TestTierRanges:
    """Test tier range configuration."""

    def test_foundation_range(self):
        assert TIER_RANGES["foundation"] == (0.4, 0.6)

    def test_intermediate_range(self):
        assert TIER_RANGES["intermediate"] == (0.6, 0.8)

    def test_advanced_range(self):
        assert TIER_RANGES["advanced"] == (0.8, 1.0)


class TestGetReferencePower:
    """Test the internal _get_reference_power function."""

    def test_metabolic_profile_none_value(self, mock_client):
        """Skips metabolic profile when sprint_1_avg_power_w is None."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"sprint_1_avg_power_w": None}
                ]
            elif table_name == "air_bike_recordings":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"peak_power_w": 350.0}
                ]
            return mock_table

        mock_client.table.side_effect = table_side_effect

        power, source = _get_reference_power(mock_client, "athlete-1")
        assert power == 350.0
        assert source == "air_bike_recording"

    def test_db_exception_falls_through(self, mock_client):
        """DB errors are caught and resolution continues."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB error")
            elif table_name == "air_bike_recordings":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB error")
            elif table_name == "air_bike_tests":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("DB error")
            return mock_table

        mock_client.table.side_effect = table_side_effect

        power, source = _get_reference_power(mock_client, "athlete-1")
        assert power is None
        assert source == "missing"
