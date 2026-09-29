"""Tests for CPET gas analysis engine."""

import pytest

from app.services.cpet_engine import (
    compute_fat_max,
    compute_threshold_metrics,
    find_crossover_intensity,
    interpolate_at_intensity,
)


class TestComputeFatMax:
    """Tests for max fat oxidation detection."""

    def test_finds_peak(self):
        stages = [
            {"stage_number": 1, "avg_fat_gh": 15.0, "intensity_value": 80, "avg_hr_bpm": 130},
            {"stage_number": 2, "avg_fat_gh": 25.0, "intensity_value": 120, "avg_hr_bpm": 145},
            {"stage_number": 3, "avg_fat_gh": 20.0, "intensity_value": 160, "avg_hr_bpm": 160},
        ]
        result = compute_fat_max(stages)
        assert result is not None
        assert result.max_fat_oxidation_gh == 25.0
        assert result.fat_max_stage_number == 2
        assert result.fat_max_intensity == 120
        assert result.fat_max_hr == 145

    def test_no_fat_data(self):
        stages = [{"stage_number": 1, "intensity_value": 80}]
        assert compute_fat_max(stages) is None

    def test_all_zero_fat(self):
        stages = [
            {"stage_number": 1, "avg_fat_gh": 0.0, "intensity_value": 80},
            {"stage_number": 2, "avg_fat_gh": 0.0, "intensity_value": 120},
        ]
        assert compute_fat_max(stages) is None

    def test_empty_stages(self):
        assert compute_fat_max([]) is None


class TestInterpolateAtIntensity:
    """Tests for linear interpolation."""

    def test_exact_match(self):
        stages = [
            {"intensity_value": 80, "avg_vo2_ml_kg_min": 30.0},
            {"intensity_value": 120, "avg_vo2_ml_kg_min": 40.0},
        ]
        assert interpolate_at_intensity(stages, 80, "avg_vo2_ml_kg_min") == 30.0

    def test_interpolation(self):
        stages = [
            {"intensity_value": 80, "avg_vo2_ml_kg_min": 30.0},
            {"intensity_value": 120, "avg_vo2_ml_kg_min": 40.0},
        ]
        result = interpolate_at_intensity(stages, 100, "avg_vo2_ml_kg_min")
        assert result == pytest.approx(35.0)

    def test_extrapolation_below(self):
        stages = [
            {"intensity_value": 80, "avg_vo2_ml_kg_min": 30.0},
            {"intensity_value": 120, "avg_vo2_ml_kg_min": 40.0},
        ]
        result = interpolate_at_intensity(stages, 60, "avg_vo2_ml_kg_min")
        assert result is not None

    def test_no_valid_data(self):
        stages = [{"intensity_value": 80}]
        assert interpolate_at_intensity(stages, 80, "avg_vo2_ml_kg_min") is None

    def test_empty_stages(self):
        assert interpolate_at_intensity([], 80, "avg_vo2_ml_kg_min") is None


class TestComputeThresholdMetrics:
    """Tests for threshold metric interpolation."""

    def test_interpolation_at_threshold(self):
        stages = [
            {"intensity_value": 80, "avg_vo2_ml_kg_min": 30.0, "avg_hr_bpm": 130, "avg_fat_gh": 20.0},
            {"intensity_value": 120, "avg_vo2_ml_kg_min": 40.0, "avg_hr_bpm": 160, "avg_fat_gh": 15.0},
            {"intensity_value": 160, "avg_vo2_ml_kg_min": 50.0, "avg_hr_bpm": 180, "avg_fat_gh": 5.0},
        ]
        result = compute_threshold_metrics(stages, 100)
        assert result is not None
        assert result.intensity == 100
        assert result.vo2_ml_kg_min == pytest.approx(35.0)
        assert result.hr_bpm == pytest.approx(145.0)
        assert result.fat_gh == pytest.approx(17.5)

    def test_empty_stages(self):
        assert compute_threshold_metrics([], 100) is None


class TestFindCrossoverIntensity:
    """Tests for CHO/FAT crossover detection."""

    def test_crossover_found(self):
        stages = [
            {"intensity_value": 80, "avg_cho_gh": 20.0, "avg_fat_gh": 30.0},
            {"intensity_value": 120, "avg_cho_gh": 35.0, "avg_fat_gh": 25.0},
            {"intensity_value": 160, "avg_cho_gh": 50.0, "avg_fat_gh": 10.0},
        ]
        result = find_crossover_intensity(stages)
        assert result is not None
        # Crossover between 80 and 120: cho goes from 20<30 to 35>25
        # diff at 80: 20-30 = -10, diff at 120: 35-25 = 10
        # t = -(-10) / (10 - (-10)) = 10/20 = 0.5
        # intensity = 80 + 0.5 * 40 = 100
        assert result == pytest.approx(100.0)

    def test_no_crossover(self):
        stages = [
            {"intensity_value": 80, "avg_cho_gh": 10.0, "avg_fat_gh": 30.0},
            {"intensity_value": 120, "avg_cho_gh": 15.0, "avg_fat_gh": 25.0},
        ]
        assert find_crossover_intensity(stages) is None

    def test_insufficient_data(self):
        assert find_crossover_intensity([]) is None
        assert find_crossover_intensity([{"intensity_value": 80}]) is None

    def test_falls_back_to_ee_columns(self):
        stages = [
            {"intensity_value": 80, "avg_cho_ee_kcal_h": 100, "avg_fat_ee_kcal_h": 200},
            {"intensity_value": 120, "avg_cho_ee_kcal_h": 300, "avg_fat_ee_kcal_h": 150},
        ]
        result = find_crossover_intensity(stages)
        assert result is not None
