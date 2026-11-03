from datetime import date, datetime
from typing import Protocol

from finscope.domain.instrument import Instrument
from finscope.market_data.models.price_series import PriceSeries


class PriceStore(Protocol):
    """Where fetched prices are kept. PricePointRepository satisfies this."""

    def get_dates(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> frozenset[date]:
        """Return the dates already stored for the instrument, inclusive."""
        ...

    def upsert_series(
        self, series: PriceSeries, provider: str, fetched_at: datetime
    ) -> None:
        """Store the series idempotently, recording which provider supplied it."""
        ...

    def get_series(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> PriceSeries | None:
        """Return the stored series for the range, or None if nothing is stored."""
        ...
