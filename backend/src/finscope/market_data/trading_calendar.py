from datetime import date
from typing import Protocol


class TradingCalendar(Protocol):
    def expected_dates(self, start_date: date, end_date: date) -> tuple[date, ...]:
        """Return every date prices should exist for, inclusive, ascending."""
        ...
