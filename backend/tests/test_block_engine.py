"""Tests for training block engine (percentage resolution + plate rounding)."""

from unittest.mock import MagicMock

import pytest

from app.services.block_engine import (
    get_athlete_1rm,
    resolve_percent_1rm,
    round_to_plate,
    _resolve_from_maxes,
    _resolve_from_vbt,
)


class TestRoundToPlate:
    """Tests for round_to_plate helper."""

    def test_exact_value_unchanged(self):
        assert round_to_plate(100.0) == 100.0

    def test_rounds_down(self):
        assert round_to_plate(101.2) == 100.0

    def test_rounds_up(self):
        assert round_to_plate(103.8) == 105.0

    def test_rounds_to_nearest_2_5(self):
        assert round_to_plate(107.5) == 107.5
        assert round_to_plate(108.0) == 107.5
        assert round_to_plate(108.8) == 110.0

    def test_zero(self):
        assert round_to_plate(0.0) == 0.0

    def test_custom_increment(self):
        assert round_to_plate(107.0, increment=5.0) == 105.0
        assert round_to_plate(108.0, increment=5.0) == 110.0

    def test_zero_increment_fallback(self):
        result = round_to_plate(107.3, increment=0)
        assert result == 107.3

    def test_small_weight(self):
        assert round_to_plate(1.3) == 2.5
        assert round_to_plate(0.5) == 0.0

    def test_negative_input(self):
        # Negative weights should round to the nearest plate increment without error
        result = round_to_plate(-5.0)
        assert result == -5.0  # -5.0 / 2.5 = -2.0 exactly, no rounding needed




class TestResolveFromVbt:
    """Tests for VBT 1RM resolution."""

    def test_resolves_from_vbt_profile(self):
        """Should compute 1RM from VBT profile data."""
        mock_client = MagicMock()

        # Profile query returns a profile
        mock_profile_resp = MagicMock()
        mock_profile_resp.data = [
            {"id": "profile-1", "exercise_name": "Back Squat", "mvt_override": None}
        ]

        # Sets query returns load-velocity data
        mock_sets_resp = MagicMock()
        mock_sets_resp.data = [
            {"load_kg": 60, "mean_velocity_ms": 0.80, "peak_velocity_ms": 1.0},
            {"load_kg": 80, "mean_velocity_ms": 0.60, "peak_velocity_ms": 0.85},
            {"load_kg": 100, "mean_velocity_ms": 0.40, "peak_velocity_ms": 0.65},
        ]

        # Chain mock calls
        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.side_effect = [mock_profile_resp, mock_sets_resp]

        result = _resolve_from_vbt(mock_client, "athlete-1", "Back Squat")
        assert result is not None
        assert result > 0

    def test_returns_none_when_no_profile(self):
        """Should return None if no VBT profile exists."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = []

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = mock_resp

        result = _resolve_from_vbt(mock_client, "athlete-1", "Back Squat")
        assert result is None

    def test_returns_none_when_insufficient_sets(self):
        """Should return None if < 2 sets."""
        mock_client = MagicMock()

        mock_profile_resp = MagicMock()
        mock_profile_resp.data = [
            {"id": "profile-1", "exercise_name": "Back Squat", "mvt_override": None}
        ]

        mock_sets_resp = MagicMock()
        mock_sets_resp.data = [
            {"load_kg": 60, "mean_velocity_ms": 0.80, "peak_velocity_ms": 1.0},
        ]

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.side_effect = [mock_profile_resp, mock_sets_resp]

        result = _resolve_from_vbt(mock_client, "athlete-1", "Back Squat")
        assert result is None

    def test_resolves_from_vbt_peak_velocity_fallback(self):
        """Should resolve 1RM using peak_velocity_ms when mean_velocity_ms is None."""
        mock_client = MagicMock()

        mock_profile_resp = MagicMock()
        mock_profile_resp.data = [
            {"id": "profile-1", "exercise_name": "Back Squat", "mvt_override": None}
        ]

        # All sets have mean_velocity_ms=None but valid peak_velocity_ms
        mock_sets_resp = MagicMock()
        mock_sets_resp.data = [
            {"load_kg": 60, "mean_velocity_ms": None, "peak_velocity_ms": 1.10},
            {"load_kg": 80, "mean_velocity_ms": None, "peak_velocity_ms": 0.85},
            {"load_kg": 100, "mean_velocity_ms": None, "peak_velocity_ms": 0.65},
        ]

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.side_effect = [mock_profile_resp, mock_sets_resp]

        result = _resolve_from_vbt(mock_client, "athlete-1", "Back Squat")
        assert result is not None
        assert result > 0


class TestResolveFromMaxes:
    """Tests for manual max resolution."""

    def test_resolves_from_maxes_table(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = [{"max_kg": 140.0}]

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = mock_resp

        result = _resolve_from_maxes(mock_client, "athlete-1", "Back Squat")
        assert result == 140.0

    def test_returns_none_when_no_max(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = []

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = mock_resp

        result = _resolve_from_maxes(mock_client, "athlete-1", "Back Squat")
        assert result is None


class TestResolvePercent1rm:
    """Tests for the combined resolution function."""

    def test_resolves_via_vbt(self):
        """VBT-first resolution produces correct weight."""
        mock_client = MagicMock()

        # VBT profile found
        mock_profile_resp = MagicMock()
        mock_profile_resp.data = [
            {"id": "p1", "exercise_name": "Back Squat", "mvt_override": None}
        ]

        # 3 sets: slope ~ -0.01, intercept ~ 1.4
        mock_sets_resp = MagicMock()
        mock_sets_resp.data = [
            {"load_kg": 60, "mean_velocity_ms": 0.80, "peak_velocity_ms": None},
            {"load_kg": 80, "mean_velocity_ms": 0.60, "peak_velocity_ms": None},
            {"load_kg": 100, "mean_velocity_ms": 0.40, "peak_velocity_ms": None},
        ]

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.side_effect = [mock_profile_resp, mock_sets_resp]

        weight, source = resolve_percent_1rm(mock_client, "a1", "Back Squat", 80.0)
        assert source == "vbt"
        assert weight is not None
        assert weight > 0
        # Should be rounded to 2.5kg increment
        assert weight % 2.5 == 0

    def test_falls_back_to_manual(self):
        """When no VBT, falls back to athlete_maxes."""
        mock_client = MagicMock()

        # No VBT profile
        mock_empty = MagicMock()
        mock_empty.data = []

        # Manual max found
        mock_max = MagicMock()
        mock_max.data = [{"max_kg": 100.0}]

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.side_effect = [mock_empty, mock_max]

        weight, source = resolve_percent_1rm(mock_client, "a1", "Back Squat", 80.0)
        assert source == "manual"
        assert weight == 80.0  # 100 * 80% = 80, rounded to 2.5 = 80.0

    def test_returns_missing_when_no_data(self):
        """When neither VBT nor manual max, returns None + missing."""
        mock_client = MagicMock()

        mock_empty = MagicMock()
        mock_empty.data = []

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = mock_empty

        weight, source = resolve_percent_1rm(mock_client, "a1", "Back Squat", 80.0)
        assert source == "missing"
        assert weight is None


class TestGetAthlete1rm:
    """Tests for the 1RM lookup function."""

    def test_returns_vbt_1rm(self):
        """When VBT profile exists, returns 1RM from analysis."""
        mock_client = MagicMock()

        mock_profile_resp = MagicMock()
        mock_profile_resp.data = [
            {"id": "p1", "exercise_name": "Back Squat", "mvt_override": None}
        ]

        mock_sets_resp = MagicMock()
        mock_sets_resp.data = [
            {"load_kg": 60, "mean_velocity_ms": 0.80, "peak_velocity_ms": None},
            {"load_kg": 80, "mean_velocity_ms": 0.60, "peak_velocity_ms": None},
            {"load_kg": 100, "mean_velocity_ms": 0.40, "peak_velocity_ms": None},
        ]

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.side_effect = [mock_profile_resp, mock_sets_resp]

        max_kg, source = get_athlete_1rm(mock_client, "a1", "Back Squat")
        assert source == "vbt"
        assert max_kg is not None
        assert max_kg > 0

    def test_returns_missing_when_nothing(self):
        mock_client = MagicMock()
        mock_empty = MagicMock()
        mock_empty.data = []

        table_mock = MagicMock()
        mock_client.table.return_value = table_mock
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.ilike.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = mock_empty

        max_kg, source = get_athlete_1rm(mock_client, "a1", "Back Squat")
        assert source == "missing"
        assert max_kg is None
