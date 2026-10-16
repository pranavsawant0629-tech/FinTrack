"""Unit tests for MarketClock and NSE Holiday Calendar."""

from datetime import datetime, timezone
import pytest

from app.tools.market.clock import IST, MarketClock
from app.tools.market.models import MarketStatus


@pytest.fixture
def clock():
    return MarketClock()


def test_weekend_detection(clock: MarketClock):
    # 2026-09-12 is Saturday
    saturday = datetime(2026, 9, 12, 11, 30, tzinfo=IST)
    assert clock.is_weekend(saturday) is True
    assert clock.is_market_open(saturday) is False
    assert clock.get_session(saturday) == "closed"

    # 2026-09-13 is Sunday
    sunday = datetime(2026, 9, 13, 14, 0, tzinfo=IST)
    assert clock.is_weekend(sunday) is True
    assert clock.is_market_open(sunday) is False
    assert clock.get_session(sunday) == "closed"

    # 2026-09-16 is Wednesday (Regular weekday)
    wednesday = datetime(2026, 9, 16, 11, 0, tzinfo=IST)
    assert clock.is_weekend(wednesday) is False


def test_holiday_detection(clock: MarketClock):
    # Republic Day: 2026-01-26 (Monday)
    republic_day = datetime(2026, 1, 26, 10, 30, tzinfo=IST)
    is_holiday, name = clock.is_trading_holiday(republic_day)
    assert is_holiday is True
    assert name == "Republic Day"
    assert clock.is_market_open(republic_day) is False
    assert clock.get_session(republic_day) == "closed"

    # Ganesh Chaturthi: 2026-09-14 (Monday)
    ganesh_chaturthi = datetime(2026, 9, 14, 11, 0, tzinfo=IST)
    is_holiday, name = clock.is_trading_holiday(ganesh_chaturthi)
    assert is_holiday is True
    assert name == "Ganesh Chaturthi"
    assert clock.is_market_open(ganesh_chaturthi) is False

    # Normal trading day: 2026-09-16 (Wednesday)
    normal_day = datetime(2026, 9, 16, 11, 0, tzinfo=IST)
    is_holiday, name = clock.is_trading_holiday(normal_day)
    assert is_holiday is False
    assert name is None


def test_intraday_sessions_progression(clock: MarketClock):
    # Wednesday 2026-09-16 (Non-holiday weekday)
    
    # 1. Early morning (08:30 IST) -> closed
    t_early = datetime(2026, 9, 16, 8, 30, tzinfo=IST)
    assert clock.get_session(t_early) == "closed"
    assert clock.is_market_open(t_early) is False

    # 2. Pre-open (09:05 IST) -> pre_open
    t_pre = datetime(2026, 9, 16, 9, 5, tzinfo=IST)
    assert clock.get_session(t_pre) == "pre_open"
    assert clock.is_market_open(t_pre) is False

    # 3. Regular Trading Open (09:15 IST) -> regular_trading
    t_open = datetime(2026, 9, 16, 9, 15, tzinfo=IST)
    assert clock.get_session(t_open) == "regular_trading"
    assert clock.is_market_open(t_open) is True

    # 4. Mid-day Trading (13:45 IST) -> regular_trading
    t_mid = datetime(2026, 9, 16, 13, 45, tzinfo=IST)
    assert clock.get_session(t_mid) == "regular_trading"
    assert clock.is_market_open(t_mid) is True

    # 5. Post-close (15:35 IST) -> post_closing
    t_post = datetime(2026, 9, 16, 15, 35, tzinfo=IST)
    assert clock.get_session(t_post) == "post_closing"
    assert clock.is_market_open(t_post) is False

    # 6. Night / Closed (19:30 IST) -> closed
    t_night = datetime(2026, 9, 16, 19, 30, tzinfo=IST)
    assert clock.get_session(t_night) == "closed"
    assert clock.is_market_open(t_night) is False


def test_next_open_calculation_same_day(clock: MarketClock):
    # On Wednesday 2026-09-16 at 08:00 IST (before market open)
    t_before = datetime(2026, 9, 16, 8, 0, tzinfo=IST)
    next_open = clock.get_next_open(t_before)
    assert next_open == datetime(2026, 9, 16, 9, 15, tzinfo=IST)


def test_next_open_calculation_next_day(clock: MarketClock):
    # On Wednesday 2026-09-16 at 16:30 IST (after market close)
    t_after = datetime(2026, 9, 16, 16, 30, tzinfo=IST)
    next_open = clock.get_next_open(t_after)
    # Next day Thursday 2026-09-17 is a normal trading day
    assert next_open == datetime(2026, 9, 17, 9, 15, tzinfo=IST)


def test_next_open_skips_weekend(clock: MarketClock):
    # On Friday 2026-09-18 at 16:30 IST (after market close on Friday)
    t_fri = datetime(2026, 9, 18, 16, 30, tzinfo=IST)
    next_open = clock.get_next_open(t_fri)
    # Skips Saturday Sep 19 and Sunday Sep 20 -> Monday Sep 21 09:15
    assert next_open == datetime(2026, 9, 21, 9, 15, tzinfo=IST)


def test_next_open_skips_holiday(clock: MarketClock):
    # Friday 2026-09-11 at 17:00 IST (after market close)
    # Saturday Sep 12 -> Weekend
    # Sunday Sep 13 -> Weekend
    # Monday Sep 14 -> Ganesh Chaturthi (Holiday!)
    # Next trading day must be Tuesday Sep 15 at 09:15 IST
    t_fri = datetime(2026, 9, 11, 17, 0, tzinfo=IST)
    next_open = clock.get_next_open(t_fri)
    assert next_open == datetime(2026, 9, 15, 9, 15, tzinfo=IST)


def test_timezone_conversion(clock: MarketClock):
    # UTC 04:00 on Wednesday 2026-09-16 is 09:30 IST (Market open)
    utc_dt = datetime(2026, 9, 16, 4, 0, tzinfo=timezone.utc)
    assert clock.is_market_open(utc_dt) is True
    assert clock.get_session(utc_dt) == "regular_trading"

    # Naive datetime is assumed to be IST
    naive_dt = datetime(2026, 9, 16, 10, 0)
    assert clock.is_market_open(naive_dt) is True


def test_market_status_payload(clock: MarketClock):
    holiday_dt = datetime(2026, 1, 26, 12, 0, tzinfo=IST)
    status: MarketStatus = clock.get_market_status(holiday_dt)
    assert status.exchange == "NSE"
    assert status.is_open is False
    assert status.session_type == "closed"
    assert status.holiday_name == "Republic Day"
    assert "2026-01-27T09:15:00+05:30" in status.next_session_open_ist


def test_missing_holiday_file_fallback(tmp_path):
    # Clock pointing to non-existent file falls back gracefully
    fake_path = tmp_path / "non_existent.json"
    fallback_clock = MarketClock(holidays_path=fake_path)
    # Still recognizes weekends properly
    sat = datetime(2026, 9, 12, 11, 0, tzinfo=IST)
    assert fallback_clock.is_weekend(sat) is True
    assert fallback_clock.is_market_open(sat) is False
