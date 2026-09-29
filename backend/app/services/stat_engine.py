"""Statistical Engine for performance analysis.

This module provides pure mathematical functions for statistical calculations.
All calculations are performed on-the-fly (not stored in database).
"""

import math
from collections import Counter
from typing import List, Optional, Tuple


class StatEngine:
    """Statistical calculations for athlete performance analysis."""

    DECIMAL_PLACES = 2

    @classmethod
    def _round(cls, value: float) -> float:
        """Round to standard decimal places."""
        return round(value, cls.DECIMAL_PLACES)

    @classmethod
    def calculate_mean(cls, values: List[float]) -> Optional[float]:
        """
        Calculate the arithmetic mean of a list of values.

        Args:
            values: List of numeric values.

        Returns:
            Mean value rounded to 2 decimal places, or None if list is empty.
        """
        if not values:
            return None
        return cls._round(sum(values) / len(values))

    @classmethod
    def calculate_std_dev(cls, values: List[float], population: bool = True) -> Optional[float]:
        """
        Calculate the standard deviation of a list of values.

        Args:
            values: List of numeric values.
            population: If True, calculates population SD (N). If False, sample SD (N-1).

        Returns:
            Standard deviation rounded to 2 decimal places, or None if list is empty.
        """
        if not values:
            return None

        n = len(values)
        if n == 1:
            return 0.0

        mean = sum(values) / n
        squared_diffs = [(x - mean) ** 2 for x in values]

        divisor = n if population else (n - 1)
        variance = sum(squared_diffs) / divisor

        return cls._round(math.sqrt(variance))

    @classmethod
    def calculate_mode(cls, values: List[float]) -> Optional[float]:
        """
        Calculate the mode (most frequent value) of a list of values.

        If multiple modes exist, returns the smallest one.
        Values are rounded to 1 decimal place before counting for practical grouping.

        Args:
            values: List of numeric values.

        Returns:
            Mode value, or None if list is empty.
        """
        if not values:
            return None

        # Round to 1 decimal place for practical grouping
        rounded_values = [round(v, 1) for v in values]
        counts = Counter(rounded_values)

        # Find the maximum count
        max_count = max(counts.values())

        # Get all values with max count (handles multimodal case)
        modes = [val for val, count in counts.items() if count == max_count]

        # Return the smallest mode if multiple exist
        return cls._round(min(modes))

    @classmethod
    def calculate_confidence_interval_95(
        cls, values: List[float]
    ) -> Optional[Tuple[float, float]]:
        """
        Calculate the 95% confidence interval for the mean.

        Uses the formula: mean ± (1.96 * SE) where SE = SD / sqrt(n)

        Args:
            values: List of numeric values.

        Returns:
            Tuple of (lower_bound, upper_bound) rounded to 2 decimal places,
            or None if list is empty or has only one value.
        """
        if not values or len(values) < 2:
            return None

        n = len(values)
        mean = sum(values) / n
        std_dev = cls.calculate_std_dev(values, population=False)  # Use sample SD for CI

        if std_dev is None or std_dev == 0:
            # If SD is 0, CI is just the mean
            return (cls._round(mean), cls._round(mean))

        # Standard error
        se = std_dev / math.sqrt(n)

        # 95% CI using z-score of 1.96
        margin = 1.96 * se

        lower = cls._round(mean - margin)
        upper = cls._round(mean + margin)

        return (lower, upper)

    @classmethod
    def calculate_z_score(
        cls, value: float, mean: float, std_dev: float
    ) -> float:
        """
        Calculate the Z-score for a value given population parameters.

        Z = (value - mean) / std_dev

        Args:
            value: The individual value to calculate Z-score for.
            mean: Population mean.
            std_dev: Population standard deviation.

        Returns:
            Z-score rounded to 2 decimal places.
            Returns 0.0 if std_dev is 0 (to handle division by zero).
        """
        if std_dev == 0:
            return 0.0

        z = (value - mean) / std_dev
        return cls._round(z)

    @classmethod
    def get_mass_band(cls, mass_kg: float) -> str:
        """
        Get the mass band label for a given body mass.

        Bins mass into 5kg increments.

        Args:
            mass_kg: Body mass in kilograms.

        Returns:
            Mass band string, e.g., "70-74.9kg"

        Examples:
            72.5 → "70-74.9kg"
            75.0 → "75-79.9kg"
            69.9 → "65-69.9kg"
        """
        # Calculate the lower bound of the 5kg band
        lower = int(mass_kg // 5) * 5
        upper = lower + 4.9

        return f"{lower}-{upper}kg"

    @classmethod
    def calculate_median(cls, values: List[float]) -> Optional[float]:
        """
        Calculate the median of a list of values.

        Args:
            values: List of numeric values.

        Returns:
            Median value rounded to 2 decimal places, or None if list is empty.
        """
        if not values:
            return None

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2

        if n % 2 == 0:
            return cls._round((sorted_vals[mid - 1] + sorted_vals[mid]) / 2)
        return cls._round(sorted_vals[mid])

    @classmethod
    def calculate_percentile_rank(cls, value: float, values: List[float]) -> float:
        """
        Calculate the empirical percentile rank of a value within a dataset.

        Percentile = count(v <= value) / len(values) * 100

        Args:
            value: The value to rank.
            values: The reference dataset.

        Returns:
            Percentile rank rounded to 1 decimal place (0.0–100.0).
            Returns 0.0 for empty list.
        """
        if not values:
            return 0.0
        count_le = sum(1 for v in values if v <= value)
        return round(count_le / len(values) * 100, 1)

    @classmethod
    def calculate_benchmarks(
        cls, values: List[float]
    ) -> Optional[dict]:
        """
        Calculate all benchmark statistics for a dataset.

        Args:
            values: List of numeric values.

        Returns:
            Dictionary with mean, std_dev, mode, ci_lower, ci_upper, count.
            Returns None if values is empty.
        """
        if not values:
            return None

        mean = cls.calculate_mean(values)
        std_dev = cls.calculate_std_dev(values)
        mode = cls.calculate_mode(values)
        ci = cls.calculate_confidence_interval_95(values)

        return {
            "mean": mean,
            "std_dev": std_dev,
            "mode": mode,
            "ci_lower": ci[0] if ci else None,
            "ci_upper": ci[1] if ci else None,
            "count": len(values),
        }

    @classmethod
    def calculate_descriptive_stats(cls, values: List[float]) -> Optional[dict]:
        """
        Calculate full descriptive statistics including median, min, max.

        Extends calculate_benchmarks with additional measures.

        Args:
            values: List of numeric values.

        Returns:
            Dictionary with mean, std_dev, median, min, max, ci_lower, ci_upper, count.
            Returns None if values is empty.
        """
        benchmarks = cls.calculate_benchmarks(values)
        if benchmarks is None:
            return None

        benchmarks["median"] = cls.calculate_median(values)
        benchmarks["min"] = cls._round(min(values))
        benchmarks["max"] = cls._round(max(values))
        return benchmarks
