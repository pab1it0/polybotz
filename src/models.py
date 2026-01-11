"""Data models for Polybotz."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MonitoredMarket:
    """A single market within an event."""

    id: str
    question: str
    outcome: str
    current_price: float | None = None
    previous_price: float | None = None
    is_closed: bool = False


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
