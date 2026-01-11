"""Shared fixtures for Polybotz tests."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.config import Configuration
from src.models import MonitoredEvent, MonitoredMarket, SpikeAlert


@pytest.fixture
def valid_config():
    """A valid Configuration object."""
    return Configuration(
        slugs=["test-event-slug", "another-event-slug"],
        poll_interval=60,
        spike_threshold=5.0,
        telegram_bot_token="123456:ABC-DEF",
        telegram_chat_id="-1001234567890",
    )


@pytest.fixture
def minimal_config():
    """Minimal valid Configuration object."""
    return Configuration(
        slugs=["single-slug"],
        poll_interval=10,
        spike_threshold=0.1,
        telegram_bot_token="token",
        telegram_chat_id="chatid",
    )


@pytest.fixture
def sample_market():
    """A sample MonitoredMarket with price data."""
    return MonitoredMarket(
        id="condition-123",
        question="Will this happen?",
        outcome="Yes",
        current_price=0.75,
        previous_price=0.50,
        is_closed=False,
    )


@pytest.fixture
def market_no_previous():
    """Market without previous price (first poll)."""
    return MonitoredMarket(
        id="condition-456",
        question="New market question?",
        outcome="No",
        current_price=0.60,
        previous_price=None,
        is_closed=False,
    )


@pytest.fixture
def closed_market():
    """A closed market."""
    return MonitoredMarket(
        id="condition-789",
        question="Closed market?",
        outcome="Yes",
        current_price=0.99,
        previous_price=0.80,
        is_closed=True,
    )


@pytest.fixture
def sample_event(sample_market, market_no_previous):
    """A sample MonitoredEvent with multiple markets."""
    return MonitoredEvent(
        slug="test-event-slug",
        name="Test Event Name",
        markets=[sample_market, market_no_previous],
        last_updated=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def spike_alert():
    """A sample SpikeAlert."""
    return SpikeAlert(
        event_name="Test Event",
        market_question="Will this happen?",
        outcome="Yes",
        price_before=0.50,
        price_after=0.75,
        change_percent=50.0,
        direction="up",
        detected_at=datetime(2024, 1, 15, 12, 30, 0),
    )


@pytest.fixture
def spike_alert_down():
    """A SpikeAlert for price going down."""
    return SpikeAlert(
        event_name="Test Event",
        market_question="Will this happen?",
        outcome="Yes",
        price_before=0.80,
        price_after=0.40,
        change_percent=50.0,
        direction="down",
        detected_at=datetime(2024, 1, 15, 12, 30, 0),
    )


@pytest.fixture
def gamma_api_response():
    """Sample Gamma API response for an event."""
    return {
        "slug": "test-event-slug",
        "title": "Test Event Title",
        "markets": [
            {
                "conditionId": "cond-001",
                "question": "Will outcome A happen?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.65", "0.35"]',
                "closed": False,
            },
            {
                "conditionId": "cond-002",
                "question": "Will outcome B happen?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["0.80", "0.20"]',
                "closed": False,
            },
        ],
    }


@pytest.fixture
def gamma_api_response_list_format():
    """Sample Gamma API response with outcomes as lists (not JSON strings)."""
    return {
        "slug": "list-format-event",
        "title": "List Format Event",
        "markets": [
            {
                "conditionId": "cond-003",
                "question": "List format question?",
                "outcomes": ["Yes", "No"],
                "outcomePrices": ["0.55", "0.45"],
                "closed": False,
            },
        ],
    }


@pytest.fixture
def gamma_api_response_closed():
    """Sample Gamma API response with a closed market."""
    return {
        "slug": "closed-event-slug",
        "title": "Closed Event Title",
        "markets": [
            {
                "conditionId": "cond-closed",
                "question": "Resolved market?",
                "outcomes": '["Yes", "No"]',
                "outcomePrices": '["1.00", "0.00"]',
                "closed": True,
            },
        ],
    }


@pytest.fixture
def valid_config_yaml():
    """Valid YAML config content."""
    return """
slugs:
  - "test-slug-one"
  - "test-slug-two"

poll_interval: 60
spike_threshold: 5.0

telegram:
  bot_token: "test-bot-token"
  chat_id: "test-chat-id"
"""


@pytest.fixture
def config_with_env_vars_yaml():
    """YAML config with environment variable placeholders."""
    return """
slugs:
  - "test-slug"

poll_interval: 30
spike_threshold: 10.0

telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"
"""


@pytest.fixture
def mock_httpx_client():
    """A mock httpx.AsyncClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_successful_response():
    """Mock successful HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"ok": True, "result": {}}
    return response


@pytest.fixture
def mock_telegram_success_response():
    """Mock successful Telegram API response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "ok": True,
        "result": {"message_id": 123},
    }
    return response


@pytest.fixture
def mock_telegram_error_response():
    """Mock Telegram API error response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "ok": False,
        "description": "Bad Request: chat not found",
    }
    return response
