# errors.py
from datetime import date

from finscope.domain.instrument import Instrument


class MarketDataError(Exception):
    """Base class for all market data failures."""


class InvalidDateRangeError(MarketDataError):
    def __init__(self, start_date: date, end_date: date) -> None:
        super().__init__(f"start_date {start_date} is after end_date {end_date}")


class PriceDataNotFoundError(MarketDataError):
    def __init__(self, instrument: Instrument, start_date: date, end_date: date) -> None:
        super().__init__(
            f"No price data for {instrument.symbol} ({instrument.id}) "
            f"between {start_date} and {end_date}"
        )