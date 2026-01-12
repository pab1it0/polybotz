"""Tests for CLOB client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clob_client import (
    CLOB_API_BASE,
    calculate_book_volume,
    fetch_book,
    fetch_midpoint,
    fetch_price,
    poll_clob_markets,
)


@pytest.fixture
def mock_client():
    """Create a mock httpx.AsyncClient."""
    return AsyncMock(spec=httpx.AsyncClient)


def create_mock_response(status_code: int, json_data: dict | None = None):
    """Create a mock httpx Response with sync json() method."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_data is not None:
        mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()
    return mock_response


class TestFetchPrice:
    """Tests for fetch_price function."""

    @pytest.mark.asyncio
    async def test_fetch_price_success(self, mock_client):
        """Test successful price fetch."""
        mock_response = create_mock_response(200, {"price": "0.65"})
        mock_client.get.return_value = mock_response

        result = await fetch_price(mock_client, "token123")

        assert result == 0.65
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_price_404(self, mock_client):
        """Test price fetch returns None on 404."""
        mock_response = create_mock_response(404)
        mock_client.get.return_value = mock_response

        result = await fetch_price(mock_client, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_price_retry_on_429(self, mock_client):
        """Test price fetch retries on rate limit."""
        mock_response_429 = create_mock_response(429)
        mock_response_ok = create_mock_response(200, {"price": "0.75"})

        mock_client.get.side_effect = [mock_response_429, mock_response_ok]

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_price(mock_client, "token123", max_retries=2)

        assert result == 0.75
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_price_timeout_handling(self, mock_client):
        """Test price fetch handles timeout gracefully."""
        mock_client.get.side_effect = httpx.TimeoutException("timeout")

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_price(mock_client, "token123", max_retries=2)

        assert result is None


class TestFetchPriceErrors:
    """Tests for fetch_price error handling."""

    @pytest.mark.asyncio
    async def test_fetch_price_http_status_error(self, mock_client):
        """Test fetch_price handles HTTP status errors."""
        mock_response = create_mock_response(500)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_price(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_price_request_error(self, mock_client):
        """Test fetch_price handles request errors."""
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_price(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_price_value_error(self, mock_client):
        """Test fetch_price handles invalid price values."""
        mock_response = create_mock_response(200, {"price": "invalid"})
        mock_response.json.return_value = {"price": "invalid"}
        # Simulate ValueError when converting price
        original_json = mock_response.json.return_value
        mock_response.json.return_value = {"price": "not_a_number"}
        mock_client.get.return_value = mock_response

        result = await fetch_price(mock_client, "token123", max_retries=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_price_missing_price_key(self, mock_client):
        """Test fetch_price handles missing price key."""
        mock_response = create_mock_response(200, {"other_key": "value"})
        mock_client.get.return_value = mock_response

        result = await fetch_price(mock_client, "token123")

        assert result is None


class TestFetchMidpoint:
    """Tests for fetch_midpoint function."""

    @pytest.mark.asyncio
    async def test_fetch_midpoint_success(self, mock_client):
        """Test successful midpoint fetch."""
        mock_response = create_mock_response(200, {"mid": "0.55"})
        mock_client.get.return_value = mock_response

        result = await fetch_midpoint(mock_client, "token123")

        assert result == 0.55

    @pytest.mark.asyncio
    async def test_fetch_midpoint_404(self, mock_client):
        """Test midpoint fetch returns None on 404."""
        mock_response = create_mock_response(404)
        mock_client.get.return_value = mock_response

        result = await fetch_midpoint(mock_client, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_midpoint_retry_on_429(self, mock_client):
        """Test midpoint fetch retries on rate limit."""
        mock_response_429 = create_mock_response(429)
        mock_response_ok = create_mock_response(200, {"mid": "0.65"})

        mock_client.get.side_effect = [mock_response_429, mock_response_ok]

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_midpoint(mock_client, "token123", max_retries=2)

        assert result == 0.65
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_midpoint_timeout(self, mock_client):
        """Test midpoint fetch handles timeout."""
        mock_client.get.side_effect = httpx.TimeoutException("timeout")

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_midpoint(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_midpoint_http_error(self, mock_client):
        """Test midpoint fetch handles HTTP errors."""
        mock_response = create_mock_response(500)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_midpoint(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_midpoint_request_error(self, mock_client):
        """Test midpoint fetch handles request errors."""
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_midpoint(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_midpoint_missing_mid_key(self, mock_client):
        """Test midpoint fetch handles missing mid key."""
        mock_response = create_mock_response(200, {"other": "value"})
        mock_client.get.return_value = mock_response

        result = await fetch_midpoint(mock_client, "token123")

        assert result is None


class TestFetchBook:
    """Tests for fetch_book function."""

    @pytest.mark.asyncio
    async def test_fetch_book_success(self, mock_client):
        """Test successful book fetch."""
        book_data = {
            "market": "0x123",
            "bids": [{"price": "0.64", "size": "100.00"}],
            "asks": [{"price": "0.66", "size": "150.00"}],
        }
        mock_response = create_mock_response(200, book_data)
        mock_client.get.return_value = mock_response

        result = await fetch_book(mock_client, "token123")

        assert result == book_data

    @pytest.mark.asyncio
    async def test_fetch_book_404(self, mock_client):
        """Test book fetch returns None on 404."""
        mock_response = create_mock_response(404)
        mock_client.get.return_value = mock_response

        result = await fetch_book(mock_client, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_book_retry_on_429(self, mock_client):
        """Test book fetch retries on rate limit."""
        mock_response_429 = create_mock_response(429)
        book_data = {"bids": [], "asks": []}
        mock_response_ok = create_mock_response(200, book_data)

        mock_client.get.side_effect = [mock_response_429, mock_response_ok]

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_book(mock_client, "token123", max_retries=2)

        assert result == book_data
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_book_timeout(self, mock_client):
        """Test book fetch handles timeout."""
        mock_client.get.side_effect = httpx.TimeoutException("timeout")

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_book(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_book_http_error(self, mock_client):
        """Test book fetch handles HTTP errors."""
        mock_response = create_mock_response(500)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_client.get.return_value = mock_response

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_book(mock_client, "token123", max_retries=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_book_request_error(self, mock_client):
        """Test book fetch handles request errors."""
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        with patch("src.clob_client.asyncio.sleep", new_callable=AsyncMock):
            result = await fetch_book(mock_client, "token123", max_retries=2)

        assert result is None


class TestCalculateBookVolume:
    """Tests for calculate_book_volume function."""

    def test_calculate_book_volume(self):
        """Test volume calculation from orderbook."""
        book = {
            "bids": [
                {"price": "0.64", "size": "100.00"},
                {"price": "0.63", "size": "50.00"},
            ],
            "asks": [
                {"price": "0.66", "size": "150.00"},
            ],
        }
        result = calculate_book_volume(book)
        assert result == 300.0

    def test_calculate_book_volume_empty(self):
        """Test volume calculation with empty book."""
        book = {"bids": [], "asks": []}
        result = calculate_book_volume(book)
        assert result == 0.0

    def test_calculate_book_volume_missing_keys(self):
        """Test volume calculation handles missing keys."""
        book = {}
        result = calculate_book_volume(book)
        assert result == 0.0

    def test_calculate_book_volume_invalid_size(self):
        """Test volume calculation handles invalid size values."""
        book = {
            "bids": [
                {"price": "0.64", "size": "invalid"},
                {"price": "0.63", "size": "50.00"},
            ],
            "asks": [
                {"price": "0.66", "size": None},
            ],
        }
        result = calculate_book_volume(book)
        # Should only count the valid 50.00
        assert result == 50.0

    def test_calculate_book_volume_missing_size(self):
        """Test volume calculation handles missing size key."""
        book = {
            "bids": [
                {"price": "0.64"},  # No size key
                {"price": "0.63", "size": "50.00"},
            ],
            "asks": [],
        }
        result = calculate_book_volume(book)
        assert result == 50.0


class TestPollClobMarkets:
    """Tests for poll_clob_markets function."""

    @pytest.mark.asyncio
    async def test_poll_clob_markets(self, mock_client):
        """Test polling multiple markets."""
        # Mock midpoint responses
        mock_mid_response = create_mock_response(200, {"mid": "0.65"})

        # Mock book responses
        mock_book_response = create_mock_response(200, {
            "bids": [{"price": "0.64", "size": "100.00"}],
            "asks": [{"price": "0.66", "size": "100.00"}],
        })

        # Alternate between midpoint and book calls
        mock_client.get.side_effect = [
            mock_mid_response,
            mock_book_response,
        ]

        result = await poll_clob_markets(mock_client, ["market1"])

        assert "market1" in result
        price, volume = result["market1"]
        assert price == 0.65
        assert volume == 200.0
