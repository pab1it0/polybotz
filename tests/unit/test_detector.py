"""Tests for src/detector.py."""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.models import MonitoredEvent, MonitoredMarket, SpikeAlert
from src.detector import detect_spike, detect_all_spikes


class TestDetectSpike:
    """Tests for detect_spike function."""

    def test_detect_spike_above_threshold(self):
        """Test spike detection when change exceeds threshold."""
        market = MonitoredMarket(
            id="test-id",
            question="Question?",
            outcome="Yes",
            current_price=0.60,
            previous_price=0.50,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)

        assert result is not None
        assert result.direction == "up"
        assert result.change_percent == pytest.approx(20.0)
        assert result.price_before == 0.50
        assert result.price_after == 0.60

    def test_detect_spike_below_threshold(self):
        """Test no spike when change is below threshold."""
        market = MonitoredMarket(
            id="test-id",
            question="Question?",
            outcome="Yes",
            current_price=0.51,
            previous_price=0.50,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result is None

    def test_detect_spike_exactly_at_threshold(self):
        """Test spike at exactly the threshold."""
        market = MonitoredMarket(
            id="test-id",
            question="Question?",
            outcome="Yes",
            current_price=0.525,
            previous_price=0.50,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result is not None
        assert result.change_percent == pytest.approx(5.0)

    def test_detect_spike_direction_up(self):
        """Test direction is 'up' for price increase."""
        market = MonitoredMarket(
            id="test-id",
            question="Q",
            outcome="Yes",
            current_price=0.80,
            previous_price=0.50,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result.direction == "up"

    def test_detect_spike_direction_down(self):
        """Test direction is 'down' for price decrease."""
        market = MonitoredMarket(
            id="test-id",
            question="Q",
            outcome="Yes",
            current_price=0.40,
            previous_price=0.80,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result.direction == "down"
        assert result.change_percent == 50.0

    def test_closed_market_returns_none(self, closed_market):
        """Test closed market returns None."""
        result = detect_spike(closed_market, threshold=5.0)
        assert result is None

    def test_first_poll_no_previous_price(self, market_no_previous):
        """Test first poll (no previous price) returns None."""
        result = detect_spike(market_no_previous, threshold=5.0)
        assert result is None

    def test_zero_previous_price_returns_none(self):
        """Test zero previous price returns None (avoid division by zero)."""
        market = MonitoredMarket(
            id="test-id",
            question="Q",
            outcome="Yes",
            current_price=0.50,
            previous_price=0.0,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result is None

    def test_none_current_price_returns_none(self):
        """Test None current price returns None."""
        market = MonitoredMarket(
            id="test-id",
            question="Q",
            outcome="Yes",
            current_price=None,
            previous_price=0.50,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result is None

    def test_spike_alert_fields(self, sample_market):
        """Test SpikeAlert fields are populated correctly."""
        result = detect_spike(sample_market, threshold=5.0)

        assert result is not None
        assert result.event_name == ""  # Filled by detect_all_spikes
        assert result.market_question == sample_market.question
        assert result.outcome == sample_market.outcome
        assert result.price_before == sample_market.previous_price
        assert result.price_after == sample_market.current_price
        assert isinstance(result.detected_at, datetime)

    def test_large_spike(self):
        """Test detection of large price spike."""
        market = MonitoredMarket(
            id="test-id",
            question="Q",
            outcome="Yes",
            current_price=0.90,
            previous_price=0.10,
            is_closed=False,
        )
        result = detect_spike(market, threshold=5.0)
        assert result is not None
        assert result.change_percent == 800.0

    def test_small_threshold(self):
        """Test with very small threshold."""
        market = MonitoredMarket(
            id="test-id",
            question="Q",
            outcome="Yes",
            current_price=0.502,
            previous_price=0.500,
            is_closed=False,
        )
        result = detect_spike(market, threshold=0.1)
        assert result is not None


class TestDetectAllSpikes:
    """Tests for detect_all_spikes function."""

    def test_detect_spikes_single_event(self, sample_event):
        """Test detecting spikes in a single event."""
        spikes = detect_all_spikes([sample_event], threshold=5.0)

        assert len(spikes) == 1
        assert spikes[0].event_name == sample_event.name

    def test_detect_spikes_multiple_events(self):
        """Test detecting spikes across multiple events."""
        market1 = MonitoredMarket(
            id="m1",
            question="Q1",
            outcome="Yes",
            current_price=0.70,
            previous_price=0.50,
            is_closed=False,
        )
        market2 = MonitoredMarket(
            id="m2",
            question="Q2",
            outcome="No",
            current_price=0.30,
            previous_price=0.50,
            is_closed=False,
        )
        event1 = MonitoredEvent(
            slug="event1",
            name="Event 1",
            markets=[market1],
        )
        event2 = MonitoredEvent(
            slug="event2",
            name="Event 2",
            markets=[market2],
        )

        spikes = detect_all_spikes([event1, event2], threshold=5.0)

        assert len(spikes) == 2
        event_names = {s.event_name for s in spikes}
        assert "Event 1" in event_names
        assert "Event 2" in event_names

    def test_detect_spikes_no_spikes(self):
        """Test when no spikes are detected."""
        market = MonitoredMarket(
            id="m1",
            question="Q",
            outcome="Yes",
            current_price=0.50,
            previous_price=0.49,
            is_closed=False,
        )
        event = MonitoredEvent(
            slug="event",
            name="Event",
            markets=[market],
        )

        spikes = detect_all_spikes([event], threshold=10.0)
        assert len(spikes) == 0

    def test_detect_spikes_empty_events(self):
        """Test with empty events list."""
        spikes = detect_all_spikes([], threshold=5.0)
        assert len(spikes) == 0

    def test_detect_spikes_event_without_markets(self):
        """Test event with no markets."""
        event = MonitoredEvent(
            slug="empty",
            name="Empty Event",
            markets=[],
        )
        spikes = detect_all_spikes([event], threshold=5.0)
        assert len(spikes) == 0

    def test_detect_spikes_mixed_results(self):
        """Test with some markets having spikes and some not."""
        spike_market = MonitoredMarket(
            id="m1",
            question="Q1",
            outcome="Yes",
            current_price=0.80,
            previous_price=0.50,
            is_closed=False,
        )
        no_spike_market = MonitoredMarket(
            id="m2",
            question="Q2",
            outcome="No",
            current_price=0.51,
            previous_price=0.50,
            is_closed=False,
        )
        closed_market = MonitoredMarket(
            id="m3",
            question="Q3",
            outcome="Yes",
            current_price=1.00,
            previous_price=0.50,
            is_closed=True,
        )

        event = MonitoredEvent(
            slug="mixed",
            name="Mixed Event",
            markets=[spike_market, no_spike_market, closed_market],
        )

        spikes = detect_all_spikes([event], threshold=5.0)

        assert len(spikes) == 1
        assert spikes[0].market_question == "Q1"

    def test_event_name_assigned_to_spike(self):
        """Test that event_name is correctly assigned to spike."""
        market = MonitoredMarket(
            id="m1",
            question="Q",
            outcome="Yes",
            current_price=0.80,
            previous_price=0.50,
            is_closed=False,
        )
        event = MonitoredEvent(
            slug="slug",
            name="My Special Event",
            markets=[market],
        )

        spikes = detect_all_spikes([event], threshold=5.0)

        assert spikes[0].event_name == "My Special Event"

    def test_logging_on_spikes(self, caplog):
        """Test that spikes are logged."""
        market = MonitoredMarket(
            id="m1",
            question="Test Question",
            outcome="Yes",
            current_price=0.80,
            previous_price=0.50,
            is_closed=False,
        )
        event = MonitoredEvent(
            slug="slug",
            name="Event",
            markets=[market],
        )

        with caplog.at_level("INFO"):
            detect_all_spikes([event], threshold=5.0)

        assert "Spike detected" in caplog.text
        assert "Total spikes detected" in caplog.text
