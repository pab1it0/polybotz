"""Spike detection algorithm for Polybotz."""

import logging
from datetime import datetime

from .models import LiquidityWarning, MonitoredEvent, MonitoredMarket, SpikeAlert

logger = logging.getLogger("polybotz.detector")


def calculate_lvr(volume_24h: float | None, liquidity: float | None) -> float | None:
    """
    Calculate Liquidity-to-Volume Ratio (LVR).

    LVR = Volume_24h / TotalLiquidity

    Returns None if liquidity is zero, negative, or missing to avoid division errors.
    """
    if liquidity is None or liquidity <= 0:
        logger.warning(f"Zero/missing liquidity (liquidity={liquidity}), skipping LVR calculation")
        return None

    if volume_24h is None:
        logger.warning("Missing volume_24h, skipping LVR calculation")
        return None

    return volume_24h / liquidity


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


def classify_lvr_health(lvr: float) -> str:
    """
    Classify LVR health status.

    Returns:
        "Healthy" for LVR < 2.0
        "Elevated" for 2.0 <= LVR < 10.0
        "High Risk" for LVR >= 10.0
    """
    if lvr < 2.0:
        return "Healthy"
    elif lvr < 10.0:
        return "Elevated"
    else:
        return "High Risk"


def detect_liquidity_warning(
    market: MonitoredMarket,
    spike: SpikeAlert,
    lvr_threshold: float,
    event_name: str,
) -> LiquidityWarning | None:
    """
    Detect if a spike should trigger a liquidity warning.

    A liquidity warning is triggered when BOTH conditions are met:
    1. Price change exceeds spike_threshold (spike already detected)
    2. LVR exceeds lvr_threshold

    Returns LiquidityWarning if conditions met, None otherwise.
    """
    # Check if LVR is available
    if market.lvr is None:
        return None

    # Check if LVR exceeds threshold
    if market.lvr <= lvr_threshold:
        return None

    # Both conditions met - create liquidity warning
    logger.info(
        f"Liquidity warning: {market.question} [{market.outcome}] "
        f"LVR={market.lvr:.2f} (threshold={lvr_threshold})"
    )

    return LiquidityWarning(
        event_name=event_name,
        market_question=market.question,
        outcome=market.outcome,
        price_before=spike.price_before,
        price_after=spike.price_after,
        change_percent=spike.change_percent,
        direction=spike.direction,
        lvr=market.lvr,
        health_status=classify_lvr_health(market.lvr),
        volume_24h=market.volume_24h,
        liquidity=market.liquidity,
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


def detect_all_liquidity_warnings(
    events: list[MonitoredEvent],
    spikes: list[SpikeAlert],
    lvr_threshold: float,
) -> list[LiquidityWarning]:
    """
    Detect liquidity warnings for all spikes that also have high LVR.

    Args:
        events: All monitored events
        spikes: Detected price spikes (already filtered by spike_threshold)
        lvr_threshold: LVR threshold for triggering warnings

    Returns:
        List of LiquidityWarning objects for spikes that also exceed LVR threshold
    """
    warnings = []

    # Build lookup for markets by (event_name, question, outcome)
    market_lookup = {}
    for event in events:
        for market in event.markets:
            key = (event.name, market.question, market.outcome)
            market_lookup[key] = (market, event.name)

    # Check each spike for LVR condition
    for spike in spikes:
        key = (spike.event_name, spike.market_question, spike.outcome)
        if key in market_lookup:
            market, event_name = market_lookup[key]
            warning = detect_liquidity_warning(market, spike, lvr_threshold, event_name)
            if warning:
                warnings.append(warning)

    if warnings:
        logger.info(f"Total liquidity warnings: {len(warnings)}")

    return warnings
