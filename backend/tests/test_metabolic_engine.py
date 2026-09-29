"""Tests for metabolic profiling engine."""

import pytest

from app.services.metabolic_engine import (
    BETA,
    ETA,
    TAU,
    MetabolicResult,
    calculate_metabolic_profile,
    generate_insights,
    sum_watts,
)


class TestSumWatts:
    """Tests for sum_watts power integration."""

    def test_basic_integration(self):
        """10 samples at 100W ~1s apart should produce ~1000J."""
        samples = [
            {"elapsed_ms": i * 1000, "watts": 100}
            for i in range(10)
        ]
        result = sum_watts(samples, 0, 10)
        assert abs(result - 1000.0) < 50  # Allow small tolerance

    def test_with_trim_offset(self):
        """Trim should exclude samples before the trim window."""
        samples = [
            {"elapsed_ms": i * 1000, "watts": 100}
            for i in range(10)
        ]
        # Trim 2s means start at 2000ms, so only samples 2-9 included
        result = sum_watts(samples, 0, 10, trim_sec=2)
        assert abs(result - 800.0) < 50

    def test_empty_samples(self):
        """Empty samples should return 0."""
        assert sum_watts([], 0, 10) == 0.0

    def test_dt_clamping(self):
        """Jittery timestamps should be clamped to [0.1, 3.0]."""
        # Two samples very close together (10ms apart = 0.01s, clamped to 0.1)
        samples = [
            {"elapsed_ms": 0, "watts": 100},
            {"elapsed_ms": 10, "watts": 100},  # 0.01s gap, clamped to 0.1
        ]
        result = sum_watts(samples, 0, 10)
        # First sample dt = interval to next = 0.01s -> clamped to 0.1
        # Second sample dt = 0.01s -> clamped to 0.1
        assert abs(result - 20.0) < 1

    def test_sprint_2_window(self):
        """Only samples in the 10-20s window should be included for sprint 2."""
        samples = [
            {"elapsed_ms": 5000, "watts": 200},   # Before window
            {"elapsed_ms": 11000, "watts": 100},   # In window
            {"elapsed_ms": 12000, "watts": 100},   # In window
            {"elapsed_ms": 25000, "watts": 200},   # After window
        ]
        result = sum_watts(samples, 10, 20)
        # Only 2 samples, 1s apart, 100W each
        assert abs(result - 200.0) < 50


class TestCalculateMetabolicProfile:
    """Tests for calculate_metabolic_profile."""

    def test_full_calculation(self):
        """Full calculation with known inputs should produce expected results."""
        result = calculate_metabolic_profile(
            body_mass_kg=80,
            resting_lactate=1.0,
            la_peaks=[5.0, 8.0, 10.0],
            mech_work_j=[3000, 2500, 2000],
        )
        assert isinstance(result, MetabolicResult)
        assert len(result.mech_work) == 3
        assert len(result.alactic) == 3
        assert len(result.glycolytic) == 3
        assert result.alactic_capacity is not None
        assert result.max_glycolytic_power is not None

    def test_manual_mode_mech_work(self):
        """Manual mode: avg_power * 10 = mech_work should be passed in correctly."""
        avg_power = 250
        mech_work = [avg_power * 10, avg_power * 10, avg_power * 10]
        result = calculate_metabolic_profile(
            body_mass_kg=75,
            resting_lactate=1.0,
            la_peaks=[4.0, 7.0, 9.0],
            mech_work_j=mech_work,
        )
        assert result.mech_work == [2500, 2500, 2500]

    def test_baseline_correction_base2(self):
        """base2 = la_peaks[0] * 0.5^(3/TAU) should be ~0.871 factor."""
        factor = 0.5 ** (3 / TAU)
        assert abs(factor - 0.871) < 0.001

    def test_baseline_correction_base3(self):
        """base3 = la_peaks[1] * 0.5^(12/TAU) should be ~0.574 factor."""
        factor = 0.5 ** (12 / TAU)
        assert abs(factor - 0.574) < 0.001

    def test_negative_delta_lactate_warning(self):
        """Negative delta lactate should generate a warning."""
        result = calculate_metabolic_profile(
            body_mass_kg=80,
            resting_lactate=10.0,  # Higher than la_peak_1
            la_peaks=[5.0, 8.0, 10.0],
            mech_work_j=[3000, 2500, 2000],
        )
        assert any("Negative delta lactate" in w for w in result.warnings)

    def test_alactic_capacity_formula(self):
        """alactic_capacity = mech_work[0] - dLa1 * mass * BETA * ETA."""
        mass = 80
        resting = 1.0
        la_peak_1 = 5.0
        dLa1 = la_peak_1 - resting
        mech_1 = 3000
        expected = mech_1 - dLa1 * mass * BETA * ETA

        result = calculate_metabolic_profile(
            body_mass_kg=mass,
            resting_lactate=resting,
            la_peaks=[la_peak_1, 8.0, 10.0],
            mech_work_j=[mech_1, 2500, 2000],
        )
        assert abs(result.alactic_capacity - expected) < 0.01

    def test_max_glycolytic_power_formula(self):
        """max_glycolytic_power = (dLa2 * mass * BETA * ETA) / 10."""
        mass = 80
        la_peak_1 = 5.0
        la_peak_2 = 8.0
        base2 = la_peak_1 * (0.5 ** (3 / TAU))
        dLa2 = la_peak_2 - base2
        expected = (dLa2 * mass * BETA * ETA) / 10

        result = calculate_metabolic_profile(
            body_mass_kg=mass,
            resting_lactate=1.0,
            la_peaks=[la_peak_1, la_peak_2, 10.0],
            mech_work_j=[3000, 2500, 2000],
        )
        assert abs(result.max_glycolytic_power - expected) < 0.01

    def test_anaerobic_cost_formula(self):
        """anaerobic_cost = (dLa2 * mass * BETA * ETA) / mech_work[1]."""
        mass = 80
        la_peak_1 = 5.0
        la_peak_2 = 8.0
        mech_2 = 2500
        base2 = la_peak_1 * (0.5 ** (3 / TAU))
        dLa2 = la_peak_2 - base2
        expected = (dLa2 * mass * BETA * ETA) / mech_2

        result = calculate_metabolic_profile(
            body_mass_kg=mass,
            resting_lactate=1.0,
            la_peaks=[la_peak_1, la_peak_2, 10.0],
            mech_work_j=[3000, mech_2, 2000],
        )
        assert abs(result.anaerobic_cost - expected) < 0.0001

    def test_fatigue_slope_formula(self):
        """fatigue_slope = (dLa3 * mass * BETA * ETA) / 10."""
        mass = 80
        la_peak_2 = 8.0
        la_peak_3 = 10.0
        base3 = la_peak_2 * (0.5 ** (12 / TAU))
        dLa3 = la_peak_3 - base3
        expected = (dLa3 * mass * BETA * ETA) / 10

        result = calculate_metabolic_profile(
            body_mass_kg=mass,
            resting_lactate=1.0,
            la_peaks=[5.0, la_peak_2, la_peak_3],
            mech_work_j=[3000, 2500, 2000],
        )
        assert abs(result.fatigue_slope - expected) < 0.01

    def test_energy_breakdown_unclamped(self):
        """alac = mech - glyco (unclamped, can be negative)."""
        result = calculate_metabolic_profile(
            body_mass_kg=80,
            resting_lactate=1.0,
            la_peaks=[5.0, 8.0, 10.0],
            mech_work_j=[3000, 2500, 2000],
        )
        for i in range(3):
            assert abs(result.alactic[i] - (result.mech_work[i] - result.glycolytic[i])) < 0.01


class TestGenerateInsights:
    """Tests for generate_insights."""

    def test_all_six_categories(self):
        """Should generate 6 insight cards for valid input."""
        result = calculate_metabolic_profile(
            body_mass_kg=80,
            resting_lactate=1.0,
            la_peaks=[5.0, 8.0, 10.0],
            mech_work_j=[3000, 2500, 2000],
        )
        insights = generate_insights(result, 80)
        categories = [i["category"] for i in insights]
        assert "alactic_capacity" in categories
        assert "glycolytic_power" in categories
        assert "anaerobic_cost" in categories
        assert "fatigue_resistance" in categories
        assert "energy_balance" in categories
        assert "work_trend" in categories
        assert len(insights) == 6
