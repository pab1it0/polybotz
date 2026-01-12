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

    def test_rolling_window_add_default_timestamp(self):
        """Test adding observation with default timestamp."""
        window = RollingWindow(duration=timedelta(hours=1))

        # Add without explicit timestamp - should use datetime.now()
        window.add(42.0)

        assert len(window.observations) == 1
        assert window.observations[0].value == 42.0
        # Timestamp should be close to now
        assert (datetime.now() - window.observations[0].timestamp).total_seconds() < 1


class TestUpdateMarketStatistics:
    """Tests for update_market_statistics function."""

    def test_update_market_statistics(self):
        """Test updating all rolling windows in a MarketStatistics instance."""
        from src.models import MarketStatistics

        stats = MarketStatistics(market_id="test_market")
        timestamp = datetime.now()

        update_market_statistics(stats, price=0.65, volume=1000.0, timestamp=timestamp)

        # Check all windows were updated
        assert len(stats.volume_1h.observations) == 1
        assert len(stats.volume_4h.observations) == 1
        assert len(stats.price_1h.observations) == 1
        assert len(stats.price_4h.observations) == 1

        # Check values
        assert stats.volume_1h.observations[0].value == 1000.0
        assert stats.price_1h.observations[0].value == 0.65
        assert stats.last_updated == timestamp

    def test_update_market_statistics_default_timestamp(self):
        """Test updating with default timestamp."""
        from src.models import MarketStatistics

        stats = MarketStatistics(market_id="test_market")

        update_market_statistics(stats, price=0.5, volume=500.0)

        assert stats.last_updated is not None
        assert (datetime.now() - stats.last_updated).total_seconds() < 1


class TestGetStatisticsSummary:
    """Tests for get_statistics_summary function."""

    def test_get_statistics_summary(self):
        """Test getting formatted statistics summary."""
        from src.models import MarketStatistics

        stats = MarketStatistics(market_id="test_market_123")
        timestamp = datetime.now()

        # Add some observations to make windows valid
        for i in range(35):
            update_market_statistics(stats, price=0.5 + i * 0.01, volume=1000.0 + i * 10, timestamp=timestamp)

        summary = get_statistics_summary(stats)

        assert summary["market_id"] == "test_market_123"
        assert summary["last_updated"] is not None
        assert "volume_1h" in summary
        assert "volume_4h" in summary
        assert "price_1h" in summary
        assert "price_4h" in summary

        # Check volume_1h details
        assert summary["volume_1h"]["observations"] == 35
        assert summary["volume_1h"]["is_valid"] is True
        assert summary["volume_1h"]["median"] is not None
        assert summary["volume_1h"]["mad"] is not None

    def test_get_statistics_summary_empty(self):
        """Test getting summary for empty statistics."""
        from src.models import MarketStatistics

        stats = MarketStatistics(market_id="empty_market")

        summary = get_statistics_summary(stats)

        assert summary["market_id"] == "empty_market"
        assert summary["last_updated"] is None
        assert summary["volume_1h"]["observations"] == 0
        assert summary["volume_1h"]["is_valid"] is False
        assert summary["volume_1h"]["median"] is None
        assert summary["volume_1h"]["mad"] is None
