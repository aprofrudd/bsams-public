"""Tests for lactate engine — piecewise regression breakpoint detection."""

import pytest

from app.services.lactate_engine import (
    _fit_segment,
    build_lactate_analysis,
    detect_breakpoints,
)


class TestFitSegment:
    """Tests for single-segment linear regression."""

    def test_perfect_linear(self):
        """y = 0.5x + 1.0 should give perfect fit."""
        xs = [2.0, 4.0, 6.0, 8.0]
        ys = [2.0, 3.0, 4.0, 5.0]
        slope, intercept, sse = _fit_segment(xs, ys)
        assert slope == pytest.approx(0.5, abs=1e-6)
        assert intercept == pytest.approx(1.0, abs=1e-6)
        assert sse == pytest.approx(0.0, abs=1e-6)

    def test_single_point(self):
        """Single point should return slope=0, intercept=y, sse=0."""
        slope, intercept, sse = _fit_segment([5.0], [3.0])
        assert slope == 0.0
        assert intercept == 3.0
        assert sse == 0.0

    def test_empty_list(self):
        """Empty lists should return zeros."""
        slope, intercept, sse = _fit_segment([], [])
        assert slope == 0.0
        assert intercept == 0.0
        assert sse == 0.0

    def test_identical_x_values(self):
        """All same X should return slope=0, intercept=mean(y)."""
        slope, intercept, sse = _fit_segment([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])
        assert slope == 0.0
        assert intercept == pytest.approx(2.0, abs=1e-6)

    def test_two_points(self):
        """Two points should give perfect fit."""
        slope, intercept, sse = _fit_segment([0.0, 10.0], [1.0, 6.0])
        assert slope == pytest.approx(0.5, abs=1e-6)
        assert intercept == pytest.approx(1.0, abs=1e-6)
        assert sse == pytest.approx(0.0, abs=1e-6)


class TestDetectBreakpoints:
    """Tests for piecewise regression breakpoint detection."""

    def test_insufficient_data_returns_none(self):
        """Fewer than 5 data points should return None."""
        assert detect_breakpoints([1, 2, 3], [1, 2, 3]) is None

    def test_four_points_returns_none(self):
        """Exactly 4 data points is still insufficient."""
        assert detect_breakpoints([1, 2, 3, 4], [1, 2, 3, 4]) is None

    def test_five_points_minimum_works(self):
        """5 data points should produce a result."""
        # Classic lactate curve shape: flat, gentle rise, steep rise
        intensities = [8.0, 10.0, 12.0, 14.0, 16.0]
        lactates = [1.0, 1.2, 2.0, 4.0, 8.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert len(result.segments) == 3

    def test_identical_intensities_returns_none(self):
        """All identical intensities should return None."""
        assert detect_breakpoints([10, 10, 10, 10, 10], [1, 2, 3, 4, 5]) is None

    def test_mismatched_lengths(self):
        """Mismatched array lengths should return None."""
        assert detect_breakpoints([1, 2, 3, 4, 5], [1, 2, 3]) is None

    def test_classic_lactate_curve(self):
        """Classic lactate curve with clear inflection points."""
        # 8 stages: flat baseline, moderate rise, steep rise
        intensities = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        lactates = [0.8, 0.9, 1.0, 1.5, 2.5, 4.0, 6.5, 10.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert result.lt1_x < result.lt2_x
        assert len(result.segments) == 3
        assert result.r_squared > 0.8

    def test_lt1_less_than_lt2(self):
        """LT1 should always be less than LT2."""
        intensities = [6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0]
        lactates = [0.8, 1.0, 1.3, 2.0, 3.5, 6.0, 10.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert result.lt1_x < result.lt2_x

    def test_cycling_data(self):
        """Cycling data with power (Watts) instead of speed."""
        intensities = [100, 150, 200, 250, 300, 350, 400]
        lactates = [0.9, 1.0, 1.5, 2.5, 4.5, 7.0, 11.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert result.lt1_x >= 100
        assert result.lt2_x <= 400

    def test_segments_cover_full_range(self):
        """Segments should span from min to max intensity."""
        intensities = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
        lactates = [0.8, 0.9, 1.2, 2.0, 3.5, 6.0, 9.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert result.segments[0].start_x == min(intensities)
        assert result.segments[2].end_x == max(intensities)

    def test_always_three_segments(self):
        """Result should always have exactly 3 segments."""
        intensities = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0]
        lactates = [0.8, 1.0, 1.5, 3.0, 5.0, 8.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert len(result.segments) == 3

    def test_r_squared_in_range(self):
        """R² should be between 0 and 1."""
        intensities = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
        lactates = [0.8, 0.9, 1.2, 2.0, 3.5, 6.0, 9.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert 0 <= result.r_squared <= 1

    def test_unsorted_data_works(self):
        """Input data does not need to be pre-sorted."""
        intensities = [14.0, 8.0, 12.0, 10.0, 16.0, 11.0, 13.0]
        lactates = [6.5, 0.8, 2.5, 1.0, 10.0, 1.5, 4.0]
        result = detect_breakpoints(intensities, lactates)
        assert result is not None
        assert result.lt1_x < result.lt2_x


class TestBuildLactateAnalysis:
    """Tests for the public wrapper."""

    def test_delegates_correctly(self):
        """Should return a result for valid data."""
        intensities = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]
        lactates = [0.8, 0.9, 1.2, 2.0, 3.5, 6.0, 9.0]
        result = build_lactate_analysis(intensities, lactates)
        assert result is not None
        assert result.lt1_x < result.lt2_x

    def test_insufficient_data_returns_none(self):
        """Should return None for insufficient data."""
        assert build_lactate_analysis([1, 2], [1, 2]) is None
