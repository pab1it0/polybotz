"""Entry point and scheduler for Polybotz."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from .config import ConfigurationError, load_config
from .poller import parse_event_response, validate_slugs, poll_all_events
from .detector import detect_all_spikes
from .alerter import send_all_alerts
from .models import MonitoredEvent

import httpx

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


def handle_shutdown(signum: int, frame) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


async def run_poll_cycle(
    client: httpx.AsyncClient,
    events: dict[str, MonitoredEvent],
    config,
) -> dict[str, MonitoredEvent]:
    """Execute one poll → detect → alert cycle."""
    logger.info(f"Starting poll cycle for {len(events)} events")

    # Poll all events
    events = await poll_all_events(client, events)

    # Detect spikes
    spikes = detect_all_spikes(list(events.values()), config.spike_threshold)

    if spikes:
        logger.info(f"Detected {len(spikes)} spike(s)")
        await send_all_alerts(spikes, config)
    else:
        logger.debug("No spikes detected")

    logger.info("Poll cycle completed")
    return events


async def main_async() -> int:
    """Async main entry point."""
    global shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("Polybotz starting...")

    # Load configuration
    config_path = Path("config.yaml")
    try:
        config = load_config(config_path)
        logger.info(f"Loaded configuration from {config_path}")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

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

    # Main polling loop
    async with httpx.AsyncClient() as client:
        while not shutdown_requested:
            try:
                events = await run_poll_cycle(client, events, config)
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
