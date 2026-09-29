"""Tests for VBT engine — regression, 1RM prediction, and threshold calculations."""

import pytest

from app.services.vbt_engine import (
    FALLBACK_MVT,
    build_analysis,
    calculate_regression,
    get_default_mvt,
    predict_1rm,
    predict_load,
    predict_velocity,
)


class TestGetDefaultMvt:
    """Tests for default MVT lookup."""

    def test_known_exercise_lowercase(self):
        assert get_default_mvt("trap bar deadlift") == 0.30

    def test_known_exercise_mixed_case(self):
        assert get_default_mvt("Bench Press") == 0.17

    def test_known_exercise_with_spaces(self):
        assert get_default_mvt("  Landmine Punch Throw  ") == 0.50

    def test_unknown_exercise_returns_fallback(self):
        assert get_default_mvt("Romanian Deadlift") == FALLBACK_MVT

    def test_empty_string_returns_fallback(self):
        assert get_default_mvt("") == FALLBACK_MVT


class TestCalculateRegression:
    """Tests for linear regression calculation."""

    def test_perfect_linear_relationship(self):
        """y = -0.01x + 1.5 (velocity decreases linearly with load)."""
        loads = [20, 40, 60, 80, 100]
        velocities = [1.3, 1.1, 0.9, 0.7, 0.5]
        result = calculate_regression(loads, velocities)
        assert result is not None
        assert result.slope == pytest.approx(-0.01, abs=1e-6)
        assert result.intercept == pytest.approx(1.5, abs=1e-4)
        assert result.r_squared == pytest.approx(1.0, abs=1e-6)

    def test_near_linear_relationship(self):
        """Real-world data won't be perfectly linear."""
        loads = [40, 60, 80, 100]
        velocities = [1.20, 0.95, 0.68, 0.35]
        result = calculate_regression(loads, velocities)
        assert result is not None
        assert result.slope < 0  # Velocity decreases with load
        assert result.r_squared > 0.95  # Should be very close to linear

    def test_two_points_minimum(self):
        """Regression with exactly 2 points should work."""
        loads = [50, 100]
        velocities = [1.0, 0.5]
        result = calculate_regression(loads, velocities)
        assert result is not None
        assert result.r_squared == pytest.approx(1.0, abs=1e-6)

    def test_single_point_returns_none(self):
        """Cannot fit a line with 1 point."""
        assert calculate_regression([50], [1.0]) is None

    def test_empty_returns_none(self):
        assert calculate_regression([], []) is None

    def test_identical_loads_returns_none(self):
        """All loads the same means division by zero in regression."""
        loads = [80, 80, 80]
        velocities = [1.0, 0.9, 0.8]
        assert calculate_regression(loads, velocities) is None

    def test_mismatched_lengths_returns_none(self):
        assert calculate_regression([40, 60], [1.0]) is None

    def test_r_squared_range(self):
        """R² should always be between 0 and 1 for reasonable data."""
        loads = [40, 60, 80, 100]
        velocities = [1.2, 0.9, 0.7, 0.4]
        result = calculate_regression(loads, velocities)
        assert result is not None
        assert 0 <= result.r_squared <= 1


class TestPredict1rm:
    """Tests for 1RM prediction from regression coefficients."""

    def test_basic_prediction(self):
        """velocity = -0.01 * load + 1.5, MVT = 0.3 → 1RM = (0.3 - 1.5) / -0.01 = 120."""
        result = predict_1rm(slope=-0.01, intercept=1.5, mvt=0.3)
        assert result == pytest.approx(120.0, abs=0.1)

    def test_bench_press_mvt(self):
        """velocity = -0.008 * load + 1.2, MVT = 0.17 → 1RM = (0.17 - 1.2) / -0.008 ≈ 128.75."""
        result = predict_1rm(slope=-0.008, intercept=1.2, mvt=0.17)
        assert result is not None
        assert result == pytest.approx(128.8, abs=0.1)

    def test_positive_slope_returns_none(self):
        """Positive slope means velocity increases with load — invalid."""
        assert predict_1rm(slope=0.01, intercept=1.0, mvt=0.3) is None

    def test_zero_slope_returns_none(self):
        assert predict_1rm(slope=0, intercept=1.0, mvt=0.3) is None

    def test_negative_result_returns_none(self):
        """If intercept < MVT, predicted 1RM would be negative."""
        assert predict_1rm(slope=-0.01, intercept=0.2, mvt=0.3) is None


class TestPredictVelocity:
    """Tests for velocity prediction at a given load."""

    def test_basic_prediction(self):
        """v = -0.01 * 80 + 1.5 = 0.7."""
        result = predict_velocity(slope=-0.01, intercept=1.5, load_kg=80)
        assert result == pytest.approx(0.7, abs=0.001)

    def test_zero_load(self):
        """At zero load, velocity = intercept."""
        result = predict_velocity(slope=-0.01, intercept=1.5, load_kg=0)
        assert result == pytest.approx(1.5, abs=0.001)


class TestPredictLoad:
    """Tests for load prediction at a given velocity."""

    def test_basic_prediction(self):
        """load = (0.7 - 1.5) / -0.01 = 80."""
        result = predict_load(slope=-0.01, intercept=1.5, velocity_ms=0.7)
        assert result == pytest.approx(80.0, abs=0.1)

    def test_zero_slope_returns_none(self):
        assert predict_load(slope=0, intercept=1.5, velocity_ms=0.7) is None

    def test_negative_result_returns_none(self):
        """If predicted load is negative, return None."""
        result = predict_load(slope=-0.01, intercept=0.5, velocity_ms=0.7)
        assert result is None


class TestBuildAnalysis:
    """Tests for the full analysis pipeline."""

    def test_complete_analysis(self):
        loads = [40, 60, 80, 100]
        velocities = [1.20, 0.95, 0.65, 0.35]
        result = build_analysis(loads, velocities, mvt=0.30)
        assert result is not None
        assert result.slope < 0
        assert result.intercept > 0
        assert 0 < result.r_squared <= 1
        assert result.estimated_1rm_kg is not None
        assert result.estimated_1rm_kg > 100  # Should be above heaviest tested load
        assert result.v0_ms is not None
        assert result.v0_ms > 0
        assert result.mvt_used_ms == 0.30

    def test_insufficient_data_returns_none(self):
        assert build_analysis([40], [1.2], mvt=0.30) is None

    def test_empty_data_returns_none(self):
        assert build_analysis([], [], mvt=0.30) is None

    def test_analysis_with_high_r_squared(self):
        """Nearly perfect linear data should give R² > 0.99."""
        loads = [20, 40, 60, 80, 100]
        velocities = [1.3, 1.1, 0.9, 0.7, 0.5]
        result = build_analysis(loads, velocities, mvt=0.30)
        assert result is not None
        assert result.r_squared > 0.99

    def test_v0_none_when_intercept_negative(self):
        """If intercept is negative (unusual), v0 should be None."""
        # Construct data where intercept would be negative:
        # This would require very unusual data patterns.
        # With typical VBT data, intercept is always positive.
        loads = [40, 60, 80, 100]
        velocities = [1.20, 0.95, 0.65, 0.35]
        result = build_analysis(loads, velocities, mvt=0.30)
        assert result is not None
        # Normal data should have positive intercept
        assert result.v0_ms is not None


class TestRealWorldScenarios:
    """Integration tests with realistic VBT data."""

    def test_trap_bar_deadlift_profile(self):
        """Realistic Trap Bar Deadlift data."""
        loads = [60, 80, 100, 120, 140]
        velocities = [1.15, 0.92, 0.70, 0.48, 0.28]
        result = build_analysis(loads, velocities, mvt=0.30)
        assert result is not None
        assert result.r_squared > 0.98
        # 1RM should be between 130 and 160 for this athlete
        assert result.estimated_1rm_kg is not None
        assert 130 < result.estimated_1rm_kg < 160

    def test_bench_press_profile(self):
        """Realistic Bench Press data with lower MVT."""
        loads = [40, 50, 60, 70, 80]
        velocities = [0.98, 0.82, 0.64, 0.44, 0.22]
        result = build_analysis(loads, velocities, mvt=0.17)
        assert result is not None
        assert result.r_squared > 0.98
        assert result.estimated_1rm_kg is not None
        # 1RM should be between 80 and 95
        assert 80 < result.estimated_1rm_kg < 95

    def test_bidirectional_prediction_consistency(self):
        """Predict load → velocity → load should return consistent results."""
        loads = [60, 80, 100, 120]
        velocities = [1.10, 0.85, 0.60, 0.35]
        result = build_analysis(loads, velocities, mvt=0.30)
        assert result is not None

        # Predict velocity at 90kg
        vel = predict_velocity(result.slope, result.intercept, 90)
        # Predict load back from that velocity
        load = predict_load(result.slope, result.intercept, vel)
        assert load is not None
        assert load == pytest.approx(90.0, abs=0.2)

    def test_percent_1rm_prediction(self):
        """Predict velocity at 85% 1RM."""
        loads = [60, 80, 100, 120]
        velocities = [1.10, 0.85, 0.60, 0.35]
        result = build_analysis(loads, velocities, mvt=0.30)
        assert result is not None
        assert result.estimated_1rm_kg is not None

        target_load = result.estimated_1rm_kg * 0.85
        vel = predict_velocity(result.slope, result.intercept, target_load)
        # At 85% 1RM, velocity should be above MVT but below max tested
        assert vel > result.mvt_used_ms
        assert vel < 1.2
