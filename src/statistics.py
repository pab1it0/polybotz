"""Statistical calculations for Z-Score/MAD hybrid detection."""

import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Observation:
    """A single data point captured from the CLOB API."""

    timestamp: datetime
    value: float


@dataclass
class RollingWindow:
    """A time-based sliding window of observations for statistical calculations."""

    duration: timedelta
    min_observations: int = 30
    observations: deque = field(default_factory=deque)

    def add(self, value: float, timestamp: datetime | None = None) -> None:
        """Add an observation and trim expired ones."""
        if timestamp is None:
            timestamp = datetime.now()
        self.observations.append(Observation(timestamp=timestamp, value=value))
        self._trim()

    def _trim(self) -> None:
        """Remove observations outside the time window."""
        cutoff = datetime.now() - self.duration
        while self.observations and self.observations[0].timestamp < cutoff:
            self.observations.popleft()

    @property
    def values(self) -> list[float]:
        """Return current observation values after trimming."""
        self._trim()
        return [obs.value for obs in self.observations]

    @property
    def median(self) -> float | None:
        """Return median of current values, or None if insufficient data."""
        vals = self.values
        if len(vals) < 1:
            return None
        return statistics.median(vals)

    @property
    def mad(self) -> float | None:
        """Return Median Absolute Deviation of current values."""
        vals = self.values
        if len(vals) < 1:
            return None
        return calculate_mad(vals)

    @property
    def is_valid(self) -> bool:
        """Return True if we have enough observations for valid statistics."""
        return len(self.observations) >= self.min_observations


def calculate_mad(values: list[float]) -> float:
    """
    Calculate Median Absolute Deviation (MAD).

    MAD = median(|X_i - median(X)|)
    """
    if not values:
        return 0.0
    median_val = statistics.median(values)
    deviations = [abs(x - median_val) for x in values]
    return statistics.median(deviations)


def calculate_zscore_mad(current: float, values: list[float]) -> float | None:
    """
    Calculate Z-score using MAD-based robust estimation.

    Z = (current - median) / (1.4826 × MAD)

    The constant 1.4826 makes MAD consistent with standard deviation
    for normally distributed data.

    Returns None if MAD is zero (all values are identical) to avoid division by zero.
    """
    if not values:
        return None

    median_val = statistics.median(values)
    mad = calculate_mad(values)

    # Avoid division by zero
    if mad == 0:
        return None

    scaled_mad = 1.4826 * mad
    return (current - median_val) / scaled_mad


def update_market_statistics(
    stats: "MarketStatistics",
    price: float,
    volume: float,
    timestamp: datetime | None = None,
) -> None:
    """Update all rolling windows in a MarketStatistics instance."""
    if timestamp is None:
        timestamp = datetime.now()

    stats.volume_1h.add(volume, timestamp)
    stats.volume_4h.add(volume, timestamp)
    stats.price_1h.add(price, timestamp)
    stats.price_4h.add(price, timestamp)
    stats.last_updated = timestamp


def get_statistics_summary(stats: "MarketStatistics") -> dict:
    """
    Return a formatted dictionary with current statistics for a market.

    Useful for display and debugging.
    """
    return {
        "market_id": stats.market_id,
        "last_updated": stats.last_updated.isoformat() if stats.last_updated else None,
        "volume_1h": {
            "observations": len(stats.volume_1h.observations),
            "is_valid": stats.volume_1h.is_valid,
            "median": stats.volume_1h.median,
            "mad": stats.volume_1h.mad,
        },
        "volume_4h": {
            "observations": len(stats.volume_4h.observations),
            "is_valid": stats.volume_4h.is_valid,
            "median": stats.volume_4h.median,
            "mad": stats.volume_4h.mad,
        },
        "price_1h": {
            "observations": len(stats.price_1h.observations),
            "is_valid": stats.price_1h.is_valid,
            "median": stats.price_1h.median,
            "mad": stats.price_1h.mad,
        },
        "price_4h": {
            "observations": len(stats.price_4h.observations),
            "is_valid": stats.price_4h.is_valid,
            "median": stats.price_4h.median,
            "mad": stats.price_4h.mad,
        },
    }


# Import MarketStatistics for type hints (avoid circular import at runtime)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import MarketStatistics
