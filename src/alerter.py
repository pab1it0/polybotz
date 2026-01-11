"""Telegram notification sender for Polybotz."""

import logging

import httpx

from .config import Configuration
from .models import LiquidityWarning, SpikeAlert

logger = logging.getLogger("polybotz.alerter")

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 10.0


def format_alert_message(alert: SpikeAlert) -> str:
    """Format a spike alert as a Telegram Markdown message."""
    direction_emoji = "\u2191" if alert.direction == "up" else "\u2193"
    sign = "+" if alert.direction == "up" else "-"

    return (
        f"\U0001F6A8 *Price Spike Detected*\n\n"
        f"*Event*: {_escape_markdown(alert.event_name)}\n"
        f"*Market*: {_escape_markdown(alert.market_question)}\n"
        f"*Outcome*: {alert.outcome}\n"
        f"*Price*: {alert.price_before:.4f} {direction_emoji} {alert.price_after:.4f} "
        f"({sign}{alert.change_percent:.1f}%)\n"
        f"*Time*: {alert.detected_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


def format_liquidity_warning_message(warning: LiquidityWarning) -> str:
    """Format a liquidity warning as a Telegram Markdown message."""
    direction_emoji = "\u2191" if warning.direction == "up" else "\u2193"
    sign = "+" if warning.direction == "up" else "-"

    return (
        f"\u26A0\uFE0F *Liquidity Warning*\n\n"
        f"*Event*: {_escape_markdown(warning.event_name)}\n"
        f"*Market*: {_escape_markdown(warning.market_question)}\n"
        f"*Outcome*: {warning.outcome}\n"
        f"*Price*: {warning.price_before:.4f} {direction_emoji} {warning.price_after:.4f} "
        f"({sign}{warning.change_percent:.1f}%)\n"
        f"*LVR*: {warning.lvr:.1f} ({warning.health_status})\n"
        f"*Time*: {warning.detected_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


def _escape_markdown(text: str) -> str:
    """Escape special Markdown characters."""
    special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


async def send_telegram_alert(
    bot_token: str,
    chat_id: str,
    message: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """Send a message via Telegram Bot API."""
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info("Telegram alert sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {result.get('description')}")
                    return False

            elif response.status_code == 429:
                logger.warning("Telegram rate limited, alert not sent")
                return False
            else:
                logger.error(f"Telegram HTTP error: {response.status_code}")
                return False

    except httpx.TimeoutException:
        logger.error("Telegram API timeout")
        return False
    except httpx.RequestError as e:
        logger.error(f"Telegram request error: {e}")
        return False


async def send_all_alerts(
    alerts: list[SpikeAlert],
    config: Configuration,
) -> int:
    """Send all spike alerts via Telegram, return count of successfully sent."""
    sent_count = 0

    for alert in alerts:
        message = format_alert_message(alert)
        success = await send_telegram_alert(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message,
        )

        if success:
            sent_count += 1
        else:
            logger.warning(
                f"Failed to send alert for {alert.market_question} [{alert.outcome}]"
            )

    logger.info(f"Sent {sent_count}/{len(alerts)} alerts via Telegram")
    return sent_count


async def send_all_liquidity_warnings(
    warnings: list[LiquidityWarning],
    config: Configuration,
) -> int:
    """Send all liquidity warnings via Telegram, return count of successfully sent."""
    sent_count = 0

    for warning in warnings:
        message = format_liquidity_warning_message(warning)
        success = await send_telegram_alert(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message,
        )

        if success:
            sent_count += 1
        else:
            logger.warning(
                f"Failed to send liquidity warning for {warning.market_question} [{warning.outcome}]"
            )

    if warnings:
        logger.info(f"Sent {sent_count}/{len(warnings)} liquidity warnings via Telegram")
    return sent_count
