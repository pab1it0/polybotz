"""Spike detection algorithm for Polybotz."""

import json
import logging
from datetime import datetime

from .models import (
    ClosedEventAlert,
    CooldownEntry,
    LiquidityWarning,
    MADAlert,
    MarketStatistics,
    MonitoredEvent,
    MonitoredMarket,
    SpikeAlert,
    ZScoreAlert,
)
from .statistics import calculate_zscore_mad

logger = logging.getLogger("polybotz.detector")


class CooldownManager:
    """Manages alert cooldown state for (market_id, metric, window) tuples."""

    def __init__(self, cooldown_minutes: int = 30, escalation_threshold: float = 1.0):
        """
        Initialize cooldown manager.

        Args:
            cooldown_minutes: Minutes to suppress re-alerts (0 = disabled)
            escalation_threshold: Z-score increase required to re-alert during cooldown
        """
        self.entries: dict[str, CooldownEntry] = {}
        self.cooldown_minutes = cooldown_minutes
        self.escalation_threshold = escalation_threshold

    def _make_key(self, market_id: str, metric: str, window: str) -> str:
        """Create a unique key for the (market_id, metric, window) tuple."""
        return f"{market_id}:{metric}:{window}"

    def should_alert(self, key: str, current_zscore: float) -> bool:
        """
        Determine if an alert should fire based on cooldown state.

        Args:
            key: Cooldown key (market_id:metric:window)
            current_zscore: Current z-score value

        Returns:
            True if alert should fire, False if suppressed
        """
        # Cooldown disabled - always alert
        if self.cooldown_minutes == 0:
            return True

        # No previous entry - first alert, always fire
        if key not in self.entries:
            return True

        entry = self.entries[key]
        now = datetime.now()
        elapsed = (now - entry.last_alert_time).total_seconds() / 60

        # Cooldown expired - alert
        if elapsed >= self.cooldown_minutes:
            return True

        # Check for escalation (significant increase in z-score)
        zscore_increase = current_zscore - entry.last_zscore
        if zscore_increase >= self.escalation_threshold:
            return True

        # Still in cooldown, not escalating - suppress
        return False

    def record_alert(self, key: str, zscore: float) -> None:
        """
        Record that an alert was sent for this key.

        Args:
            key: Cooldown key (market_id:metric:window)
            zscore: Z-score value at time of alert
        """
        self.entries[key] = CooldownEntry(
            key=key,
            last_alert_time=datetime.now(),
            last_zscore=zscore,
        )

    def clear_entry(self, key: str) -> None:
        """
        Clear cooldown entry when anomaly resolves.

        Args:
            key: Cooldown key to remove
        """
        if key in self.entries:
            del self.entries[key]

    def cleanup_stale(self) -> None:
        """Remove cooldown entries older than 2x cooldown_minutes."""
        if self.cooldown_minutes == 0:
            return

        now = datetime.now()
        stale_threshold = self.cooldown_minutes * 2
        stale_keys = []

        for key, entry in self.entries.items():
            elapsed = (now - entry.last_alert_time).total_seconds() / 60
            if elapsed > stale_threshold:
                stale_keys.append(key)

        for key in stale_keys:
            del self.entries[key]

        if stale_keys:
            logger.debug(f"Cleaned up {len(stale_keys)} stale cooldown entries")


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


def detect_zscore_alert(
    stats: MarketStatistics,
    threshold: float,
    metric: str = "volume",
    window: str = "1h",
) -> ZScoreAlert | None:
    """
    Detect if current value exceeds Z-score threshold for a given metric/window.

    Args:
        stats: MarketStatistics for a single market
        threshold: Z-score threshold (e.g., 3.5)
        metric: "volume" or "price"
        window: "1h" or "4h"

    Returns:
        ZScoreAlert if threshold exceeded, None otherwise.
    """
    # Get the appropriate rolling window
    window_map = {
        ("volume", "1h"): stats.volume_1h,
        ("volume", "4h"): stats.volume_4h,
        ("price", "1h"): stats.price_1h,
        ("price", "4h"): stats.price_4h,
    }

    rolling_window = window_map.get((metric, window))
    if rolling_window is None:
        logger.warning(f"Unknown metric/window combo: {metric}/{window}")
        return None

    # Check if we have enough observations
    if not rolling_window.is_valid:
        return None

    values = rolling_window.values
    if not values:
        return None

    # Current value is the most recent
    current = values[-1]

    # Calculate Z-score using all values (including current)
    zscore = calculate_zscore_mad(current, values)
    if zscore is None:
        return None

    # Check threshold
    if abs(zscore) <= threshold:
        return None

    median = rolling_window.median
    mad = rolling_window.mad

    logger.info(
        f"Z-score alert: {stats.market_id} {metric}/{window} "
        f"zscore={zscore:.2f} (threshold={threshold})"
    )

    return ZScoreAlert(
        market_id=stats.market_id,
        metric=metric,
        window=window,
        current_value=current,
        median=median,
        mad=mad,
        zscore=zscore,
        threshold=threshold,
        detected_at=datetime.now(),
    )


def detect_mad_alert(
    stats: MarketStatistics,
    multiplier: float,
    metric: str = "price",
    window: str = "1h",
) -> MADAlert | None:
    """
    Detect if current value exceeds MAD multiplier threshold.

    Alert triggers when: |current - median| > multiplier × MAD

    Args:
        stats: MarketStatistics for a single market
        multiplier: MAD multiplier threshold (e.g., 3.0)
        metric: "volume" or "price"
        window: "1h" or "4h"

    Returns:
        MADAlert if threshold exceeded, None otherwise.
    """
    # Get the appropriate rolling window
    window_map = {
        ("volume", "1h"): stats.volume_1h,
        ("volume", "4h"): stats.volume_4h,
        ("price", "1h"): stats.price_1h,
        ("price", "4h"): stats.price_4h,
    }

    rolling_window = window_map.get((metric, window))
    if rolling_window is None:
        logger.warning(f"Unknown metric/window combo: {metric}/{window}")
        return None

    # Check if we have enough observations
    if not rolling_window.is_valid:
        return None

    values = rolling_window.values
    if not values:
        return None

    # Current value is the most recent
    current = values[-1]
    median = rolling_window.median
    mad = rolling_window.mad

    if median is None or mad is None or mad == 0:
        return None

    # Calculate how many MADs away from median
    deviation = abs(current - median)
    actual_multiplier = deviation / mad

    # Check threshold
    if actual_multiplier <= multiplier:
        return None

    logger.info(
        f"MAD alert: {stats.market_id} {metric}/{window} "
        f"multiplier={actual_multiplier:.2f} (threshold={multiplier})"
    )

    return MADAlert(
        market_id=stats.market_id,
        metric=metric,
        window=window,
        current_value=current,
        median=median,
        mad=mad,
        multiplier=actual_multiplier,
        threshold_multiplier=multiplier,
        detected_at=datetime.now(),
    )


def detect_all_zscore_alerts(
    stats_dict: dict[str, MarketStatistics],
    threshold: float = 3.5,
    cooldown_manager: CooldownManager | None = None,
    token_mapping: dict[str, tuple[str, str]] | None = None,
) -> list[ZScoreAlert]:
    """
    Detect Z-score alerts across all monitored markets.

    Checks volume on 1h and 4h windows.

    Args:
        stats_dict: Dict mapping market_id to MarketStatistics
        threshold: Z-score threshold (default 3.5)
        cooldown_manager: Optional CooldownManager for suppressing repeated alerts
        token_mapping: Optional dict mapping token_id to (event_name, outcome)

    Returns:
        List of ZScoreAlert objects for all triggered alerts.
    """
    alerts = []

    for market_id, stats in stats_dict.items():
        # Check volume on both windows
        for window in ("1h", "4h"):
            alert = detect_zscore_alert(stats, threshold, metric="volume", window=window)
            if alert:
                # Apply cooldown check
                if cooldown_manager:
                    key = cooldown_manager._make_key(market_id, "volume", window)
                    if not cooldown_manager.should_alert(key, alert.zscore):
                        continue  # Suppressed by cooldown
                    cooldown_manager.record_alert(key, alert.zscore)

                # Add human-readable event info if available
                if token_mapping and market_id in token_mapping:
                    event_name, outcome = token_mapping[market_id]
                    alert.event_name = event_name
                    alert.outcome = outcome

                alerts.append(alert)

    if alerts:
        logger.info(f"Total Z-score alerts: {len(alerts)}")

    return alerts


def detect_all_mad_alerts(
    stats_dict: dict[str, MarketStatistics],
    multiplier: float = 3.0,
    cooldown_manager: CooldownManager | None = None,
    token_mapping: dict[str, tuple[str, str]] | None = None,
) -> list[MADAlert]:
    """
    Detect MAD alerts across all monitored markets.

    Checks price on 1h and 4h windows.

    Args:
        stats_dict: Dict mapping market_id to MarketStatistics
        multiplier: MAD multiplier threshold (default 3.0)
        cooldown_manager: Optional CooldownManager for suppressing repeated alerts
        token_mapping: Optional dict mapping token_id to (event_name, outcome)

    Returns:
        List of MADAlert objects for all triggered alerts.
    """
    alerts = []

    for market_id, stats in stats_dict.items():
        # Check price on both windows
        for window in ("1h", "4h"):
            alert = detect_mad_alert(stats, multiplier, metric="price", window=window)
            if alert:
                # Apply cooldown check (use multiplier as proxy for zscore)
                if cooldown_manager:
                    key = cooldown_manager._make_key(market_id, "price", window)
                    if not cooldown_manager.should_alert(key, alert.multiplier):
                        continue  # Suppressed by cooldown
                    cooldown_manager.record_alert(key, alert.multiplier)

                # Add human-readable event info if available
                if token_mapping and market_id in token_mapping:
                    event_name, outcome = token_mapping[market_id]
                    alert.event_name = event_name
                    alert.outcome = outcome

                alerts.append(alert)

    if alerts:
        logger.info(f"Total MAD alerts: {len(alerts)}")

    return alerts


def detect_closed_markets(
    events: dict[str, MonitoredEvent],
    new_data: dict[str, dict],
) -> tuple[list[ClosedEventAlert], list[str]]:
    """
    Detect markets that transitioned from open to closed.

    Compares the new API data against existing event state to find
    markets that just closed. Returns alerts for each transition
    and a list of event slugs to remove (when all markets are closed).

    Args:
        events: Dict mapping slug to existing MonitoredEvent state
        new_data: Dict mapping slug to raw API response data

    Returns:
        Tuple of (list of ClosedEventAlert, list of slugs to remove)
    """
    alerts = []
    slugs_to_remove = []

    for slug, event in events.items():
        if slug not in new_data:
            continue

        api_event = new_data[slug]
        api_markets = api_event.get("markets", [])

        # Build lookup of API market data by question
        api_market_lookup = {}
        for api_market in api_markets:
            question = api_market.get("question", "")
            api_market_lookup[question] = api_market

        all_closed = True
        for market in event.markets:
            api_market = api_market_lookup.get(market.question)
            if api_market is None:
                continue

            new_closed = api_market.get("closed", False)

            # Check for transition: was open, now closed
            if new_closed and not market.is_closed:
                # Get final price from API
                final_price = None
                outcome_prices = api_market.get("outcomePrices")
                if outcome_prices:
                    try:
                        # outcomePrices is typically a JSON string like '["0.95", "0.05"]'
                        if isinstance(outcome_prices, str):
                            prices = json.loads(outcome_prices)
                        else:
                            prices = outcome_prices
                        # Match outcome to price (Yes=0, No=1)
                        idx = 0 if market.outcome.lower() == "yes" else 1
                        if idx < len(prices):
                            final_price = float(prices[idx])
                    except (json.JSONDecodeError, ValueError, IndexError):
                        final_price = market.current_price

                alert = ClosedEventAlert(
                    event_name=event.name,
                    event_slug=slug,
                    market_question=market.question,
                    outcome=market.outcome,
                    final_price=final_price,
                    detected_at=datetime.now(),
                )
                alerts.append(alert)
                logger.info(
                    f"Market closed: {market.question} [{market.outcome}] "
                    f"final_price={final_price}"
                )

            # Track if any market is still open
            if not new_closed:
                all_closed = False

        # If all markets are closed, mark event for removal
        if all_closed and event.markets:
            slugs_to_remove.append(slug)
            logger.info(f"All markets closed for event: {event.name}")

    if alerts:
        logger.info(f"Total closed market alerts: {len(alerts)}")

    return alerts, slugs_to_remove
