"""Tests for src/alerter.py."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.models import LiquidityWarning, SpikeAlert
from src.config import Configuration
from src.alerter import (
    format_alert_message,
    format_liquidity_warning_message,
    _escape_markdown,
    send_telegram_alert,
    send_all_alerts,
    send_all_liquidity_warnings,
    TELEGRAM_API_BASE,
)


class TestEscapeMarkdown:
    """Tests for _escape_markdown function."""

    def test_escape_underscore(self):
        """Test escaping underscores."""
        result = _escape_markdown("hello_world")
        assert result == "hello\\_world"

    def test_escape_asterisk(self):
        """Test escaping asterisks."""
        result = _escape_markdown("*bold*")
        assert result == "\\*bold\\*"

    def test_escape_brackets(self):
        """Test escaping brackets."""
        result = _escape_markdown("[link](url)")
        assert result == "\\[link\\]\\(url\\)"

    def test_escape_multiple_chars(self):
        """Test escaping multiple special characters."""
        result = _escape_markdown("test_with*special[chars]")
        assert result == "test\\_with\\*special\\[chars\\]"

    def test_no_escape_needed(self):
        """Test string without special characters."""
        result = _escape_markdown("plain text")
        assert result == "plain text"

    def test_escape_all_special_chars(self):
        """Test escaping all special characters."""
        special = "_*[]()~`>#+-=|{}.!"
        result = _escape_markdown(special)
        for char in special:
            assert f"\\{char}" in result

    def test_escape_empty_string(self):
        """Test empty string."""
        result = _escape_markdown("")
        assert result == ""


class TestFormatAlertMessage:
    """Tests for format_alert_message function."""

    def test_format_alert_up(self, spike_alert):
        """Test formatting alert with price going up."""
        message = format_alert_message(spike_alert)

        assert "Price Spike Detected" in message
        assert spike_alert.outcome in message
        assert "up" in spike_alert.direction
        assert "\u2191" in message  # Up arrow
        assert "+50.0%" in message

    def test_format_alert_down(self, spike_alert_down):
        """Test formatting alert with price going down."""
        message = format_alert_message(spike_alert_down)

        assert "Price Spike Detected" in message
        assert "\u2193" in message  # Down arrow
        assert "-50.0%" in message

    def test_format_alert_contains_event_name(self, spike_alert):
        """Test message contains event name."""
        message = format_alert_message(spike_alert)
        assert "Test Event" in message

    def test_format_alert_contains_market_question(self, spike_alert):
        """Test message contains market question."""
        message = format_alert_message(spike_alert)
        assert "Will this happen" in message

    def test_format_alert_contains_prices(self, spike_alert):
        """Test message contains price information."""
        message = format_alert_message(spike_alert)
        assert "0.5000" in message
        assert "0.7500" in message

    def test_format_alert_contains_timestamp(self, spike_alert):
        """Test message contains timestamp."""
        message = format_alert_message(spike_alert)
        assert "2024-01-15 12:30:00" in message

    def test_format_alert_markdown(self, spike_alert):
        """Test message uses Markdown formatting."""
        message = format_alert_message(spike_alert)
        assert "*Event*:" in message
        assert "*Market*:" in message
        assert "*Price*:" in message

    def test_format_alert_escapes_special_chars(self):
        """Test special characters in event name are escaped."""
        alert = SpikeAlert(
            event_name="Test_Event*Name",
            market_question="Question_with*special",
            outcome="Yes",
            price_before=0.50,
            price_after=0.75,
            change_percent=50.0,
            direction="up",
            detected_at=datetime(2024, 1, 15, 12, 30, 0),
        )
        message = format_alert_message(alert)
        assert "\\_" in message
        assert "\\*" in message


class TestSendTelegramAlert:
    """Tests for send_telegram_alert function."""

    @pytest.mark.asyncio
    async def test_send_alert_success(self, mock_telegram_success_response):
        """Test successful alert sending."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_telegram_alert(
                bot_token="test-token",
                chat_id="test-chat",
                message="Test message",
            )

            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_api_error(self, mock_telegram_error_response):
        """Test handling Telegram API error response."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_error_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_telegram_alert(
                bot_token="test-token",
                chat_id="test-chat",
                message="Test message",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_http_error(self):
        """Test handling HTTP error status codes."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_telegram_alert(
                bot_token="test-token",
                chat_id="test-chat",
                message="Test message",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_rate_limited(self):
        """Test handling rate limiting (429)."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_telegram_alert(
                bot_token="test-token",
                chat_id="test-chat",
                message="Test message",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_timeout(self):
        """Test handling timeout exception."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_telegram_alert(
                bot_token="test-token",
                chat_id="test-chat",
                message="Test message",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_request_error(self):
        """Test handling request error."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await send_telegram_alert(
                bot_token="test-token",
                chat_id="test-chat",
                message="Test message",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_correct_url(self, mock_telegram_success_response):
        """Test correct Telegram API URL is used."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await send_telegram_alert(
                bot_token="my-token",
                chat_id="my-chat",
                message="Test",
            )

            call_args = mock_client.post.call_args
            url = call_args[0][0]
            assert url == f"{TELEGRAM_API_BASE}/botmy-token/sendMessage"

    @pytest.mark.asyncio
    async def test_send_alert_correct_payload(self, mock_telegram_success_response):
        """Test correct payload is sent."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await send_telegram_alert(
                bot_token="token",
                chat_id="chat123",
                message="Test message",
            )

            call_args = mock_client.post.call_args
            payload = call_args.kwargs["json"]
            assert payload["chat_id"] == "chat123"
            assert payload["text"] == "Test message"
            assert payload["parse_mode"] == "Markdown"


class TestSendAllAlerts:
    """Tests for send_all_alerts function."""

    @pytest.mark.asyncio
    async def test_send_all_alerts_success(self, valid_config, spike_alert, mock_telegram_success_response):
        """Test sending multiple alerts successfully."""
        alerts = [spike_alert, spike_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_alerts(alerts, valid_config)

            assert count == 2
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_all_alerts_partial_failure(self, valid_config, spike_alert):
        """Test sending alerts with partial failures."""
        alerts = [spike_alert, spike_alert, spike_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"ok": True}

            error_response = MagicMock()
            error_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.post.side_effect = [success_response, error_response, success_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_alerts(alerts, valid_config)

            assert count == 2

    @pytest.mark.asyncio
    async def test_send_all_alerts_empty_list(self, valid_config):
        """Test sending empty alerts list."""
        count = await send_all_alerts([], valid_config)
        assert count == 0

    @pytest.mark.asyncio
    async def test_send_all_alerts_all_fail(self, valid_config, spike_alert):
        """Test when all alerts fail to send."""
        alerts = [spike_alert, spike_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_alerts(alerts, valid_config)

            assert count == 0

    @pytest.mark.asyncio
    async def test_send_all_alerts_uses_config(self, spike_alert, mock_telegram_success_response):
        """Test that config values are used for sending."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="config-token-123",
            telegram_chat_id="config-chat-456",
        )

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await send_all_alerts([spike_alert], config)

            call_args = mock_client.post.call_args
            url = call_args[0][0]
            payload = call_args.kwargs["json"]

            assert "config-token-123" in url
            assert payload["chat_id"] == "config-chat-456"

    @pytest.mark.asyncio
    async def test_send_all_alerts_logging(self, valid_config, spike_alert, mock_telegram_success_response, caplog):
        """Test logging during alert sending."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with caplog.at_level("INFO"):
                await send_all_alerts([spike_alert], valid_config)

            assert "Sent 1/1 alerts" in caplog.text


class TestFormatLiquidityWarningMessage:
    """Tests for format_liquidity_warning_message function."""

    def test_format_warning_up(self, liquidity_warning):
        """Test formatting warning with price going up."""
        message = format_liquidity_warning_message(liquidity_warning)

        assert "Liquidity Warning" in message
        assert liquidity_warning.outcome in message
        assert "\u2191" in message  # Up arrow
        assert "+20.0%" in message

    def test_format_warning_down(self, liquidity_warning_down):
        """Test formatting warning with price going down."""
        message = format_liquidity_warning_message(liquidity_warning_down)

        assert "Liquidity Warning" in message
        assert "\u2193" in message  # Down arrow
        assert "-25.0%" in message

    def test_format_warning_contains_event_name(self, liquidity_warning):
        """Test message contains event name."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "Test Event" in message

    def test_format_warning_contains_market_question(self, liquidity_warning):
        """Test message contains market question."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "Will this happen" in message

    def test_format_warning_contains_prices(self, liquidity_warning):
        """Test message contains price information."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "0.5000" in message
        assert "0.6000" in message

    def test_format_warning_contains_lvr(self, liquidity_warning):
        """Test message contains LVR information."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "12.5" in message
        assert "High Risk" in message

    def test_format_warning_contains_timestamp(self, liquidity_warning):
        """Test message contains timestamp."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "2024-01-15 12:30:00" in message

    def test_format_warning_markdown(self, liquidity_warning):
        """Test message uses Markdown formatting."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "*Event*:" in message
        assert "*Market*:" in message
        assert "*Price*:" in message
        assert "*LVR*:" in message

    def test_format_warning_escapes_special_chars(self):
        """Test special characters in event name are escaped."""
        warning = LiquidityWarning(
            event_name="Test_Event*Name",
            market_question="Question_with*special",
            outcome="Yes",
            price_before=0.50,
            price_after=0.60,
            change_percent=20.0,
            direction="up",
            lvr=12.5,
            health_status="High Risk",
            volume_24h=1000000.0,
            liquidity=80000.0,
            detected_at=datetime(2024, 1, 15, 12, 30, 0),
        )
        message = format_liquidity_warning_message(warning)
        assert "\\_" in message
        assert "\\*" in message

    def test_format_warning_uses_warning_emoji(self, liquidity_warning):
        """Test message uses warning emoji (not alert emoji)."""
        message = format_liquidity_warning_message(liquidity_warning)
        assert "\u26A0" in message  # Warning emoji


class TestSendAllLiquidityWarnings:
    """Tests for send_all_liquidity_warnings function."""

    @pytest.mark.asyncio
    async def test_send_warnings_success(self, valid_config, liquidity_warning, mock_telegram_success_response):
        """Test sending multiple warnings successfully."""
        warnings = [liquidity_warning, liquidity_warning]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_liquidity_warnings(warnings, valid_config)

            assert count == 2
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_warnings_partial_failure(self, valid_config, liquidity_warning):
        """Test sending warnings with partial failures."""
        warnings = [liquidity_warning, liquidity_warning, liquidity_warning]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"ok": True}

            error_response = MagicMock()
            error_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.post.side_effect = [success_response, error_response, success_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_liquidity_warnings(warnings, valid_config)

            assert count == 2

    @pytest.mark.asyncio
    async def test_send_warnings_empty_list(self, valid_config):
        """Test sending empty warnings list."""
        count = await send_all_liquidity_warnings([], valid_config)
        assert count == 0

    @pytest.mark.asyncio
    async def test_send_warnings_all_fail(self, valid_config, liquidity_warning):
        """Test when all warnings fail to send."""
        warnings = [liquidity_warning, liquidity_warning]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_liquidity_warnings(warnings, valid_config)

            assert count == 0

    @pytest.mark.asyncio
    async def test_send_warnings_uses_config(self, liquidity_warning, mock_telegram_success_response):
        """Test that config values are used for sending."""
        config = Configuration(
            slugs=["slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="config-token-123",
            telegram_chat_id="config-chat-456",
        )

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await send_all_liquidity_warnings([liquidity_warning], config)

            call_args = mock_client.post.call_args
            url = call_args[0][0]
            payload = call_args.kwargs["json"]

            assert "config-token-123" in url
            assert payload["chat_id"] == "config-chat-456"

    @pytest.mark.asyncio
    async def test_send_warnings_logging(self, valid_config, liquidity_warning, mock_telegram_success_response, caplog):
        """Test logging during warning sending."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with caplog.at_level("INFO"):
                await send_all_liquidity_warnings([liquidity_warning], valid_config)

            assert "Sent 1/1 liquidity warnings" in caplog.text

    @pytest.mark.asyncio
    async def test_send_warnings_no_logging_when_empty(self, valid_config, caplog):
        """Test no logging when warnings list is empty."""
        with caplog.at_level("INFO"):
            await send_all_liquidity_warnings([], valid_config)

        assert "liquidity warnings" not in caplog.text
