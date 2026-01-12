"""Gamma API polling logic for Polybotz."""

import asyncio
import json
import logging
from datetime import datetime

import httpx

from .config import Configuration
from .detector import calculate_lvr
from .models import MonitoredEvent, MonitoredMarket

logger = logging.getLogger("polybotz.poller")

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0


async def fetch_event_by_slug(
    client: httpx.AsyncClient,
    slug: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> dict | None:
    """Fetch event data from Gamma API by slug with retry logic."""
    url = f"{GAMMA_API_BASE}/events/slug/{slug}"

    for attempt in range(max_retries):
        try:
            response = await client.get(url, timeout=timeout)

            if response.status_code == 404:
                logger.warning(f"Event not found: {slug}")
                return None

            if response.status_code == 429:
                logger.warning(f"Rate limited fetching {slug}, attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {slug}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching {slug}: {e.response.status_code}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.RequestError as e:
            logger.error(f"Request error fetching {slug}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)

    logger.error(f"Failed to fetch {slug} after {max_retries} attempts")
    return None


async def validate_slugs(config: Configuration) -> list[str]:
    """Validate each slug on startup, return list of valid slugs."""
    valid_slugs = []

    async with httpx.AsyncClient() as client:
        for slug in config.slugs:
            logger.info(f"Validating slug: {slug}")
            data = await fetch_event_by_slug(client, slug)

            if data is None:
                logger.warning(f"Invalid slug, skipping: {slug}")
            else:
                logger.info(f"Valid slug: {slug} ({data.get('title', 'Unknown')})")
                valid_slugs.append(slug)

    return valid_slugs


def _parse_json_field(value) -> list:
    """Parse a field that may be a JSON string or already a list."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    elif isinstance(value, list):
        return value
    return []


def parse_event_response(data: dict) -> MonitoredEvent:
    """Convert API response to MonitoredEvent."""
    markets = []

    for market_data in data.get("markets", []):
        # Handle outcomes and prices that may be JSON strings
        outcomes = _parse_json_field(market_data.get("outcomes", []))
        prices = _parse_json_field(market_data.get("outcomePrices", []))
        clob_token_ids = _parse_json_field(market_data.get("clobTokenIds", []))

        # Parse volume and liquidity at market level
        volume_24h = None
        liquidity = None
        try:
            if market_data.get("volume24hr") is not None:
                volume_24h = float(market_data.get("volume24hr"))
        except (ValueError, TypeError):
            pass
        try:
            if market_data.get("liquidityNum") is not None:
                liquidity = float(market_data.get("liquidityNum"))
        except (ValueError, TypeError):
            pass

        # Create a market entry for each outcome
        for i, outcome in enumerate(outcomes):
            price = None
            if i < len(prices):
                try:
                    price = float(prices[i])
                except (ValueError, TypeError):
                    price = None

            # Get CLOB token ID for this outcome (if available)
            clob_token_id = None
            if i < len(clob_token_ids):
                clob_token_id = str(clob_token_ids[i]) if clob_token_ids[i] else None

            market = MonitoredMarket(
                id=market_data.get("conditionId", market_data.get("id", "")),
                question=market_data.get("question", ""),
                outcome=outcome,
                current_price=price,
                previous_price=None,
                is_closed=market_data.get("closed", False),
                volume_24h=volume_24h,
                liquidity=liquidity,
                clob_token_id=clob_token_id,
            )
            markets.append(market)

    return MonitoredEvent(
        slug=data.get("slug", ""),
        name=data.get("title", ""),
        markets=markets,
        last_updated=datetime.now(),
    )


def update_prices(event: MonitoredEvent, new_data: dict) -> MonitoredEvent:
    """Update event with new price data, storing current as previous."""
    new_event = parse_event_response(new_data)

    # Create lookup of existing markets by (id, outcome)
    existing = {(m.id, m.outcome): m for m in event.markets}

    for new_market in new_event.markets:
        key = (new_market.id, new_market.outcome)
        if key in existing:
            # Update existing: current becomes previous
            new_market.previous_price = existing[key].current_price
        # else: new market, previous_price stays None

        # Calculate and store LVR for each market
        new_market.lvr = calculate_lvr(new_market.volume_24h, new_market.liquidity)
        if new_market.lvr is not None:
            logger.debug(
                f"LVR calculated: {new_market.question} [{new_market.outcome}] "
                f"LVR={new_market.lvr:.2f} (vol={new_market.volume_24h}, liq={new_market.liquidity})"
            )

    event.markets = new_event.markets
    event.last_updated = new_event.last_updated
    event.name = new_event.name

    return event


async def poll_all_events(
    client: httpx.AsyncClient,
    events: dict[str, MonitoredEvent],
) -> dict[str, MonitoredEvent]:
    """Fetch all configured events and update their data."""
    for slug, event in events.items():
        logger.debug(f"Polling event: {slug}")
        data = await fetch_event_by_slug(client, slug)

        if data is None:
            logger.error(f"Failed to poll event: {slug}")
            continue

        events[slug] = update_prices(event, data)

    return events


async def fetch_all_events_raw(
    client: httpx.AsyncClient,
    slugs: list[str],
) -> dict[str, dict]:
    """
    Fetch raw API data for all events without updating state.

    Used for detecting state transitions (e.g., closed markets)
    before updating the main event state.

    Args:
        client: HTTP client for API requests
        slugs: List of event slugs to fetch

    Returns:
        Dict mapping slug to raw API response data
    """
    raw_data = {}

    for slug in slugs:
        logger.debug(f"Fetching raw data for: {slug}")
        data = await fetch_event_by_slug(client, slug)

        if data is not None:
            raw_data[slug] = data

    return raw_data
