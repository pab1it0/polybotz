"""Entry point and scheduler for Polybotz."""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

import httpx

from .alerter import (
    send_all_alerts,
    send_all_closed_event_alerts,
    send_all_liquidity_warnings,
    send_all_mad_alerts,
    send_all_zscore_alerts,
)
from .clob_client import poll_clob_markets
from .config import ConfigurationError, load_config
from .detector import (
    CooldownManager,
    detect_all_liquidity_warnings,
    detect_all_mad_alerts,
    detect_all_spikes,
    detect_all_zscore_alerts,
    detect_closed_markets,
)
from .models import MarketStatistics, MonitoredEvent
from .poller import fetch_all_events_raw, parse_event_response, poll_all_events, validate_slugs
from .statistics import update_market_statistics

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("polybotz")

# Graceful shutdown flag
shutdown_requested = False


def extract_clob_token_ids(events: dict[str, MonitoredEvent]) -> list[str]:
    """Extract all CLOB token IDs from monitored events."""
    token_ids = []
    for event in events.values():
        for market in event.markets:
            if market.clob_token_id and not market.is_closed:
                token_ids.append(market.clob_token_id)
    return token_ids


def build_token_event_mapping(events: dict[str, MonitoredEvent]) -> dict[str, tuple[str, str]]:
    """Build mapping from CLOB token ID to (event_name, outcome).

    Args:
        events: Dict mapping slug to MonitoredEvent

    Returns:
        Dict mapping token_id to (event_name, outcome) tuple
    """
    mapping = {}
    for event in events.values():
        for market in event.markets:
            if market.clob_token_id:
                mapping[market.clob_token_id] = (event.name, market.outcome)
    return mapping


def handle_shutdown(signum: int, frame) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


async def run_poll_cycle(
    client: httpx.AsyncClient,
    events: dict[str, MonitoredEvent],
    market_stats: dict[str, MarketStatistics],
    config,
    cooldown_manager: CooldownManager | None = None,
) -> dict[str, MonitoredEvent]:
    """Execute one poll → detect → alert cycle."""
    logger.info(f"Starting poll cycle for {len(events)} events")

    # Cleanup stale cooldown entries at start of each cycle
    if cooldown_manager:
        cooldown_manager.cleanup_stale()

    # Fetch raw data first (before updating state)
    raw_data = await fetch_all_events_raw(client, list(events.keys()))

    # Check if closed detector is enabled
    if "closed" in config.detectors:
        # Detect closed markets BEFORE updating state
        closed_alerts, slugs_to_remove = detect_closed_markets(events, raw_data)

        # Send alerts for closed markets
        if closed_alerts:
            logger.info(f"Detected {len(closed_alerts)} closed market(s)")
            await send_all_closed_event_alerts(closed_alerts, config)

        # Remove fully-closed events from monitoring
        for slug in slugs_to_remove:
            logger.info(f"Removing closed event from monitoring: {slug}")
            del events[slug]

    # Poll all Gamma API events (updates remaining events)
    events = await poll_all_events(client, events)

    # Check if spike detector is enabled
    if "spike" in config.detectors:
        # Detect spikes from Gamma API
        spikes = detect_all_spikes(list(events.values()), config.spike_threshold)

        if spikes:
            logger.info(f"Detected {len(spikes)} spike(s)")
            await send_all_alerts(spikes, config)

            # Check if LVR detector is enabled
            if "lvr" in config.detectors:
                # Detect liquidity warnings for spikes with high LVR
                warnings = detect_all_liquidity_warnings(
                    list(events.values()),
                    spikes,
                    config.lvr_threshold,
                )
                if warnings:
                    await send_all_liquidity_warnings(warnings, config)
        else:
            logger.debug("No spikes detected")

    # Poll CLOB markets - use config override or extract from events
    clob_token_ids = config.clob_token_ids if config.clob_token_ids else extract_clob_token_ids(events)
    if clob_token_ids:
        # Build token-to-event mapping for human-readable alerts
        token_mapping = build_token_event_mapping(events)
        await run_clob_poll_cycle(
            client, market_stats, clob_token_ids, config, cooldown_manager, token_mapping
        )

    logger.info("Poll cycle completed")
    return events


async def run_clob_poll_cycle(
    client: httpx.AsyncClient,
    market_stats: dict[str, MarketStatistics],
    clob_token_ids: list[str],
    config,
    cooldown_manager: CooldownManager | None = None,
    token_mapping: dict[str, tuple[str, str]] | None = None,
) -> None:
    """Execute CLOB polling and Z-score/MAD detection cycle."""
    logger.debug(f"Polling {len(clob_token_ids)} CLOB markets")

    # Poll CLOB markets for price and volume
    clob_data = await poll_clob_markets(client, clob_token_ids)
    timestamp = datetime.now()

    # Update statistics for each market
    for market_id, (price, volume) in clob_data.items():
        if price is None or volume is None:
            logger.debug(f"Skipping {market_id}: missing price or volume")
            continue

        # Initialize MarketStatistics if not exists
        if market_id not in market_stats:
            market_stats[market_id] = MarketStatistics(market_id=market_id)

        # Update rolling windows
        update_market_statistics(market_stats[market_id], price, volume, timestamp)

    # Check warm-up status
    valid_markets = sum(1 for s in market_stats.values() if s.volume_1h.is_valid)
    if valid_markets < len(market_stats):
        min_obs = 30
        if clob_token_ids and clob_token_ids[0] in market_stats:
            min_obs = market_stats[clob_token_ids[0]].volume_1h.min_observations
        logger.info(
            f"CLOB warm-up: {valid_markets}/{len(market_stats)} markets have sufficient data "
            f"(need {min_obs} observations)"
        )

    # Check if zscore detector is enabled
    if "zscore" in config.detectors:
        # Detect Z-score alerts (volume spikes)
        zscore_alerts = detect_all_zscore_alerts(
            market_stats,
            config.zscore_threshold,
            cooldown_manager=cooldown_manager,
            token_mapping=token_mapping,
        )
        if zscore_alerts:
            logger.info(f"Detected {len(zscore_alerts)} Z-score alert(s)")
            await send_all_zscore_alerts(zscore_alerts, config)

    # Check if mad detector is enabled
    if "mad" in config.detectors:
        # Detect MAD alerts (price anomalies)
        mad_alerts = detect_all_mad_alerts(
            market_stats,
            config.mad_multiplier,
            cooldown_manager=cooldown_manager,
            token_mapping=token_mapping,
        )
        if mad_alerts:
            logger.info(f"Detected {len(mad_alerts)} MAD alert(s)")
            await send_all_mad_alerts(mad_alerts, config)


async def main_async() -> int:
    """Async main entry point."""
    global shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("Polybotz starting...")

    # Load configuration (from file if exists, otherwise from environment variables)
    config_path = Path("config.yaml")
    try:
        config = load_config(config_path)
        if config_path.exists():
            logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.info("Loaded configuration from environment variables")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Log enabled detectors
    if config.detectors:
        logger.info(f"Enabled detectors: {', '.join(sorted(config.detectors))}")
    else:
        logger.info("No detectors enabled (monitoring only mode)")

    # Validate slugs on startup
    logger.info(f"Validating {len(config.slugs)} configured slugs...")
    valid_slugs = await validate_slugs(config)

    if not valid_slugs:
        logger.error("No valid slugs found. Exiting.")
        return 1

    logger.info(f"Monitoring {len(valid_slugs)} valid events")

    # Initialize events dict with first fetch
    events: dict[str, MonitoredEvent] = {}
    async with httpx.AsyncClient() as client:
        for slug in valid_slugs:
            from .poller import fetch_event_by_slug
            data = await fetch_event_by_slug(client, slug)
            if data:
                events[slug] = parse_event_response(data)

    logger.info(f"Initialized {len(events)} events for monitoring")

    # Log CLOB configuration - use config override or auto-extracted tokens
    if config.clob_token_ids:
        logger.info(
            f"CLOB monitoring enabled (config override): {len(config.clob_token_ids)} token(s), "
            f"Z-score threshold={config.zscore_threshold}, MAD multiplier={config.mad_multiplier}"
        )
    else:
        auto_clob_tokens = extract_clob_token_ids(events)
        if auto_clob_tokens:
            logger.info(
                f"CLOB monitoring enabled (auto-detected): {len(auto_clob_tokens)} token(s) from events, "
                f"Z-score threshold={config.zscore_threshold}, MAD multiplier={config.mad_multiplier}"
            )
        else:
            logger.info("CLOB monitoring disabled (no token IDs found in events)")

    # Initialize CLOB market statistics dict
    market_stats: dict[str, MarketStatistics] = {}

    # Initialize cooldown manager for alert suppression
    cooldown_manager = CooldownManager(
        cooldown_minutes=config.cooldown_minutes,
        escalation_threshold=config.escalation_threshold,
    )
    if config.cooldown_minutes > 0:
        logger.info(
            f"Alert cooldown enabled: {config.cooldown_minutes} minutes, "
            f"escalation threshold={config.escalation_threshold}"
        )
    else:
        logger.info("Alert cooldown disabled (cooldown_minutes=0)")

    # Main polling loop
    async with httpx.AsyncClient() as client:
        while not shutdown_requested:
            try:
                events = await run_poll_cycle(
                    client, events, market_stats, config, cooldown_manager
                )
            except Exception as e:
                logger.error(f"Error in poll cycle: {e}")

            # Wait for next poll interval
            logger.debug(f"Sleeping for {config.poll_interval} seconds...")
            for _ in range(config.poll_interval):
                if shutdown_requested:
                    break
                await asyncio.sleep(1)

    logger.info("Polybotz shutdown complete")
    return 0


def main() -> None:
    """Main entry point for Polybotz."""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
