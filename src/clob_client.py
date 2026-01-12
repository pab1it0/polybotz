"""CLOB API client for Polymarket."""

import asyncio
import logging
from datetime import datetime

import httpx

logger = logging.getLogger("polybotz.clob_client")

CLOB_API_BASE = "https://clob.polymarket.com"
DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3
RETRY_DELAY = 1.0


async def fetch_price(
    client: httpx.AsyncClient,
    token_id: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> float | None:
    """
    Fetch current price for a token from CLOB API.

    Returns the price as a float, or None on error.
    """
    url = f"{CLOB_API_BASE}/price"
    params = {"token_id": token_id}

    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params, timeout=timeout)

            if response.status_code == 404:
                logger.warning(f"Token not found: {token_id}")
                return None

            if response.status_code == 429:
                delay = RETRY_DELAY * (2**attempt)
                logger.warning(f"CLOB rate limited, waiting {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue

            response.raise_for_status()
            data = response.json()
            price_str = data.get("price")
            if price_str is not None:
                return float(price_str)
            return None

        except httpx.TimeoutException:
            logger.warning(f"CLOB timeout fetching price for {token_id}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.HTTPStatusError as e:
            logger.error(f"CLOB HTTP error fetching price for {token_id}: {e.response.status_code}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.RequestError as e:
            logger.error(f"CLOB request error fetching price for {token_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except (ValueError, KeyError) as e:
            logger.error(f"CLOB parse error for price {token_id}: {e}")
            return None

    logger.error(f"Failed to fetch price for {token_id} after {max_retries} attempts")
    return None


async def fetch_midpoint(
    client: httpx.AsyncClient,
    token_id: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> float | None:
    """
    Fetch midpoint price for a token from CLOB API.

    Returns the midpoint as a float, or None on error.
    """
    url = f"{CLOB_API_BASE}/midpoint"
    params = {"token_id": token_id}

    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params, timeout=timeout)

            if response.status_code == 404:
                logger.warning(f"Token not found for midpoint: {token_id}")
                return None

            if response.status_code == 429:
                delay = RETRY_DELAY * (2**attempt)
                logger.warning(f"CLOB rate limited, waiting {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue

            response.raise_for_status()
            data = response.json()
            mid_str = data.get("mid")
            if mid_str is not None:
                return float(mid_str)
            return None

        except httpx.TimeoutException:
            logger.warning(f"CLOB timeout fetching midpoint for {token_id}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.HTTPStatusError as e:
            logger.error(f"CLOB HTTP error fetching midpoint for {token_id}: {e.response.status_code}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.RequestError as e:
            logger.error(f"CLOB request error fetching midpoint for {token_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except (ValueError, KeyError) as e:
            logger.error(f"CLOB parse error for midpoint {token_id}: {e}")
            return None

    logger.error(f"Failed to fetch midpoint for {token_id} after {max_retries} attempts")
    return None


async def fetch_book(
    client: httpx.AsyncClient,
    token_id: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> dict | None:
    """
    Fetch orderbook for a token from CLOB API.

    Returns the orderbook dict with bids/asks, or None on error.
    """
    url = f"{CLOB_API_BASE}/book"
    params = {"token_id": token_id}

    for attempt in range(max_retries):
        try:
            response = await client.get(url, params=params, timeout=timeout)

            if response.status_code == 404:
                logger.warning(f"Token not found for book: {token_id}")
                return None

            if response.status_code == 429:
                delay = RETRY_DELAY * (2**attempt)
                logger.warning(f"CLOB rate limited, waiting {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            logger.warning(f"CLOB timeout fetching book for {token_id}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.HTTPStatusError as e:
            logger.error(f"CLOB HTTP error fetching book for {token_id}: {e.response.status_code}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)
        except httpx.RequestError as e:
            logger.error(f"CLOB request error fetching book for {token_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(RETRY_DELAY)

    logger.error(f"Failed to fetch book for {token_id} after {max_retries} attempts")
    return None


def calculate_book_volume(book: dict) -> float:
    """
    Calculate total volume from an orderbook.

    Sums the size of all bids and asks.
    """
    total = 0.0
    for side in ("bids", "asks"):
        for order in book.get(side, []):
            try:
                total += float(order.get("size", 0))
            except (ValueError, TypeError):
                continue
    return total


async def poll_clob_markets(
    client: httpx.AsyncClient,
    market_ids: list[str],
) -> dict[str, tuple[float | None, float | None]]:
    """
    Poll price and volume for multiple markets.

    Returns a dict mapping market_id to (price, volume) tuples.
    """
    results = {}
    timestamp = datetime.now()

    for market_id in market_ids:
        # Fetch midpoint price
        price = await fetch_midpoint(client, market_id)

        # Fetch orderbook for volume
        book = await fetch_book(client, market_id)
        volume = calculate_book_volume(book) if book else None

        results[market_id] = (price, volume)
        logger.debug(f"CLOB poll {market_id}: price={price}, volume={volume}")

    return results
