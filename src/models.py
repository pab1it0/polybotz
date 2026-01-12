"""Data models for Polybotz."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .statistics import RollingWindow


@dataclass
class MonitoredMarket:
    """A single market within an event."""

    id: str
    question: str
    outcome: str
    current_price: float | None = None
    previous_price: float | None = None
    is_closed: bool = False
    volume_24h: float | None = None
    liquidity: float | None = None
    lvr: float | None = None
    clob_token_id: str | None = None  # CLOB token ID for this outcome


@dataclass
class MonitoredEvent:
    """An event being tracked, with its current state."""

    slug: str
    name: str
    markets: list[MonitoredMarket] = field(default_factory=list)
    last_updated: datetime | None = None


@dataclass
class SpikeAlert:
    """A detected price spike ready for notification."""

    event_name: str
    market_question: str
    outcome: str
    price_before: float
    price_after: float
    change_percent: float
    direction: str  # "up" or "down"
    detected_at: datetime


@dataclass
class LiquidityWarning:
    """Alert for LVR-triggered liquidity warnings."""

    event_name: str
    market_question: str
    outcome: str
    price_before: float
    price_after: float
    change_percent: float
    direction: str  # "up" or "down"
    lvr: float
    health_status: str  # "Healthy", "Elevated", or "High Risk"
    volume_24h: float
    liquidity: float
    detected_at: datetime


@dataclass
class MarketStatistics:
    """Rolling statistics for a single market tracked via CLOB API."""

    market_id: str
    volume_1h: "RollingWindow" = field(default=None)  # type: ignore
    volume_4h: "RollingWindow" = field(default=None)  # type: ignore
    price_1h: "RollingWindow" = field(default=None)  # type: ignore
    price_4h: "RollingWindow" = field(default=None)  # type: ignore
    last_updated: datetime | None = None

    def __post_init__(self):
        """Initialize rolling windows if not provided."""
        from .statistics import RollingWindow

        if self.volume_1h is None:
            self.volume_1h = RollingWindow(duration=timedelta(hours=1))
        if self.volume_4h is None:
            self.volume_4h = RollingWindow(duration=timedelta(hours=4))
        if self.price_1h is None:
            self.price_1h = RollingWindow(duration=timedelta(hours=1))
        if self.price_4h is None:
            self.price_4h = RollingWindow(duration=timedelta(hours=4))


@dataclass
class CooldownEntry:
    """Tracks cooldown state for a specific (market_id, metric, window) tuple."""

    key: str  # Format: "{market_id}:{metric}:{window}"
    last_alert_time: datetime
    last_zscore: float


@dataclass
class ZScoreAlert:
    """Alert triggered when Z-score exceeds threshold."""

    market_id: str
    metric: str  # "volume" or "price"
    window: str  # "1h" or "4h"
    current_value: float
    median: float
    mad: float
    zscore: float
    threshold: float
    detected_at: datetime
    event_name: str | None = None  # Human-readable event name
    outcome: str | None = None  # "Yes" or "No" outcome


@dataclass
class MADAlert:
    """Alert triggered when value exceeds MAD multiplier."""

    market_id: str
    metric: str  # "volume" or "price"
    window: str  # "1h" or "4h"
    current_value: float
    median: float
    mad: float
    multiplier: float
    threshold_multiplier: float
    detected_at: datetime
    event_name: str | None = None  # Human-readable event name
    outcome: str | None = None  # "Yes" or "No" outcome


@dataclass
class ClosedEventAlert:
    """Alert when a market transitions from open to closed."""

    event_name: str
    event_slug: str
    market_question: str
    outcome: str
    final_price: float | None
    detected_at: datetime
