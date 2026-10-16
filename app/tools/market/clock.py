"""Deterministic NSE/BSE Market Clock and Session State Evaluator.

Accurately tracks Indian Equity market sessions (Pre-Open, Regular Trading,
Post-Close, Closed) in Asia/Kolkata timezone (IST, UTC+5:30) and evaluates
trading holidays against the official NSE holiday calendar.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Literal

from app.tools.market.models import MarketStatus

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo
    IST: timezone = ZoneInfo("Asia/Kolkata")  # type: ignore[assignment]
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")

# Session time boundaries (IST)
PRE_OPEN_START = time(9, 0)
PRE_OPEN_END = time(9, 15)
REGULAR_START = time(9, 15)
REGULAR_END = time(15, 30)
POST_CLOSE_START = time(15, 30)
POST_CLOSE_END = time(16, 0)


def _default_holidays_path() -> Path:
    """Resolve project root data/market/nse_holidays.json."""
    # clock.py -> market/ -> tools/ -> app/ -> project_root
    root = Path(__file__).resolve().parent.parent.parent.parent
    return root / "data" / "market" / "nse_holidays.json"


class MarketClock:
    """NSE/BSE Indian Equity Market Clock.
    
    Determines market open/closed status, current trading session,
    trading holidays, and next regular session opening time.
    """

    def __init__(self, holidays_path: Path | str | None = None) -> None:
        self.holidays_path = Path(holidays_path) if holidays_path else _default_holidays_path()
        self._holidays: dict[str, str] = {}
        self._load_holidays()

    def _load_holidays(self) -> None:
        """Load holiday definitions from JSON."""
        if not self.holidays_path.exists():
            logger.warning(
                "NSE holiday calendar file not found at %s. Falling back to weekend-only calendar.",
                self.holidays_path,
            )
            return

        try:
            with open(self.holidays_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("trading_holidays", []):
                    dt_str = item.get("date")
                    desc = item.get("description", "Trading Holiday")
                    if dt_str:
                        self._holidays[dt_str] = desc
        except Exception as exc:
            logger.error("Failed to parse NSE holiday calendar from %s: %s", self.holidays_path, exc)

    def get_ist_now(self) -> datetime:
        """Return the current datetime localized to Asia/Kolkata."""
        return datetime.now(IST)

    def is_weekend(self, dt: datetime | date | None = None) -> bool:
        """Check if date is a Saturday (5) or Sunday (6)."""
        if dt is None:
            dt = self.get_ist_now()
        target_date = dt.date() if isinstance(dt, datetime) else dt
        return target_date.weekday() in (5, 6)

    def is_trading_holiday(self, dt: datetime | date | None = None) -> tuple[bool, str | None]:
        """Check if date is a listed NSE trading holiday.
        
        Returns:
            tuple[bool, str | None]: (is_holiday, holiday_name)
        """
        if dt is None:
            dt = self.get_ist_now()
        target_date = dt.date() if isinstance(dt, datetime) else dt
        date_key = target_date.strftime("%Y-%m-%d")
        if date_key in self._holidays:
            return True, self._holidays[date_key]
        return False, None

    def is_market_open(self, dt: datetime | None = None) -> bool:
        """Return True if current time is within Regular Trading hours (09:15 - 15:30 IST).
        
        Returns False on weekends, trading holidays, or outside regular hours.
        """
        status = self.get_market_status(dt)
        return status.is_open

    def get_session(
        self, dt: datetime | None = None
    ) -> Literal["pre_open", "regular_trading", "post_closing", "closed"]:
        """Return the current trading session label."""
        if dt is None:
            dt = self.get_ist_now()
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        else:
            dt = dt.astimezone(IST)

        if self.is_weekend(dt):
            return "closed"

        is_holiday, _ = self.is_trading_holiday(dt)
        if is_holiday:
            return "closed"

        t = dt.time()
        if PRE_OPEN_START <= t < PRE_OPEN_END:
            return "pre_open"
        if REGULAR_START <= t < REGULAR_END:
            return "regular_trading"
        if POST_CLOSE_START <= t < POST_CLOSE_END:
            return "post_closing"
        return "closed"

    def get_next_open(self, dt: datetime | None = None) -> datetime:
        """Calculate the next regular trading session opening datetime (09:15 IST).
        
        If currently before 09:15 on an active trading day, returns today at 09:15 IST.
        Otherwise advances day by day until a non-holiday weekday is found.
        """
        if dt is None:
            dt = self.get_ist_now()
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        else:
            dt = dt.astimezone(IST)

        current_date = dt.date()
        current_time = dt.time()

        # Check if today is a trading day and market hasn't opened yet
        if not self.is_weekend(current_date):
            is_holiday, _ = self.is_trading_holiday(current_date)
            if not is_holiday and current_time < REGULAR_START:
                return datetime.combine(current_date, REGULAR_START, tzinfo=IST)

        # Advance to subsequent days
        candidate_date = current_date + timedelta(days=1)
        while True:
            if not self.is_weekend(candidate_date):
                is_holiday, _ = self.is_trading_holiday(candidate_date)
                if not is_holiday:
                    return datetime.combine(candidate_date, REGULAR_START, tzinfo=IST)
            candidate_date += timedelta(days=1)

    def get_market_status(self, dt: datetime | None = None) -> MarketStatus:
        """Evaluate full MarketStatus for the given or current datetime."""
        if dt is None:
            dt = self.get_ist_now()
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        else:
            dt = dt.astimezone(IST)

        session = self.get_session(dt)
        is_open = session == "regular_trading"
        _, holiday_name = self.is_trading_holiday(dt)
        next_open = self.get_next_open(dt)

        return MarketStatus(
            exchange="NSE",
            is_open=is_open,
            session_type=session,
            current_time_ist=dt.isoformat(),
            next_session_open_ist=next_open.isoformat(),
            holiday_name=holiday_name,
        )
