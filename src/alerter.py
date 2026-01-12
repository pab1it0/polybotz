"""Telegram notification sender for Polybotz."""

import logging

import httpx

from .config import Configuration
from .models import ClosedEventAlert, LiquidityWarning, MADAlert, SpikeAlert, ZScoreAlert

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


def format_zscore_alert(alert: ZScoreAlert) -> str:
    """Format a Z-score alert as a Telegram Markdown message."""
    direction = "spike" if alert.zscore > 0 else "drop"

    return (
        f"\U0001F4CA *Z-Score Alert*\n\n"
        f"*Market*: {_escape_markdown(alert.market_id)}\n"
        f"*Metric*: {alert.metric} ({alert.window})\n"
        f"*Current*: {alert.current_value:.4f}\n"
        f"*Median*: {alert.median:.4f}\n"
        f"*MAD*: {alert.mad:.4f}\n"
        f"*Z-Score*: {alert.zscore:+.2f} ({direction})\n"
        f"*Threshold*: \u00b1{alert.threshold:.1f}\n"
        f"*Time*: {alert.detected_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


def format_mad_alert(alert: MADAlert) -> str:
    """Format a MAD alert as a Telegram Markdown message."""
    direction = "above" if alert.current_value > alert.median else "below"

    return (
        f"\U0001F4C8 *MAD Alert*\n\n"
        f"*Market*: {_escape_markdown(alert.market_id)}\n"
        f"*Metric*: {alert.metric} ({alert.window})\n"
        f"*Current*: {alert.current_value:.4f}\n"
        f"*Median*: {alert.median:.4f}\n"
        f"*MAD*: {alert.mad:.4f}\n"
        f"*Deviation*: {alert.multiplier:.1f}x MAD ({direction} median)\n"
        f"*Threshold*: {alert.threshold_multiplier:.1f}x MAD\n"
        f"*Time*: {alert.detected_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )


def format_closed_event_alert(alert: ClosedEventAlert) -> str:
    """Format a closed event alert as a Telegram Markdown message."""
    price_str = f"{alert.final_price:.4f}" if alert.final_price is not None else "N/A"

    return (
        f"\u2705 *Market Closed*\n\n"
        f"*Event*: {_escape_markdown(alert.event_name)}\n"
        f"*Market*: {_escape_markdown(alert.market_question)}\n"
        f"*Outcome*: {alert.outcome}\n"
        f"*Final Price*: {price_str}\n"
        f"*Time*: {alert.detected_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
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


async def send_all_zscore_alerts(
    alerts: list[ZScoreAlert],
    config: Configuration,
) -> int:
    """Send all Z-score alerts via Telegram, return count of successfully sent."""
    sent_count = 0

    for alert in alerts:
        message = format_zscore_alert(alert)
        success = await send_telegram_alert(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message,
        )

        if success:
            sent_count += 1
        else:
            logger.warning(
                f"Failed to send Z-score alert for {alert.market_id} [{alert.metric}/{alert.window}]"
            )

    if alerts:
        logger.info(f"Sent {sent_count}/{len(alerts)} Z-score alerts via Telegram")
    return sent_count


async def send_all_mad_alerts(
    alerts: list[MADAlert],
    config: Configuration,
) -> int:
    """Send all MAD alerts via Telegram, return count of successfully sent."""
    sent_count = 0

    for alert in alerts:
        message = format_mad_alert(alert)
        success = await send_telegram_alert(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message,
        )

        if success:
            sent_count += 1
        else:
            logger.warning(
                f"Failed to send MAD alert for {alert.market_id} [{alert.metric}/{alert.window}]"
            )

    if alerts:
        logger.info(f"Sent {sent_count}/{len(alerts)} MAD alerts via Telegram")
    return sent_count


async def send_all_closed_event_alerts(
    alerts: list[ClosedEventAlert],
    config: Configuration,
) -> int:
    """Send all closed event alerts via Telegram, return count of successfully sent."""
    sent_count = 0

    for alert in alerts:
        message = format_closed_event_alert(alert)
        success = await send_telegram_alert(
            config.telegram_bot_token,
            config.telegram_chat_id,
            message,
        )

        if success:
            sent_count += 1
        else:
            logger.warning(
                f"Failed to send closed event alert for {alert.market_question} [{alert.outcome}]"
            )

    if alerts:
        logger.info(f"Sent {sent_count}/{len(alerts)} closed event alerts via Telegram")
    return sent_count
