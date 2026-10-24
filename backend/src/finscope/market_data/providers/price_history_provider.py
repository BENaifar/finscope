
from datetime import date
from typing import Protocol

from src.finscope.domain.instrument import Instrument
from src.finscope.market_data.models.price_series import PriceSeries


class PriceHistoryProvider(Protocol):
    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        """Return historical adjusted closes for the requested instruments.

        Contract:
        - One PriceSeries per instrument, in the same order as `instruments`.
        - Points are sorted by date ascending, unique per date, and restricted
          to start_date <= date <= end_date (both inclusive).
        - Raises InvalidDateRangeError if start_date > end_date.
        - Raises PriceDataNotFoundError if an instrument has no data in range.
        - Raises MarketDataError (or a subclass) for any other provider failure.
        """
        ...
