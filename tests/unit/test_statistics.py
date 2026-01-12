"""Tests for statistics module."""

from datetime import datetime, timedelta

import pytest

from src.statistics import (
    Observation,
    RollingWindow,
    calculate_mad,
    calculate_zscore_mad,
    get_statistics_summary,
    update_market_statistics,
)


class TestCalculateMAD:
    """Tests for calculate_mad function."""

    def test_calculate_mad_with_known_values(self):
        """Test MAD calculation with known values."""
        # Values: [1, 2, 3, 4, 5]
        # Median: 3
        # Deviations: [2, 1, 0, 1, 2]
        # MAD: median([0, 1, 1, 2, 2]) = 1
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calculate_mad(values)
        assert result == 1.0

    def test_calculate_mad_empty_list(self):
        """Test MAD with empty list returns 0."""
        result = calculate_mad([])
        assert result == 0.0

    def test_calculate_mad_single_value(self):
        """Test MAD with single value returns 0."""
        result = calculate_mad([5.0])
        assert result == 0.0

    def test_calculate_mad_identical_values(self):
        """Test MAD with identical values returns 0."""
        result = calculate_mad([3.0, 3.0, 3.0, 3.0])
        assert result == 0.0

    def test_calculate_mad_with_outliers(self):
        """Test MAD is robust to outliers."""
        # Values with outlier: [1, 2, 3, 4, 100]
        # Median: 3
        # Deviations: [2, 1, 0, 1, 97]
        # MAD: median([0, 1, 1, 2, 97]) = 1
        values = [1.0, 2.0, 3.0, 4.0, 100.0]
        result = calculate_mad(values)
        assert result == 1.0


class TestCalculateZScoreMAD:
    """Tests for calculate_zscore_mad function."""

    def test_calculate_zscore_mad_with_known_values(self):
        """Test Z-score calculation with known values."""
        # Values: [1, 2, 3, 4, 5], median=3, MAD=1
        # Scaled MAD = 1.4826 * 1 = 1.4826
        # Z-score for current=5: (5-3)/1.4826 = 1.349
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        current = 5.0
        result = calculate_zscore_mad(current, values)
        assert result is not None
        assert abs(result - 1.349) < 0.01

    def test_calculate_zscore_mad_empty_list(self):
        """Test Z-score with empty list returns None."""
        result = calculate_zscore_mad(5.0, [])
        assert result is None

    def test_calculate_zscore_mad_zero_mad(self):
        """Test Z-score with zero MAD (identical values) returns None."""
        # All identical values → MAD = 0 → division by zero protection
        result = calculate_zscore_mad(5.0, [3.0, 3.0, 3.0])
        assert result is None

    def test_calculate_zscore_mad_negative_zscore(self):
        """Test Z-score can be negative for below-median values."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        current = 1.0  # Below median
        result = calculate_zscore_mad(current, values)
        assert result is not None
        assert result < 0


class TestRollingWindow:
    """Tests for RollingWindow class."""

    def test_rolling_window_add_and_values(self):
        """Test adding observations and retrieving values."""
        window = RollingWindow(duration=timedelta(hours=1))
        now = datetime.now()

        window.add(1.0, now)
        window.add(2.0, now)
        window.add(3.0, now)

        assert window.values == [1.0, 2.0, 3.0]

    def test_rolling_window_trim_expired(self):
        """Test that expired observations are trimmed."""
        window = RollingWindow(duration=timedelta(hours=1))
        now = datetime.now()
        old_time = now - timedelta(hours=2)

        # Add old observation (should be trimmed)
        window.add(999.0, old_time)
        # Add current observation
        window.add(1.0, now)

        assert window.values == [1.0]

    def test_rolling_window_is_valid(self):
        """Test is_valid property with min_observations."""
        window = RollingWindow(duration=timedelta(hours=1), min_observations=3)
        now = datetime.now()

        window.add(1.0, now)
        window.add(2.0, now)
        assert not window.is_valid

        window.add(3.0, now)
        assert window.is_valid

    def test_rolling_window_median(self):
        """Test median property."""
        window = RollingWindow(duration=timedelta(hours=1))
        now = datetime.now()

        window.add(1.0, now)
        window.add(2.0, now)
        window.add(3.0, now)
        window.add(4.0, now)
        window.add(5.0, now)

        assert window.median == 3.0

    def test_rolling_window_mad(self):
        """Test mad property."""
        window = RollingWindow(duration=timedelta(hours=1))
        now = datetime.now()

        window.add(1.0, now)
        window.add(2.0, now)
        window.add(3.0, now)
        window.add(4.0, now)
        window.add(5.0, now)

        assert window.mad == 1.0

    def test_rolling_window_empty_median(self):
        """Test median returns None for empty window."""
        window = RollingWindow(duration=timedelta(hours=1))
        assert window.median is None

    def test_rolling_window_empty_mad(self):
        """Test mad returns None for empty window."""
        window = RollingWindow(duration=timedelta(hours=1))
        assert window.mad is None
