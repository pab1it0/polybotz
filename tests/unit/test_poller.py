"""Tests for src/poller.py."""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.config import Configuration
from src.models import MonitoredEvent, MonitoredMarket
from src.poller import (
    _parse_json_field,
    fetch_event_by_slug,
    validate_slugs,
    parse_event_response,
    update_prices,
    poll_all_events,
    GAMMA_API_BASE,
)


class TestParseJsonField:
    """Tests for _parse_json_field function."""

    def test_parse_json_string(self):
        """Test parsing JSON string into list."""
        result = _parse_json_field('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_parse_already_list(self):
        """Test handling value that's already a list."""
        result = _parse_json_field(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_parse_invalid_json(self):
        """Test handling invalid JSON string."""
        result = _parse_json_field("not valid json")
        assert result == []

    def test_parse_empty_string(self):
        """Test handling empty string."""
        result = _parse_json_field("")
        assert result == []

    def test_parse_empty_list(self):
        """Test handling empty list."""
        result = _parse_json_field([])
        assert result == []

    def test_parse_empty_json_array(self):
        """Test handling empty JSON array string."""
        result = _parse_json_field("[]")
        assert result == []

    def test_parse_none(self):
        """Test handling None value."""
        result = _parse_json_field(None)
        assert result == []

    def test_parse_number(self):
        """Test handling numeric value."""
        result = _parse_json_field(123)
        assert result == []

    def test_parse_dict(self):
        """Test handling dict value."""
        result = _parse_json_field({"key": "value"})
        assert result == []

    def test_parse_prices_json_string(self):
        """Test parsing price JSON strings (typical API format)."""
        result = _parse_json_field('["0.65", "0.35"]')
        assert result == ["0.65", "0.35"]


class TestFetchEventBySlug:
    """Tests for fetch_event_by_slug function."""

    @pytest.mark.asyncio
    async def test_fetch_success(self, gamma_api_response):
        """Test successful event fetch."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        result = await fetch_event_by_slug(mock_client, "test-slug")

        assert result == gamma_api_response
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_not_found(self):
        """Test 404 not found response."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        result = await fetch_event_by_slug(mock_client, "nonexistent-slug")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_rate_limited_then_success(self, gamma_api_response):
        """Test retry on rate limiting (429)."""
        mock_client = AsyncMock()

        rate_limited_response = MagicMock()
        rate_limited_response.status_code = 429

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = gamma_api_response

        mock_client.get.side_effect = [rate_limited_response, success_response]

        result = await fetch_event_by_slug(mock_client, "test-slug", max_retries=3)

        assert result == gamma_api_response
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_timeout_retry(self, gamma_api_response):
        """Test retry on timeout."""
        mock_client = AsyncMock()

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = gamma_api_response

        mock_client.get.side_effect = [
            httpx.TimeoutException("Timeout"),
            success_response,
        ]

        result = await fetch_event_by_slug(mock_client, "test-slug", max_retries=3)

        assert result == gamma_api_response

    @pytest.mark.asyncio
    async def test_fetch_all_retries_fail(self):
        """Test failure after all retries exhausted."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")

        result = await fetch_event_by_slug(mock_client, "test-slug", max_retries=2)

        assert result is None
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        """Test handling HTTP status error."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        result = await fetch_event_by_slug(mock_client, "test-slug", max_retries=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_request_error(self):
        """Test handling request error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        result = await fetch_event_by_slug(mock_client, "test-slug", max_retries=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_correct_url(self, gamma_api_response):
        """Test correct API URL is constructed."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        await fetch_event_by_slug(mock_client, "my-event-slug")

        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert url == f"{GAMMA_API_BASE}/events/slug/my-event-slug"


class TestValidateSlugs:
    """Tests for validate_slugs function."""

    @pytest.mark.asyncio
    async def test_validate_all_valid(self, gamma_api_response):
        """Test validation with all valid slugs."""
        config = Configuration(
            slugs=["slug1", "slug2"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = gamma_api_response
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await validate_slugs(config)

            assert result == ["slug1", "slug2"]

    @pytest.mark.asyncio
    async def test_validate_some_invalid(self, gamma_api_response):
        """Test validation with some invalid slugs."""
        config = Configuration(
            slugs=["valid-slug", "invalid-slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            valid_response = MagicMock()
            valid_response.status_code = 200
            valid_response.json.return_value = gamma_api_response

            not_found_response = MagicMock()
            not_found_response.status_code = 404

            mock_client.get.side_effect = [valid_response, not_found_response]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await validate_slugs(config)

            assert result == ["valid-slug"]

    @pytest.mark.asyncio
    async def test_validate_all_invalid(self):
        """Test validation with all invalid slugs."""
        config = Configuration(
            slugs=["invalid1", "invalid2"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await validate_slugs(config)

            assert result == []

    @pytest.mark.asyncio
    async def test_validate_logs_info(self, gamma_api_response, caplog):
        """Test that validation logs slug status."""
        config = Configuration(
            slugs=["test-slug"],
            poll_interval=60,
            spike_threshold=5.0,
            telegram_bot_token="token",
            telegram_chat_id="chatid",
        )

        with patch("src.poller.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = gamma_api_response
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with caplog.at_level("INFO"):
                await validate_slugs(config)

            assert "Validating slug" in caplog.text
            assert "Valid slug" in caplog.text


class TestParseEventResponse:
    """Tests for parse_event_response function."""

    def test_parse_json_string_format(self, gamma_api_response):
        """Test parsing response with JSON string outcomes/prices."""
        result = parse_event_response(gamma_api_response)

        assert result.slug == "test-event-slug"
        assert result.name == "Test Event Title"
        assert len(result.markets) == 4  # 2 markets * 2 outcomes each
        assert isinstance(result.last_updated, datetime)

    def test_parse_list_format(self, gamma_api_response_list_format):
        """Test parsing response with list outcomes/prices."""
        result = parse_event_response(gamma_api_response_list_format)

        assert result.slug == "list-format-event"
        assert len(result.markets) == 2  # 1 market * 2 outcomes

    def test_parse_closed_market(self, gamma_api_response_closed):
        """Test parsing closed market."""
        result = parse_event_response(gamma_api_response_closed)

        assert len(result.markets) == 2
        assert all(m.is_closed for m in result.markets)

    def test_parse_market_prices(self, gamma_api_response):
        """Test that market prices are parsed correctly."""
        result = parse_event_response(gamma_api_response)

        yes_market = next(m for m in result.markets if m.outcome == "Yes" and m.question == "Will outcome A happen?")
        assert yes_market.current_price == 0.65

    def test_parse_previous_price_is_none(self, gamma_api_response):
        """Test that previous_price is None on initial parse."""
        result = parse_event_response(gamma_api_response)

        for market in result.markets:
            assert market.previous_price is None

    def test_parse_empty_markets(self):
        """Test parsing event with no markets."""
        data = {
            "slug": "empty-event",
            "title": "Empty Event",
            "markets": [],
        }
        result = parse_event_response(data)

        assert result.slug == "empty-event"
        assert result.markets == []

    def test_parse_missing_fields(self):
        """Test parsing with missing optional fields."""
        data = {
            "markets": [
                {
                    "id": "m1",
                    "outcomes": '["Yes"]',
                    "outcomePrices": '["0.5"]',
                }
            ]
        }
        result = parse_event_response(data)

        assert result.slug == ""
        assert result.name == ""
        assert len(result.markets) == 1

    def test_parse_invalid_price(self):
        """Test handling invalid price value."""
        data = {
            "slug": "test",
            "title": "Test",
            "markets": [
                {
                    "conditionId": "c1",
                    "question": "Q",
                    "outcomes": '["Yes"]',
                    "outcomePrices": '["invalid"]',
                    "closed": False,
                }
            ],
        }
        result = parse_event_response(data)

        assert result.markets[0].current_price is None


class TestUpdatePrices:
    """Tests for update_prices function."""

    def test_update_existing_market(self, gamma_api_response):
        """Test updating existing market with new price."""
        # Create initial event
        initial_event = parse_event_response(gamma_api_response)

        # Modify the API response to have new prices
        new_data = gamma_api_response.copy()
        new_data["markets"] = [
            {
                "conditionId": "cond-001",
                "question": "Will outcome A happen?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.75", "0.25"]',  # Changed from 0.65/0.35
                "closed": False,
            },
            gamma_api_response["markets"][1],
        ]

        result = update_prices(initial_event, new_data)

        # Find the "Yes" market for outcome A
        yes_market = next(
            m for m in result.markets
            if m.outcome == "Yes" and m.question == "Will outcome A happen?"
        )

        assert yes_market.current_price == 0.75
        assert yes_market.previous_price == 0.65

    def test_update_new_market(self, gamma_api_response):
        """Test adding new market that wasn't in original."""
        initial_event = parse_event_response(gamma_api_response)

        # Add a new market
        new_data = gamma_api_response.copy()
        new_data["markets"] = gamma_api_response["markets"] + [
            {
                "conditionId": "cond-new",
                "question": "New market?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.50", "0.50"]',
                "closed": False,
            }
        ]

        result = update_prices(initial_event, new_data)

        # Find the new market
        new_market = next(
            m for m in result.markets
            if m.question == "New market?"
        )

        assert new_market.current_price == 0.50
        assert new_market.previous_price is None  # No previous price

    def test_update_preserves_event_data(self, gamma_api_response):
        """Test that event metadata is updated."""
        initial_event = parse_event_response(gamma_api_response)
        initial_time = initial_event.last_updated

        new_data = gamma_api_response.copy()
        new_data["title"] = "Updated Title"

        result = update_prices(initial_event, new_data)

        assert result.name == "Updated Title"
        assert result.last_updated >= initial_time


class TestPollAllEvents:
    """Tests for poll_all_events function."""

    @pytest.mark.asyncio
    async def test_poll_all_success(self, gamma_api_response):
        """Test polling all events successfully."""
        initial_event = parse_event_response(gamma_api_response)
        events = {"test-slug": initial_event}

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        result = await poll_all_events(mock_client, events)

        assert "test-slug" in result
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_poll_handles_failure(self, gamma_api_response):
        """Test polling continues on individual failure."""
        event1 = parse_event_response(gamma_api_response)
        event2 = MonitoredEvent(slug="slug2", name="Event 2", markets=[])
        events = {"slug1": event1, "slug2": event2}

        mock_client = AsyncMock()
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = gamma_api_response

        fail_response = MagicMock()
        fail_response.status_code = 404

        mock_client.get.side_effect = [success_response, fail_response]

        result = await poll_all_events(mock_client, events)

        # Both events should still be in result
        assert "slug1" in result
        assert "slug2" in result

    @pytest.mark.asyncio
    async def test_poll_empty_events(self):
        """Test polling empty events dict."""
        mock_client = AsyncMock()
        events: dict[str, MonitoredEvent] = {}

        result = await poll_all_events(mock_client, events)

        assert result == {}
        mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_logs_debug(self, gamma_api_response, caplog):
        """Test polling logs debug messages."""
        initial_event = parse_event_response(gamma_api_response)
        events = {"test-slug": initial_event}

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = gamma_api_response
        mock_client.get.return_value = mock_response

        with caplog.at_level("DEBUG"):
            await poll_all_events(mock_client, events)

        assert "Polling event" in caplog.text
