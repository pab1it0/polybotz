"""Tests for src/detector.py."""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.models import LiquidityWarning, MonitoredEvent, MonitoredMarket, SpikeAlert
from src.detector import (
    calculate_lvr,
    classify_lvr_health,
    detect_all_liquidity_warnings,
    detect_all_spikes,
    detect_liquidity_warning,
    detect_spike,
)


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


class TestCalculateLvr:
    """Tests for calculate_lvr function."""

    def test_calculate_lvr_normal(self):
        """Test LVR calculation with valid values."""
        result = calculate_lvr(1000000.0, 100000.0)
        assert result == 10.0

    def test_calculate_lvr_low_ratio(self):
        """Test LVR with low volume relative to liquidity."""
        result = calculate_lvr(100000.0, 1000000.0)
        assert result == 0.1

    def test_calculate_lvr_zero_liquidity(self, caplog):
        """Test LVR with zero liquidity returns None."""
        with caplog.at_level("WARNING"):
            result = calculate_lvr(1000000.0, 0)
        assert result is None
        assert "Zero/missing liquidity" in caplog.text

    def test_calculate_lvr_negative_liquidity(self, caplog):
        """Test LVR with negative liquidity returns None."""
        with caplog.at_level("WARNING"):
            result = calculate_lvr(1000000.0, -100.0)
        assert result is None
        assert "Zero/missing liquidity" in caplog.text

    def test_calculate_lvr_none_liquidity(self, caplog):
        """Test LVR with None liquidity returns None."""
        with caplog.at_level("WARNING"):
            result = calculate_lvr(1000000.0, None)
        assert result is None
        assert "Zero/missing liquidity" in caplog.text

    def test_calculate_lvr_none_volume(self, caplog):
        """Test LVR with None volume returns None."""
        with caplog.at_level("WARNING"):
            result = calculate_lvr(None, 100000.0)
        assert result is None
        assert "Missing volume_24h" in caplog.text

    def test_calculate_lvr_both_none(self, caplog):
        """Test LVR with both values None."""
        with caplog.at_level("WARNING"):
            result = calculate_lvr(None, None)
        assert result is None

    def test_calculate_lvr_zero_volume(self):
        """Test LVR with zero volume (valid, returns 0)."""
        result = calculate_lvr(0.0, 100000.0)
        assert result == 0.0

    def test_calculate_lvr_float_precision(self):
        """Test LVR with float precision."""
        result = calculate_lvr(333333.33, 100000.0)
        assert result == pytest.approx(3.3333333)


class TestClassifyLvrHealth:
    """Tests for classify_lvr_health function."""

    def test_healthy_lvr_zero(self):
        """Test LVR of 0 is Healthy."""
        assert classify_lvr_health(0.0) == "Healthy"

    def test_healthy_lvr_low(self):
        """Test LVR below 2.0 is Healthy."""
        assert classify_lvr_health(1.5) == "Healthy"
        assert classify_lvr_health(1.99) == "Healthy"

    def test_elevated_lvr_boundary(self):
        """Test LVR at exactly 2.0 is Elevated."""
        assert classify_lvr_health(2.0) == "Elevated"

    def test_elevated_lvr_mid(self):
        """Test LVR between 2.0 and 10.0 is Elevated."""
        assert classify_lvr_health(5.0) == "Elevated"
        assert classify_lvr_health(9.99) == "Elevated"

    def test_high_risk_boundary(self):
        """Test LVR at exactly 10.0 is High Risk."""
        assert classify_lvr_health(10.0) == "High Risk"

    def test_high_risk_high_values(self):
        """Test LVR above 10.0 is High Risk."""
        assert classify_lvr_health(15.0) == "High Risk"
        assert classify_lvr_health(100.0) == "High Risk"


class TestDetectLiquidityWarning:
    """Tests for detect_liquidity_warning function."""

    def test_warning_detected_high_lvr(self, market_with_lvr, spike_alert):
        """Test liquidity warning is detected when LVR exceeds threshold."""
        warning = detect_liquidity_warning(
            market=market_with_lvr,
            spike=spike_alert,
            lvr_threshold=8.0,
            event_name="Test Event",
        )

        assert warning is not None
        assert warning.event_name == "Test Event"
        assert warning.lvr == 10.0
        assert warning.health_status == "High Risk"

    def test_no_warning_low_lvr(self, market_low_lvr, spike_alert):
        """Test no warning when LVR is below threshold."""
        warning = detect_liquidity_warning(
            market=market_low_lvr,
            spike=spike_alert,
            lvr_threshold=8.0,
            event_name="Test Event",
        )

        assert warning is None

    def test_no_warning_lvr_at_threshold(self):
        """Test no warning when LVR equals threshold (must exceed)."""
        market = MonitoredMarket(
            id="m1",
            question="Q",
            outcome="Yes",
            current_price=0.60,
            previous_price=0.50,
            is_closed=False,
            volume_24h=800000.0,
            liquidity=100000.0,
            lvr=8.0,  # Exactly at threshold
        )
        spike = SpikeAlert(
            event_name="",
            market_question="Q",
            outcome="Yes",
            price_before=0.50,
            price_after=0.60,
            change_percent=20.0,
            direction="up",
            detected_at=datetime.now(),
        )

        warning = detect_liquidity_warning(
            market=market,
            spike=spike,
            lvr_threshold=8.0,
            event_name="Test",
        )

        assert warning is None

    def test_no_warning_none_lvr(self, spike_alert):
        """Test no warning when LVR is None."""
        market = MonitoredMarket(
            id="m1",
            question="Q",
            outcome="Yes",
            current_price=0.60,
            previous_price=0.50,
            is_closed=False,
            lvr=None,
        )

        warning = detect_liquidity_warning(
            market=market,
            spike=spike_alert,
            lvr_threshold=8.0,
            event_name="Test",
        )

        assert warning is None

    def test_warning_fields_correct(self):
        """Test all warning fields are populated correctly."""
        market = MonitoredMarket(
            id="m1",
            question="Will this happen?",
            outcome="Yes",
            current_price=0.60,
            previous_price=0.50,
            is_closed=False,
            volume_24h=1000000.0,
            liquidity=80000.0,
            lvr=12.5,
        )
        spike = SpikeAlert(
            event_name="",
            market_question="Will this happen?",
            outcome="Yes",
            price_before=0.50,
            price_after=0.60,
            change_percent=20.0,
            direction="up",
            detected_at=datetime.now(),
        )

        warning = detect_liquidity_warning(
            market=market,
            spike=spike,
            lvr_threshold=8.0,
            event_name="My Event",
        )

        assert warning.event_name == "My Event"
        assert warning.market_question == "Will this happen?"
        assert warning.outcome == "Yes"
        assert warning.price_before == 0.50
        assert warning.price_after == 0.60
        assert warning.change_percent == 20.0
        assert warning.direction == "up"
        assert warning.lvr == 12.5
        assert warning.health_status == "High Risk"
        assert warning.volume_24h == 1000000.0
        assert warning.liquidity == 80000.0
        assert isinstance(warning.detected_at, datetime)

    def test_warning_logging(self, market_with_lvr, spike_alert, caplog):
        """Test that liquidity warnings are logged."""
        with caplog.at_level("INFO"):
            detect_liquidity_warning(
                market=market_with_lvr,
                spike=spike_alert,
                lvr_threshold=8.0,
                event_name="Test Event",
            )

        assert "Liquidity warning" in caplog.text
        assert "LVR=" in caplog.text


class TestDetectAllLiquidityWarnings:
    """Tests for detect_all_liquidity_warnings function."""

    def test_detect_warnings_single_spike(self):
        """Test detecting liquidity warning for single spike."""
        market = MonitoredMarket(
            id="m1",
            question="Q1",
            outcome="Yes",
            current_price=0.60,
            previous_price=0.50,
            is_closed=False,
            volume_24h=1000000.0,
            liquidity=80000.0,
            lvr=12.5,
        )
        event = MonitoredEvent(
            slug="e1",
            name="Event 1",
            markets=[market],
        )
        spike = SpikeAlert(
            event_name="Event 1",
            market_question="Q1",
            outcome="Yes",
            price_before=0.50,
            price_after=0.60,
            change_percent=20.0,
            direction="up",
            detected_at=datetime.now(),
        )

        warnings = detect_all_liquidity_warnings([event], [spike], lvr_threshold=8.0)

        assert len(warnings) == 1
        assert warnings[0].lvr == 12.5

    def test_detect_warnings_multiple_spikes(self):
        """Test detecting warnings for multiple spikes."""
        market1 = MonitoredMarket(
            id="m1", question="Q1", outcome="Yes",
            current_price=0.60, previous_price=0.50, is_closed=False,
            volume_24h=1000000.0, liquidity=80000.0, lvr=12.5,
        )
        market2 = MonitoredMarket(
            id="m2", question="Q2", outcome="No",
            current_price=0.30, previous_price=0.50, is_closed=False,
            volume_24h=900000.0, liquidity=100000.0, lvr=9.0,
        )
        event = MonitoredEvent(
            slug="e1", name="Event 1",
            markets=[market1, market2],
        )
        spikes = [
            SpikeAlert(
                event_name="Event 1", market_question="Q1", outcome="Yes",
                price_before=0.50, price_after=0.60, change_percent=20.0,
                direction="up", detected_at=datetime.now(),
            ),
            SpikeAlert(
                event_name="Event 1", market_question="Q2", outcome="No",
                price_before=0.50, price_after=0.30, change_percent=40.0,
                direction="down", detected_at=datetime.now(),
            ),
        ]

        warnings = detect_all_liquidity_warnings([event], spikes, lvr_threshold=8.0)

        assert len(warnings) == 2

    def test_detect_warnings_no_spikes(self):
        """Test no warnings when no spikes."""
        market = MonitoredMarket(
            id="m1", question="Q", outcome="Yes",
            current_price=0.51, previous_price=0.50, is_closed=False,
            lvr=12.5,
        )
        event = MonitoredEvent(slug="e1", name="Event", markets=[market])

        warnings = detect_all_liquidity_warnings([event], [], lvr_threshold=8.0)

        assert len(warnings) == 0

    def test_detect_warnings_spikes_below_lvr_threshold(self):
        """Test no warnings when LVR below threshold."""
        market = MonitoredMarket(
            id="m1", question="Q", outcome="Yes",
            current_price=0.60, previous_price=0.50, is_closed=False,
            volume_24h=100000.0, liquidity=100000.0, lvr=1.0,
        )
        event = MonitoredEvent(slug="e1", name="Event", markets=[market])
        spike = SpikeAlert(
            event_name="Event", market_question="Q", outcome="Yes",
            price_before=0.50, price_after=0.60, change_percent=20.0,
            direction="up", detected_at=datetime.now(),
        )

        warnings = detect_all_liquidity_warnings([event], [spike], lvr_threshold=8.0)

        assert len(warnings) == 0

    def test_detect_warnings_mixed_results(self):
        """Test with some spikes having high LVR and some not."""
        market_high = MonitoredMarket(
            id="m1", question="Q1", outcome="Yes",
            current_price=0.60, previous_price=0.50, is_closed=False,
            lvr=12.0,
        )
        market_low = MonitoredMarket(
            id="m2", question="Q2", outcome="No",
            current_price=0.30, previous_price=0.50, is_closed=False,
            lvr=2.0,
        )
        event = MonitoredEvent(
            slug="e1", name="Event",
            markets=[market_high, market_low],
        )
        spikes = [
            SpikeAlert(
                event_name="Event", market_question="Q1", outcome="Yes",
                price_before=0.50, price_after=0.60, change_percent=20.0,
                direction="up", detected_at=datetime.now(),
            ),
            SpikeAlert(
                event_name="Event", market_question="Q2", outcome="No",
                price_before=0.50, price_after=0.30, change_percent=40.0,
                direction="down", detected_at=datetime.now(),
            ),
        ]

        warnings = detect_all_liquidity_warnings([event], spikes, lvr_threshold=8.0)

        assert len(warnings) == 1
        assert warnings[0].market_question == "Q1"

    def test_detect_warnings_logging(self, caplog):
        """Test that warning count is logged."""
        market = MonitoredMarket(
            id="m1", question="Q", outcome="Yes",
            current_price=0.60, previous_price=0.50, is_closed=False,
            lvr=12.0,
        )
        event = MonitoredEvent(slug="e1", name="Event", markets=[market])
        spike = SpikeAlert(
            event_name="Event", market_question="Q", outcome="Yes",
            price_before=0.50, price_after=0.60, change_percent=20.0,
            direction="up", detected_at=datetime.now(),
        )

        with caplog.at_level("INFO"):
            detect_all_liquidity_warnings([event], [spike], lvr_threshold=8.0)

        assert "Total liquidity warnings" in caplog.text
