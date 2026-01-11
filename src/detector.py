"""Spike detection algorithm for Polybotz."""

import logging
from datetime import datetime

from .models import MonitoredEvent, MonitoredMarket, SpikeAlert

logger = logging.getLogger("polybotz.detector")


def detect_spike(market: MonitoredMarket, threshold: float) -> SpikeAlert | None:
    """
    Detect if a market has a price spike exceeding threshold.

    Returns SpikeAlert if spike detected, None otherwise.
    """
    # Edge case: market is closed - skip detection
    if market.is_closed:
        return None

    # Edge case: first poll - no previous price, no spike detection
    if market.previous_price is None:
        return None

    # Edge case: current price not available
    if market.current_price is None:
        return None

    # Edge case: previous_price is 0 - skip comparison to avoid division by zero
    if market.previous_price == 0:
        return None

    # Calculate percentage change
    change = market.current_price - market.previous_price
    change_percent = abs(change / market.previous_price) * 100

    # Check if threshold exceeded
    if change_percent < threshold:
        return None

    # Determine direction
    direction = "up" if change > 0 else "down"

    logger.info(
        f"Spike detected: {market.question} [{market.outcome}] "
        f"{market.previous_price:.4f} → {market.current_price:.4f} "
        f"({direction} {change_percent:.1f}%)"
    )

    return SpikeAlert(
        event_name="",  # Will be filled by detect_all_spikes
        market_question=market.question,
        outcome=market.outcome,
        price_before=market.previous_price,
        price_after=market.current_price,
        change_percent=change_percent,
        direction=direction,
        detected_at=datetime.now(),
    )


def detect_all_spikes(
    events: list[MonitoredEvent],
    threshold: float,
) -> list[SpikeAlert]:
    """Detect spikes across all monitored events and markets."""
    spikes = []

    for event in events:
        for market in event.markets:
            spike = detect_spike(market, threshold)
            if spike:
                spike.event_name = event.name
                spikes.append(spike)

    if spikes:
        logger.info(f"Total spikes detected: {len(spikes)}")

    return spikes
