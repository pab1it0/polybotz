"""Tests for src/alerter.py."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.models import ClosedEventAlert, LiquidityWarning, MADAlert, SpikeAlert, ZScoreAlert
from src.config import Configuration
from src.alerter import (
    format_alert_message,
    format_closed_event_alert,
    format_liquidity_warning_message,
    format_mad_alert,
    format_zscore_alert,
    _escape_markdown,
    send_telegram_alert,
    send_all_alerts,
    send_all_closed_event_alerts,
    send_all_liquidity_warnings,
    send_all_mad_alerts,
    send_all_zscore_alerts,
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


class TestFormatZScoreAlert:
    """Tests for format_zscore_alert function."""

    @pytest.fixture
    def zscore_alert(self):
        """Create a sample Z-score alert."""
        return ZScoreAlert(
            market_id="0x123abc",
            metric="volume",
            window="1h",
            current_value=1500.0,
            median=500.0,
            mad=100.0,
            zscore=6.75,
            threshold=3.5,
            detected_at=datetime(2024, 1, 15, 12, 30, 0),
        )

    def test_format_zscore_alert_contains_market(self, zscore_alert):
        """Test message contains market ID."""
        message = format_zscore_alert(zscore_alert)
        assert "0x123abc" in message

    def test_format_zscore_alert_contains_metric(self, zscore_alert):
        """Test message contains metric and window."""
        message = format_zscore_alert(zscore_alert)
        assert "volume" in message
        assert "1h" in message

    def test_format_zscore_alert_contains_zscore(self, zscore_alert):
        """Test message contains Z-score value."""
        message = format_zscore_alert(zscore_alert)
        assert "+6.75" in message

    def test_format_zscore_alert_spike_direction(self, zscore_alert):
        """Test message shows spike for positive Z-score."""
        message = format_zscore_alert(zscore_alert)
        assert "spike" in message

    def test_format_zscore_alert_drop_direction(self, zscore_alert):
        """Test message shows drop for negative Z-score."""
        zscore_alert.zscore = -4.5
        message = format_zscore_alert(zscore_alert)
        assert "drop" in message

    def test_format_zscore_alert_contains_threshold(self, zscore_alert):
        """Test message contains threshold."""
        message = format_zscore_alert(zscore_alert)
        assert "3.5" in message

    def test_format_zscore_alert_contains_statistics(self, zscore_alert):
        """Test message contains statistical values."""
        message = format_zscore_alert(zscore_alert)
        assert "1500" in message  # current
        assert "500" in message  # median
        assert "100" in message  # MAD

    def test_format_zscore_alert_markdown(self, zscore_alert):
        """Test message uses Markdown formatting."""
        message = format_zscore_alert(zscore_alert)
        assert "*Market*:" in message
        assert "*Z-Score*:" in message


class TestFormatMADAlert:
    """Tests for format_mad_alert function."""

    @pytest.fixture
    def mad_alert(self):
        """Create a sample MAD alert."""
        return MADAlert(
            market_id="0x456def",
            metric="price",
            window="4h",
            current_value=0.85,
            median=0.50,
            mad=0.05,
            multiplier=7.0,
            threshold_multiplier=3.0,
            detected_at=datetime(2024, 1, 15, 14, 45, 0),
        )

    def test_format_mad_alert_contains_market(self, mad_alert):
        """Test message contains market ID."""
        message = format_mad_alert(mad_alert)
        assert "0x456def" in message

    def test_format_mad_alert_contains_metric(self, mad_alert):
        """Test message contains metric and window."""
        message = format_mad_alert(mad_alert)
        assert "price" in message
        assert "4h" in message

    def test_format_mad_alert_contains_multiplier(self, mad_alert):
        """Test message contains MAD multiplier."""
        message = format_mad_alert(mad_alert)
        assert "7.0x MAD" in message

    def test_format_mad_alert_above_direction(self, mad_alert):
        """Test message shows above for price above median."""
        message = format_mad_alert(mad_alert)
        assert "above" in message

    def test_format_mad_alert_below_direction(self, mad_alert):
        """Test message shows below for price below median."""
        mad_alert.current_value = 0.15
        message = format_mad_alert(mad_alert)
        assert "below" in message

    def test_format_mad_alert_contains_threshold(self, mad_alert):
        """Test message contains threshold."""
        message = format_mad_alert(mad_alert)
        assert "3.0x MAD" in message

    def test_format_mad_alert_markdown(self, mad_alert):
        """Test message uses Markdown formatting."""
        message = format_mad_alert(mad_alert)
        assert "*Market*:" in message
        assert "*Deviation*:" in message


class TestSendAllZScoreAlerts:
    """Tests for send_all_zscore_alerts function."""

    @pytest.fixture
    def zscore_alert(self):
        """Create a sample Z-score alert."""
        return ZScoreAlert(
            market_id="0x123abc",
            metric="volume",
            window="1h",
            current_value=1500.0,
            median=500.0,
            mad=100.0,
            zscore=6.75,
            threshold=3.5,
            detected_at=datetime(2024, 1, 15, 12, 30, 0),
        )

    @pytest.mark.asyncio
    async def test_send_zscore_alerts_success(self, valid_config, zscore_alert, mock_telegram_success_response):
        """Test sending multiple Z-score alerts successfully."""
        alerts = [zscore_alert, zscore_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_zscore_alerts(alerts, valid_config)

            assert count == 2
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_zscore_alerts_empty_list(self, valid_config):
        """Test sending empty Z-score alerts list."""
        count = await send_all_zscore_alerts([], valid_config)
        assert count == 0

    @pytest.mark.asyncio
    async def test_send_zscore_alerts_partial_failure(self, valid_config, zscore_alert):
        """Test sending Z-score alerts with partial failures."""
        alerts = [zscore_alert, zscore_alert, zscore_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"ok": True}

            error_response = MagicMock()
            error_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.post.side_effect = [success_response, error_response, success_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_zscore_alerts(alerts, valid_config)

            assert count == 2

    @pytest.mark.asyncio
    async def test_send_zscore_alerts_logging(self, valid_config, zscore_alert, mock_telegram_success_response, caplog):
        """Test logging during Z-score alert sending."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with caplog.at_level("INFO"):
                await send_all_zscore_alerts([zscore_alert], valid_config)

            assert "Sent 1/1 Z-score alerts" in caplog.text


class TestSendAllMADAlerts:
    """Tests for send_all_mad_alerts function."""

    @pytest.fixture
    def mad_alert(self):
        """Create a sample MAD alert."""
        return MADAlert(
            market_id="0x456def",
            metric="price",
            window="4h",
            current_value=0.85,
            median=0.50,
            mad=0.05,
            multiplier=7.0,
            threshold_multiplier=3.0,
            detected_at=datetime(2024, 1, 15, 14, 45, 0),
        )

    @pytest.mark.asyncio
    async def test_send_mad_alerts_success(self, valid_config, mad_alert, mock_telegram_success_response):
        """Test sending multiple MAD alerts successfully."""
        alerts = [mad_alert, mad_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_mad_alerts(alerts, valid_config)

            assert count == 2
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_mad_alerts_empty_list(self, valid_config):
        """Test sending empty MAD alerts list."""
        count = await send_all_mad_alerts([], valid_config)
        assert count == 0

    @pytest.mark.asyncio
    async def test_send_mad_alerts_partial_failure(self, valid_config, mad_alert):
        """Test sending MAD alerts with partial failures."""
        alerts = [mad_alert, mad_alert, mad_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"ok": True}

            error_response = MagicMock()
            error_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.post.side_effect = [success_response, error_response, success_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_mad_alerts(alerts, valid_config)

            assert count == 2

    @pytest.mark.asyncio
    async def test_send_mad_alerts_logging(self, valid_config, mad_alert, mock_telegram_success_response, caplog):
        """Test logging during MAD alert sending."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with caplog.at_level("INFO"):
                await send_all_mad_alerts([mad_alert], valid_config)

            assert "Sent 1/1 MAD alerts" in caplog.text


class TestFormatClosedEventAlert:
    """Tests for format_closed_event_alert function."""

    def test_format_closed_event_alert_contains_event_name(self, closed_event_alert):
        """Test message contains event name."""
        message = format_closed_event_alert(closed_event_alert)
        assert "Test Event" in message

    def test_format_closed_event_alert_contains_market_question(self, closed_event_alert):
        """Test message contains market question."""
        message = format_closed_event_alert(closed_event_alert)
        assert "Did this happen" in message

    def test_format_closed_event_alert_contains_outcome(self, closed_event_alert):
        """Test message contains outcome."""
        message = format_closed_event_alert(closed_event_alert)
        assert "Yes" in message

    def test_format_closed_event_alert_contains_final_price(self, closed_event_alert):
        """Test message contains final price."""
        message = format_closed_event_alert(closed_event_alert)
        assert "0.9500" in message

    def test_format_closed_event_alert_no_price(self, closed_event_alert_no_price):
        """Test message when final price is None."""
        message = format_closed_event_alert(closed_event_alert_no_price)
        assert "N/A" in message

    def test_format_closed_event_alert_contains_timestamp(self, closed_event_alert):
        """Test message contains timestamp."""
        message = format_closed_event_alert(closed_event_alert)
        assert "2024-01-15 12:30:00" in message

    def test_format_closed_event_alert_markdown(self, closed_event_alert):
        """Test message uses Markdown formatting."""
        message = format_closed_event_alert(closed_event_alert)
        assert "*Event*:" in message
        assert "*Market*:" in message
        assert "*Final Price*:" in message

    def test_format_closed_event_alert_uses_checkmark(self, closed_event_alert):
        """Test message uses checkmark emoji."""
        message = format_closed_event_alert(closed_event_alert)
        assert "\u2705" in message  # Checkmark emoji

    def test_format_closed_event_alert_escapes_special_chars(self):
        """Test special characters in event name are escaped."""
        alert = ClosedEventAlert(
            event_name="Test_Event*Name",
            event_slug="test-slug",
            market_question="Question_with*special",
            outcome="Yes",
            final_price=0.95,
            detected_at=datetime(2024, 1, 15, 12, 30, 0),
        )
        message = format_closed_event_alert(alert)
        assert "\\_" in message
        assert "\\*" in message


class TestSendAllClosedEventAlerts:
    """Tests for send_all_closed_event_alerts function."""

    @pytest.mark.asyncio
    async def test_send_closed_alerts_success(self, valid_config, closed_event_alert, mock_telegram_success_response):
        """Test sending multiple closed event alerts successfully."""
        alerts = [closed_event_alert, closed_event_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_closed_event_alerts(alerts, valid_config)

            assert count == 2
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_closed_alerts_empty_list(self, valid_config):
        """Test sending empty closed event alerts list."""
        count = await send_all_closed_event_alerts([], valid_config)
        assert count == 0

    @pytest.mark.asyncio
    async def test_send_closed_alerts_partial_failure(self, valid_config, closed_event_alert):
        """Test sending closed event alerts with partial failures."""
        alerts = [closed_event_alert, closed_event_alert, closed_event_alert]

        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {"ok": True}

            error_response = MagicMock()
            error_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.post.side_effect = [success_response, error_response, success_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            count = await send_all_closed_event_alerts(alerts, valid_config)

            assert count == 2

    @pytest.mark.asyncio
    async def test_send_closed_alerts_logging(self, valid_config, closed_event_alert, mock_telegram_success_response, caplog):
        """Test logging during closed event alert sending."""
        with patch("src.alerter.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_telegram_success_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with caplog.at_level("INFO"):
                await send_all_closed_event_alerts([closed_event_alert], valid_config)

            assert "Sent 1/1 closed event alerts" in caplog.text

    @pytest.mark.asyncio
    async def test_send_closed_alerts_no_logging_when_empty(self, valid_config, caplog):
        """Test no logging when closed alerts list is empty."""
        with caplog.at_level("INFO"):
            await send_all_closed_event_alerts([], valid_config)

        assert "closed event alerts" not in caplog.text
