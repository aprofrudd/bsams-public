"""Tests for Statistical Engine."""

import pytest

from app.services.stat_engine import StatEngine


class TestCalculateMean:
    """Test calculate_mean method."""

    def test_basic_mean(self):
        """Should calculate correct mean for simple list."""
        values = [10.0, 20.0, 30.0]
        assert StatEngine.calculate_mean(values) == 20.0

    def test_mean_with_decimals(self):
        """Should handle decimal values."""
        values = [10.5, 20.5, 30.5]
        assert StatEngine.calculate_mean(values) == 20.5

    def test_mean_single_value(self):
        """Should return the value itself for single item list."""
        assert StatEngine.calculate_mean([42.0]) == 42.0

    def test_mean_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_mean([]) is None

    def test_mean_rounds_to_two_decimals(self):
        """Should round to 2 decimal places."""
        values = [1.0, 2.0, 3.0]  # Mean is 2.0
        assert StatEngine.calculate_mean(values) == 2.0

        values = [1.111, 2.222, 3.333]  # Mean is 2.222
        assert StatEngine.calculate_mean(values) == 2.22


class TestCalculateStdDev:
    """Test calculate_std_dev method."""

    def test_basic_std_dev(self):
        """Should calculate correct population SD."""
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        # Population SD = 2.0
        assert StatEngine.calculate_std_dev(values) == 2.0

    def test_std_dev_sample(self):
        """Should calculate correct sample SD when specified."""
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        # Sample SD = 2.14 (using N-1)
        result = StatEngine.calculate_std_dev(values, population=False)
        assert result == 2.14

    def test_std_dev_identical_values(self):
        """Should return 0 when all values are identical (SD=0 case)."""
        values = [5.0, 5.0, 5.0, 5.0]
        assert StatEngine.calculate_std_dev(values) == 0.0

    def test_std_dev_single_value(self):
        """Should return 0 for single value."""
        assert StatEngine.calculate_std_dev([42.0]) == 0.0

    def test_std_dev_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_std_dev([]) is None

    def test_std_dev_two_values(self):
        """Should handle two values correctly."""
        values = [10.0, 20.0]
        # Population SD = 5.0
        assert StatEngine.calculate_std_dev(values) == 5.0


class TestCalculateMode:
    """Test calculate_mode method."""

    def test_basic_mode(self):
        """Should return most frequent value."""
        values = [1.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0]
        assert StatEngine.calculate_mode(values) == 3.0

    def test_mode_with_tie(self):
        """Should return smallest mode when multiple modes exist."""
        values = [1.0, 1.0, 2.0, 2.0, 3.0]  # Both 1 and 2 appear twice
        assert StatEngine.calculate_mode(values) == 1.0

    def test_mode_single_value(self):
        """Should return the value for single item list."""
        assert StatEngine.calculate_mode([42.0]) == 42.0

    def test_mode_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_mode([]) is None

    def test_mode_groups_by_decimal(self):
        """Should group similar values (rounded to 1 decimal)."""
        # 45.51 and 45.54 both round to 45.5
        values = [45.51, 45.54, 46.0]
        assert StatEngine.calculate_mode(values) == 45.5


class TestCalculateConfidenceInterval:
    """Test calculate_confidence_interval_95 method."""

    def test_basic_ci(self):
        """Should calculate 95% CI correctly."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        ci = StatEngine.calculate_confidence_interval_95(values)
        assert ci is not None
        lower, upper = ci
        # Mean = 30, Sample SD ≈ 15.81, SE ≈ 7.07, margin ≈ 13.86
        assert lower < 30.0 < upper
        assert 15.0 < lower < 20.0
        assert 40.0 < upper < 45.0

    def test_ci_identical_values(self):
        """Should return mean for both bounds when SD=0."""
        values = [25.0, 25.0, 25.0, 25.0]
        ci = StatEngine.calculate_confidence_interval_95(values)
        assert ci == (25.0, 25.0)

    def test_ci_single_value(self):
        """Should return None for single value (need at least 2)."""
        assert StatEngine.calculate_confidence_interval_95([42.0]) is None

    def test_ci_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_confidence_interval_95([]) is None

    def test_ci_two_values(self):
        """Should calculate CI for two values."""
        values = [10.0, 20.0]
        ci = StatEngine.calculate_confidence_interval_95(values)
        assert ci is not None
        assert ci[0] < 15.0 < ci[1]


class TestCalculateZScore:
    """Test calculate_z_score method."""

    def test_basic_z_score(self):
        """Should calculate correct Z-score."""
        # Value at mean should have Z=0
        assert StatEngine.calculate_z_score(50.0, 50.0, 10.0) == 0.0

        # Value 1 SD above mean should have Z=1
        assert StatEngine.calculate_z_score(60.0, 50.0, 10.0) == 1.0

        # Value 1 SD below mean should have Z=-1
        assert StatEngine.calculate_z_score(40.0, 50.0, 10.0) == -1.0

    def test_z_score_two_sd(self):
        """Should handle values multiple SDs from mean."""
        # Value 2 SD above mean
        assert StatEngine.calculate_z_score(70.0, 50.0, 10.0) == 2.0

        # Value 2 SD below mean
        assert StatEngine.calculate_z_score(30.0, 50.0, 10.0) == -2.0

    def test_z_score_division_by_zero(self):
        """Should return 0 when SD is 0 (division by zero case)."""
        assert StatEngine.calculate_z_score(45.0, 50.0, 0.0) == 0.0

    def test_z_score_rounds_to_two_decimals(self):
        """Should round to 2 decimal places."""
        # Z = (45 - 50) / 3 = -1.666...
        assert StatEngine.calculate_z_score(45.0, 50.0, 3.0) == -1.67


class TestGetMassBand:
    """Test get_mass_band method."""

    def test_basic_mass_bands(self):
        """Should return correct 5kg band."""
        assert StatEngine.get_mass_band(72.5) == "70-74.9kg"
        assert StatEngine.get_mass_band(75.0) == "75-79.9kg"
        assert StatEngine.get_mass_band(69.9) == "65-69.9kg"

    def test_mass_band_boundaries(self):
        """Should handle band boundaries correctly."""
        # Lower boundary of band
        assert StatEngine.get_mass_band(70.0) == "70-74.9kg"
        assert StatEngine.get_mass_band(65.0) == "65-69.9kg"

        # Upper boundary (just under next band)
        assert StatEngine.get_mass_band(74.9) == "70-74.9kg"
        assert StatEngine.get_mass_band(69.99) == "65-69.9kg"

    def test_mass_band_light_athletes(self):
        """Should handle lighter athletes."""
        assert StatEngine.get_mass_band(52.0) == "50-54.9kg"
        assert StatEngine.get_mass_band(48.0) == "45-49.9kg"

    def test_mass_band_heavy_athletes(self):
        """Should handle heavier athletes."""
        assert StatEngine.get_mass_band(95.0) == "95-99.9kg"
        assert StatEngine.get_mass_band(105.0) == "105-109.9kg"

    def test_mass_band_edge_cases(self):
        """Should handle edge cases."""
        assert StatEngine.get_mass_band(0.0) == "0-4.9kg"
        assert StatEngine.get_mass_band(100.0) == "100-104.9kg"


class TestCalculateBenchmarks:
    """Test calculate_benchmarks method."""

    def test_basic_benchmarks(self):
        """Should return all benchmark statistics."""
        values = [40.0, 42.0, 44.0, 46.0, 48.0]
        result = StatEngine.calculate_benchmarks(values)

        assert result is not None
        assert result["mean"] == 44.0
        assert result["std_dev"] is not None
        assert result["mode"] is not None
        assert result["ci_lower"] is not None
        assert result["ci_upper"] is not None
        assert result["count"] == 5

    def test_benchmarks_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_benchmarks([]) is None

    def test_benchmarks_single_value(self):
        """Should handle single value (no CI)."""
        result = StatEngine.calculate_benchmarks([42.0])
        assert result is not None
        assert result["mean"] == 42.0
        assert result["count"] == 1
        assert result["ci_lower"] is None  # No CI for single value


class TestCalculateMedian:
    """Test calculate_median method."""

    def test_median_odd_count(self):
        """Should return middle value for odd-length list."""
        assert StatEngine.calculate_median([1.0, 3.0, 5.0]) == 3.0

    def test_median_even_count(self):
        """Should return average of two middle values for even-length list."""
        assert StatEngine.calculate_median([1.0, 2.0, 3.0, 4.0]) == 2.5

    def test_median_single_value(self):
        """Should return the value for single item list."""
        assert StatEngine.calculate_median([42.0]) == 42.0

    def test_median_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_median([]) is None

    def test_median_unsorted_input(self):
        """Should sort values before computing median."""
        assert StatEngine.calculate_median([5.0, 1.0, 3.0]) == 3.0

    def test_median_two_values(self):
        """Should return average of two values."""
        assert StatEngine.calculate_median([10.0, 20.0]) == 15.0

    def test_median_rounds_to_two_decimals(self):
        """Should round to 2 decimal places."""
        # Median of [1.0, 2.0] = 1.5 (no rounding needed)
        assert StatEngine.calculate_median([1.0, 2.0]) == 1.5
        # Median of [1.111, 2.222] = 1.6665 → 1.67
        assert StatEngine.calculate_median([1.111, 2.222]) == 1.67

    def test_median_identical_values(self):
        """Should return the value when all values are identical."""
        assert StatEngine.calculate_median([5.0, 5.0, 5.0, 5.0]) == 5.0


class TestCalculateDescriptiveStats:
    """Test calculate_descriptive_stats method."""

    def test_basic_descriptive_stats(self):
        """Should return all descriptive statistics."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = StatEngine.calculate_descriptive_stats(values)

        assert result is not None
        assert result["mean"] == 30.0
        assert result["median"] == 30.0
        assert result["min"] == 10.0
        assert result["max"] == 50.0
        assert result["count"] == 5
        assert result["std_dev"] is not None
        assert result["ci_lower"] is not None
        assert result["ci_upper"] is not None

    def test_descriptive_stats_empty_list(self):
        """Should return None for empty list."""
        assert StatEngine.calculate_descriptive_stats([]) is None

    def test_descriptive_stats_single_value(self):
        """Should handle single value (SD=0, no CI)."""
        result = StatEngine.calculate_descriptive_stats([42.0])
        assert result is not None
        assert result["mean"] == 42.0
        assert result["median"] == 42.0
        assert result["min"] == 42.0
        assert result["max"] == 42.0
        assert result["std_dev"] == 0.0
        assert result["count"] == 1

    def test_descriptive_stats_two_values(self):
        """Should handle two values."""
        result = StatEngine.calculate_descriptive_stats([10.0, 20.0])
        assert result is not None
        assert result["mean"] == 15.0
        assert result["median"] == 15.0
        assert result["min"] == 10.0
        assert result["max"] == 20.0

    def test_descriptive_stats_includes_benchmarks(self):
        """Should include mode from calculate_benchmarks."""
        values = [5.0, 5.0, 5.0, 10.0, 15.0]
        result = StatEngine.calculate_descriptive_stats(values)
        assert result is not None
        assert result["mode"] == 5.0


class TestCalculatePercentileRank:
    """Test calculate_percentile_rank method."""

    def test_basic_percentile(self):
        """Should calculate correct percentile for a value in the middle."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        # 30 is <= 3 of 5 values → 60.0%
        assert StatEngine.calculate_percentile_rank(30.0, values) == 60.0

    def test_at_max(self):
        """Should return 100.0 for the maximum value."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        assert StatEngine.calculate_percentile_rank(50.0, values) == 100.0

    def test_at_min(self):
        """Should return 20.0 for the minimum value in a 5-item list."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        # 10 is <= 1 of 5 → 20.0%
        assert StatEngine.calculate_percentile_rank(10.0, values) == 20.0

    def test_below_all(self):
        """Should return 0.0 when value is below all values."""
        values = [10.0, 20.0, 30.0]
        assert StatEngine.calculate_percentile_rank(5.0, values) == 0.0

    def test_above_all(self):
        """Should return 100.0 when value is above all values."""
        values = [10.0, 20.0, 30.0]
        assert StatEngine.calculate_percentile_rank(50.0, values) == 100.0

    def test_empty_list(self):
        """Should return 0.0 for empty list."""
        assert StatEngine.calculate_percentile_rank(10.0, []) == 0.0

    def test_duplicates(self):
        """Should handle duplicate values correctly."""
        values = [10.0, 20.0, 20.0, 30.0]
        # 20 is <= 3 of 4 → 75.0%
        assert StatEngine.calculate_percentile_rank(20.0, values) == 75.0

    def test_single_value(self):
        """Should return 100.0 when value equals the single item."""
        assert StatEngine.calculate_percentile_rank(42.0, [42.0]) == 100.0


class TestEdgeCases:
    """Test edge cases across all methods."""

    def test_negative_values(self):
        """Should handle negative values."""
        values = [-10.0, -5.0, 0.0, 5.0, 10.0]
        assert StatEngine.calculate_mean(values) == 0.0
        assert StatEngine.calculate_std_dev(values) is not None

    def test_large_values(self):
        """Should handle large values."""
        values = [1000000.0, 2000000.0, 3000000.0]
        assert StatEngine.calculate_mean(values) == 2000000.0

    def test_small_decimal_values(self):
        """Should handle small decimal values."""
        values = [0.001, 0.002, 0.003]
        mean = StatEngine.calculate_mean(values)
        assert mean == 0.0  # Rounds to 2 decimal places

    def test_mixed_precision_values(self):
        """Should handle values with mixed precision."""
        values = [1.0, 1.5, 1.55, 1.555]
        result = StatEngine.calculate_mean(values)
        assert isinstance(result, float)
