from datetime import date, datetime
from decimal import Decimal

from tests.fixtures.factories import jan

from finscope.domain.instrument import Instrument
from finscope.market_data.errors import InvalidDateRangeError, MarketDataError
from finscope.market_data.models.price_point import PricePoint
from finscope.market_data.models.price_series import PriceSeries
from finscope.market_data.providers.in_memory import InMemoryPriceHistoryProvider
from finscope.market_data.providers.price_history_provider import (
    PriceHistoryProvider,
)


def make_provider(
    prices_by_instrument_id: dict[str, dict[int, str]],
) -> InMemoryPriceHistoryProvider:
    """Build an in-memory provider; keys are January 2024 day numbers."""
    return InMemoryPriceHistoryProvider(
        {
            instrument_id: [
                PricePoint(jan(day), Decimal(price)) for day, price in prices.items()
            ]
            for instrument_id, prices in prices_by_instrument_id.items()
        }
    )


class SpyProvider:
    """Wraps a provider and records every call as (instrument ids, start, end)."""

    def __init__(self, inner: PriceHistoryProvider) -> None:
        self._inner = inner
        self.calls: list[tuple[tuple[str, ...], date, date]] = []

    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        self.calls.append(
            (tuple(instrument.id for instrument in instruments), start_date, end_date)
        )
        return self._inner.get_price_series(instruments, start_date, end_date)


class FailingProvider:
    def __init__(self, message: str = "provider unavailable") -> None:
        self._message = message

    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        raise MarketDataError(self._message)


class FixedCalendar:
    """Expects exactly the given January 2024 day numbers."""

    def __init__(self, *days: int) -> None:
        self._dates = tuple(jan(day) for day in days)

    def expected_dates(self, start_date: date, end_date: date) -> tuple[date, ...]:
        if start_date > end_date:
            raise InvalidDateRangeError(start_date, end_date)
        return tuple(day for day in self._dates if start_date <= day <= end_date)


class FakePriceStore:
    """In-memory PriceStore that records upserts as (provider, dates, fetched_at)."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, date], tuple[Decimal, str]] = {}
        self.upserts: list[tuple[str, tuple[date, ...], datetime]] = []

    def seed(
        self, instrument: Instrument, prices: dict[int, str], provider: str = "seed"
    ) -> None:
        for day, price in prices.items():
            self.rows[(instrument.id, jan(day))] = (Decimal(price), provider)

    def get_dates(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> frozenset[date]:
        return frozenset(
            day
            for (instrument_id, day) in self.rows
            if instrument_id == instrument.id and start_date <= day <= end_date
        )

    def upsert_series(
        self, series: PriceSeries, provider: str, fetched_at: datetime
    ) -> None:
        self.upserts.append(
            (provider, tuple(point.date for point in series.points), fetched_at)
        )
        for point in series.points:
            self.rows[(series.instrument.id, point.date)] = (
                point.adjusted_close,
                provider,
            )

    def get_series(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> PriceSeries | None:
        points = tuple(
            PricePoint(day, price)
            for (instrument_id, day), (price, _) in sorted(self.rows.items())
            if instrument_id == instrument.id and start_date <= day <= end_date
        )
        return PriceSeries(instrument=instrument, points=points) if points else None
