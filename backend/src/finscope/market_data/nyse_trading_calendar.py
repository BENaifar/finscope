from datetime import date

import exchange_calendars as xcals
import pandas as pd

from finscope.market_data.errors import CalendarRangeError, InvalidDateRangeError

_CALENDAR_START = pd.Timestamp("1990-01-01")


class NyseTradingCalendar:
    """NYSE sessions (weekends, holidays and special closures excluded)."""

    def __init__(self) -> None:
        self._calendar = xcals.get_calendar("XNYS", start=_CALENDAR_START)

    def expected_dates(self, start_date: date, end_date: date) -> tuple[date, ...]:
        if start_date > end_date:
            raise InvalidDateRangeError(start_date, end_date)

        first = self._calendar.first_session.date()
        last = self._calendar.last_session.date()
        if start_date < first or end_date > last:
            raise CalendarRangeError(start_date, end_date, first, last)

        sessions = self._calendar.sessions_in_range(
            pd.Timestamp(start_date), pd.Timestamp(end_date)
        )
        return tuple(session.date() for session in sessions)
