"""Tests for event metrics JSONB validation."""

import pytest
from pydantic import ValidationError

from app.schemas.performance_event import PerformanceEventCreate, PerformanceEventUpdate
from app.schemas.metric_registry import METRIC_GROUPS, ALLOWED_METRIC_KEYS, METRIC_DEFINITIONS
from app.schemas.upload import CSVColumnMapping


class TestMetricsValidation:
    """Test metrics dict validation on PerformanceEventCreate."""

    def test_valid_metrics_accepted(self):
        """Should accept valid metric keys with numeric values."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={"height_cm": 45.5, "body_mass_kg": 72.0, "test_type": "CMJ"},
        )
        assert event.metrics["height_cm"] == 45.5

    def test_unknown_key_rejected(self):
        """Should reject unknown metric keys."""
        with pytest.raises(ValidationError, match="Unknown metric key"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"height_cm": 45.5, "malicious_key": 999},
            )

    def test_non_numeric_value_rejected(self):
        """Should reject non-numeric values for numeric metrics."""
        with pytest.raises(ValidationError, match="must be a number"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"height_cm": "not_a_number"},
            )

    def test_value_below_minimum_rejected(self):
        """Should reject values below minimum range."""
        with pytest.raises(ValidationError, match="below minimum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"height_cm": -5.0},
            )

    def test_value_above_maximum_rejected(self):
        """Should reject values above maximum range."""
        with pytest.raises(ValidationError, match="above maximum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"height_cm": 999.0},
            )

    def test_test_type_string_accepted(self):
        """Should accept string value for test_type."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={"test_type": "CMJ", "height_cm": 45.0},
        )
        assert event.metrics["test_type"] == "CMJ"

    def test_test_type_numeric_rejected(self):
        """Should reject numeric value for test_type."""
        with pytest.raises(ValidationError, match="test_type must be a string"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"test_type": 123},
            )

    def test_test_type_too_long_rejected(self):
        """Should reject test_type longer than 50 characters."""
        with pytest.raises(ValidationError, match="50 characters"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"test_type": "A" * 51},
            )

    def test_empty_metrics_accepted(self):
        """Should accept empty metrics dict."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={},
        )
        assert event.metrics == {}

    def test_all_valid_keys_accepted(self):
        """Should accept all known metric keys with valid values."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={
                "test_type": "CMJ",
                "body_mass_kg": 72.0,
                "height_cm": 45.5,
                "sj_height_cm": 35.0,
                "eur_cm": 10.5,
                "rsi": 2.21,
                "flight_time_ms": 450.0,
                "contraction_time_ms": 200.0,
            },
        )
        assert len(event.metrics) == 8

    def test_eur_negative_accepted(self):
        """Should accept negative EUR values (SJ > CMJ is physically possible)."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={"eur_cm": -5.0},
        )
        assert event.metrics["eur_cm"] == -5.0

    def test_integer_values_accepted(self):
        """Should accept integer values for numeric metrics."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={"height_cm": 45, "body_mass_kg": 72},
        )
        assert event.metrics["height_cm"] == 45


class TestUpdateMetricsValidation:
    """Test metrics validation on PerformanceEventUpdate."""

    def test_update_unknown_key_rejected(self):
        """Should reject unknown metric keys on update."""
        with pytest.raises(ValidationError, match="Unknown metric key"):
            PerformanceEventUpdate(
                metrics={"bad_key": 123},
            )

    def test_update_valid_metrics_accepted(self):
        """Should accept valid metrics on update."""
        update = PerformanceEventUpdate(
            metrics={"height_cm": 46.0},
        )
        assert update.metrics["height_cm"] == 46.0

    def test_update_none_metrics_accepted(self):
        """Should accept None metrics (no update)."""
        update = PerformanceEventUpdate(metrics=None)
        assert update.metrics is None


class TestIsometricMetrics:
    """Test isometric metric validation and registry."""

    ISOMETRIC_KEYS = [
        "iso_trunk_rotation_left_kg",
        "iso_trunk_rotation_right_kg",
        "grip_strength_left_kg",
        "grip_strength_right_kg",
        "grip_rfd_left_pct",
        "grip_rfd_right_pct",
    ]

    def test_isometric_metrics_accepted(self):
        """Should accept all 6 isometric metrics with valid values."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={
                "test_type": "Isometric",
                "iso_trunk_rotation_left_kg": 85.0,
                "iso_trunk_rotation_right_kg": 90.0,
                "grip_strength_left_kg": 55.0,
                "grip_strength_right_kg": 58.0,
                "grip_rfd_left_pct": 120.0,
                "grip_rfd_right_pct": 115.0,
            },
        )
        assert event.metrics["iso_trunk_rotation_left_kg"] == 85.0
        assert event.metrics["grip_strength_right_kg"] == 58.0
        assert event.metrics["grip_rfd_left_pct"] == 120.0

    def test_isometric_below_minimum_rejected(self):
        """Should reject isometric metric below minimum (0)."""
        with pytest.raises(ValidationError, match="below minimum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"grip_strength_left_kg": -1.0},
            )

    def test_isometric_above_maximum_rejected(self):
        """Should reject isometric metric above maximum."""
        with pytest.raises(ValidationError, match="above maximum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"grip_strength_left_kg": 250.0},
            )

    def test_trunk_rotation_above_maximum_rejected(self):
        """Should reject trunk rotation above 500."""
        with pytest.raises(ValidationError, match="above maximum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"iso_trunk_rotation_left_kg": 501.0},
            )

    def test_isometric_group_exists_with_expected_entries(self):
        """Isometric group holds the 6 original keys plus the 4 combine RFD (N/s) keys."""
        assert "isometric" in METRIC_GROUPS
        assert len(METRIC_GROUPS["isometric"]) == 10

    def test_isometric_order_is_stable(self):
        """frontend testing/page.tsx defaults the Isometrics tab to ISOMETRIC_METRIC_KEYS[0].

        New isometric keys must be APPENDED, never inserted, or that default silently changes.
        """
        iso_keys = [m.key for m in METRIC_GROUPS["isometric"]]
        assert iso_keys[0] == "iso_trunk_rotation_left_kg"
        assert iso_keys[:6] == [
            "iso_trunk_rotation_left_kg",
            "iso_trunk_rotation_right_kg",
            "grip_strength_left_kg",
            "grip_strength_right_kg",
            "grip_rfd_left_pct",
            "grip_rfd_right_pct",
        ]

    def test_all_isometric_keys_in_allowed(self):
        """All isometric keys should be present in ALLOWED_METRIC_KEYS."""
        for key in self.ISOMETRIC_KEYS:
            assert key in ALLOWED_METRIC_KEYS, f"{key} not in ALLOWED_METRIC_KEYS"

    def test_csv_isometric_column_mappings(self):
        """CSV column mappings should include isometric columns."""
        mapping = CSVColumnMapping()
        expected_mappings = {
            "Isometric Trunk Rotation Left (kg)": "iso_trunk_rotation_left_kg",
            "Isometric Trunk Rotation Right (kg)": "iso_trunk_rotation_right_kg",
            "Iso Trunk Rotation L (kg)": "iso_trunk_rotation_left_kg",
            "Iso Trunk Rotation R (kg)": "iso_trunk_rotation_right_kg",
            "Grip Strength Left (kg)": "grip_strength_left_kg",
            "Grip Strength Right (kg)": "grip_strength_right_kg",
            "Grip Strength L (kg)": "grip_strength_left_kg",
            "Grip Strength R (kg)": "grip_strength_right_kg",
            "Grip RFD Left (%)": "grip_rfd_left_pct",
            "Grip RFD Right (%)": "grip_rfd_right_pct",
            "Grip RFD L (%)": "grip_rfd_left_pct",
            "Grip RFD R (%)": "grip_rfd_right_pct",
        }
        for csv_col, expected_key in expected_mappings.items():
            assert csv_col in mapping.metric_columns, f"Missing CSV column: {csv_col}"
            assert mapping.metric_columns[csv_col]["metric_key"] == expected_key
            assert mapping.metric_columns[csv_col]["test_type"] == "Isometric"


class TestCombineMetrics:
    """Metric keys added for the Boxing Science Combine (10-5 pogo, RFD in N/s)."""

    POGO_KEYS = ["pogo_flight_time_ms", "pogo_contact_time_ms", "pogo_rsi"]
    RFD_KEYS = [
        "grip_rfd_left_n_s",
        "grip_rfd_right_n_s",
        "iso_trunk_rotation_rfd_left_n_s",
        "iso_trunk_rotation_rfd_right_n_s",
    ]

    def test_pogo_metrics_accepted(self):
        """A 10-5 pogo attempt validates."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={
                "pogo_flight_time_ms": 480.0,
                "pogo_contact_time_ms": 190.0,
                "pogo_rsi": 2.53,
                "test_type": "Pogo",
            },
        )
        assert event.metrics["pogo_rsi"] == 2.53

    def test_pogo_keys_do_not_collide_with_cmj_rsi(self):
        """Pogo and CMJ RSI must be storable on the same event without overwriting."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={"rsi": 0.42, "pogo_rsi": 2.53},
        )
        assert event.metrics["rsi"] == 0.42
        assert event.metrics["pogo_rsi"] == 2.53

    def test_pogo_rsi_above_maximum_rejected(self):
        """A mistyped pogo RSI is rejected by the registry range."""
        with pytest.raises(ValidationError, match="above maximum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"pogo_rsi": 99.0},
            )

    def test_rfd_n_s_metrics_accepted(self):
        """Optional RFD in N/s validates for both grip and trunk rotation."""
        event = PerformanceEventCreate(
            athlete_id="00000000-0000-0000-0000-000000000001",
            event_date="2024-01-01",
            metrics={
                "grip_strength_left_kg": 48.2,
                "grip_rfd_left_n_s": 1450.0,
                "iso_trunk_rotation_rfd_right_n_s": 980.5,
            },
        )
        assert event.metrics["grip_rfd_left_n_s"] == 1450.0

    def test_rfd_above_maximum_rejected(self):
        with pytest.raises(ValidationError, match="above maximum"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"grip_rfd_left_n_s": 20001.0},
            )

    def test_all_combine_keys_allowed(self):
        for key in self.POGO_KEYS + self.RFD_KEYS:
            assert key in ALLOWED_METRIC_KEYS, f"{key} not in ALLOWED_METRIC_KEYS"

    def test_unknown_pogo_lookalike_still_rejected(self):
        """The allowlist is still strict — a near-miss key is not silently accepted."""
        with pytest.raises(ValidationError, match="Unknown metric key"):
            PerformanceEventCreate(
                athlete_id="00000000-0000-0000-0000-000000000001",
                event_date="2024-01-01",
                metrics={"pogo_foo": 1.0},
            )

    def test_pogo_group_is_jump(self):
        """Pogo keys live in the jump group so they appear on the existing Metrics tab."""
        jump_keys = [m.key for m in METRIC_GROUPS["jump"]]
        for key in self.POGO_KEYS:
            assert key in jump_keys

    def test_csv_combine_column_mappings(self):
        mapping = CSVColumnMapping()
        expected = {
            "10-5 Pogo Flight Time (ms)": ("Pogo", "pogo_flight_time_ms"),
            "10-5 Pogo Contact Time (ms)": ("Pogo", "pogo_contact_time_ms"),
            "10-5 Pogo RSI": ("Pogo", "pogo_rsi"),
            "Pogo RSI": ("Pogo", "pogo_rsi"),
            "Grip RFD Left (N/s)": ("Isometric", "grip_rfd_left_n_s"),
            "Grip RFD R (N/s)": ("Isometric", "grip_rfd_right_n_s"),
            "Iso Trunk Rotation RFD Left (N/s)": ("Isometric", "iso_trunk_rotation_rfd_left_n_s"),
            "Iso Trunk Rotation RFD R (N/s)": ("Isometric", "iso_trunk_rotation_rfd_right_n_s"),
        }
        for csv_col, (test_type, metric_key) in expected.items():
            assert csv_col in mapping.metric_columns, f"Missing CSV column: {csv_col}"
            assert mapping.metric_columns[csv_col]["metric_key"] == metric_key
            assert mapping.metric_columns[csv_col]["test_type"] == test_type

    def test_registry_mirrors_are_in_parity(self):
        """The frontend registry is hand-maintained; catch drift for testing-domain keys.

        `test_type` is a known, harmless omission in the mirror (it is in NON_METRIC_KEYS
        and the frontend filters it out explicitly).
        """
        import re
        from pathlib import Path

        ts_path = (
            Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "metricRegistry.ts"
        )
        if not ts_path.exists():
            pytest.skip("frontend registry not present")
        ts_keys = set(re.findall(r"\{ key: '([a-z0-9_]+)'", ts_path.read_text()))
        py_keys = {m.key for m in METRIC_DEFINITIONS} - {"test_type"}
        assert py_keys - ts_keys == set(), f"missing from frontend mirror: {py_keys - ts_keys}"
        assert ts_keys - py_keys == set(), f"extra in frontend mirror: {ts_keys - py_keys}"
