# providers/in_memory.py
from collections.abc import Mapping, Sequence
from datetime import date

from src.finscope.domain.instrument import Instrument
from src.finscope.market_data.models.price_series import PricePoint, PriceSeries
from src.finscope.market_data.providers.series_builder import (
    build_price_series,
    validate_date_range,
)


class InMemoryPriceHistoryProvider:
    """Serves prices from a dict keyed by instrument id. Meant for tests and fixtures."""

    def __init__(self, prices_by_instrument_id: Mapping[str, Sequence[PricePoint]]) -> None:
        self._prices = {key: tuple(points) for key, points in prices_by_instrument_id.items()}

    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        validate_date_range(start_date, end_date)
        return tuple(
            build_price_series(
                instrument, self._prices.get(instrument.id, ()), start_date, end_date
            )
            for instrument in instruments
        )