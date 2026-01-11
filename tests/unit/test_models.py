"""Tests for src/models.py dataclasses."""

import pytest
from datetime import datetime

from src.models import MonitoredEvent, MonitoredMarket, SpikeAlert


class TestMonitoredMarket:
    """Tests for MonitoredMarket dataclass."""

    def test_create_with_all_fields(self):
        """Test creating market with all fields."""
        market = MonitoredMarket(
            id="test-id",
            question="Test question?",
            outcome="Yes",
            current_price=0.75,
            previous_price=0.50,
            is_closed=False,
        )
        assert market.id == "test-id"
        assert market.question == "Test question?"
        assert market.outcome == "Yes"
        assert market.current_price == 0.75
        assert market.previous_price == 0.50
        assert market.is_closed is False

    def test_create_with_defaults(self):
        """Test creating market with default values."""
        market = MonitoredMarket(
            id="id",
            question="question",
            outcome="outcome",
        )
        assert market.current_price is None
        assert market.previous_price is None
        assert market.is_closed is False

    def test_none_prices(self):
        """Test market with None prices."""
        market = MonitoredMarket(
            id="id",
            question="Q",
            outcome="Yes",
            current_price=None,
            previous_price=None,
        )
        assert market.current_price is None
        assert market.previous_price is None

    def test_closed_market(self):
        """Test closed market."""
        market = MonitoredMarket(
            id="id",
            question="Q",
            outcome="Yes",
            is_closed=True,
        )
        assert market.is_closed is True

    def test_price_types(self):
        """Test that prices can be floats."""
        market = MonitoredMarket(
            id="id",
            question="Q",
            outcome="Yes",
            current_price=0.123456789,
            previous_price=0.987654321,
        )
        assert isinstance(market.current_price, float)
        assert isinstance(market.previous_price, float)


class TestMonitoredEvent:
    """Tests for MonitoredEvent dataclass."""

    def test_create_with_all_fields(self):
        """Test creating event with all fields."""
        now = datetime.now()
        markets = [
            MonitoredMarket(id="1", question="Q1", outcome="Yes"),
            MonitoredMarket(id="2", question="Q2", outcome="No"),
        ]
        event = MonitoredEvent(
            slug="test-slug",
            name="Test Name",
            markets=markets,
            last_updated=now,
        )
        assert event.slug == "test-slug"
        assert event.name == "Test Name"
        assert len(event.markets) == 2
        assert event.last_updated == now

    def test_create_with_defaults(self):
        """Test creating event with default values."""
        event = MonitoredEvent(slug="slug", name="name")
        assert event.markets == []
        assert event.last_updated is None

    def test_empty_markets_list(self):
        """Test event with empty markets list."""
        event = MonitoredEvent(slug="slug", name="name", markets=[])
        assert event.markets == []
        assert len(event.markets) == 0

    def test_markets_default_factory(self):
        """Test that markets default to empty list, not shared."""
        event1 = MonitoredEvent(slug="slug1", name="name1")
        event2 = MonitoredEvent(slug="slug2", name="name2")

        event1.markets.append(MonitoredMarket(id="1", question="Q", outcome="Y"))

        assert len(event1.markets) == 1
        assert len(event2.markets) == 0


class TestSpikeAlert:
    """Tests for SpikeAlert dataclass."""

    def test_create_spike_alert(self):
        """Test creating spike alert."""
        now = datetime.now()
        alert = SpikeAlert(
            event_name="Event",
            market_question="Question?",
            outcome="Yes",
            price_before=0.50,
            price_after=0.75,
            change_percent=50.0,
            direction="up",
            detected_at=now,
        )
        assert alert.event_name == "Event"
        assert alert.market_question == "Question?"
        assert alert.outcome == "Yes"
        assert alert.price_before == 0.50
        assert alert.price_after == 0.75
        assert alert.change_percent == 50.0
        assert alert.direction == "up"
        assert alert.detected_at == now

    def test_direction_up(self, spike_alert):
        """Test spike alert with direction up."""
        assert spike_alert.direction == "up"
        assert spike_alert.price_after > spike_alert.price_before

    def test_direction_down(self, spike_alert_down):
        """Test spike alert with direction down."""
        assert spike_alert_down.direction == "down"
        assert spike_alert_down.price_after < spike_alert_down.price_before

    def test_change_percent_calculation(self):
        """Test that change_percent is stored correctly."""
        alert = SpikeAlert(
            event_name="E",
            market_question="Q",
            outcome="Y",
            price_before=0.20,
            price_after=0.30,
            change_percent=50.0,
            direction="up",
            detected_at=datetime.now(),
        )
        assert alert.change_percent == 50.0

    def test_detected_at_timestamp(self):
        """Test detected_at is a datetime."""
        specific_time = datetime(2024, 6, 15, 10, 30, 45)
        alert = SpikeAlert(
            event_name="E",
            market_question="Q",
            outcome="Y",
            price_before=0.1,
            price_after=0.2,
            change_percent=100.0,
            direction="up",
            detected_at=specific_time,
        )
        assert alert.detected_at == specific_time
        assert alert.detected_at.year == 2024
        assert alert.detected_at.month == 6
