from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from finscope.domain.instrument import Instrument
from finscope.market_data.coverage import find_missing_dates
from finscope.market_data.errors import (
    IncompleteMarketDataError,
    PriceDataNotFoundError,
)
from finscope.market_data.models.price_series import PriceSeries
from finscope.market_data.price_store import PriceStore
from finscope.market_data.providers.price_history_provider import (
    PriceHistoryProvider,
)
from finscope.market_data.trading_calendar import TradingCalendar


@dataclass(frozen=True)
class ProviderSource:
    """A provider plus the name recorded as the provenance of its prices."""

    name: str
    provider: PriceHistoryProvider


def _utc_now() -> datetime:
    return datetime.now(UTC)


class MarketDataService:
    """Serve price series from the store, filling genuine gaps from providers.

    Implements PriceHistoryProvider, so it can replace a provider anywhere one
    is expected. The caller owns the transaction: this service never commits.

    Rules:
    - Expected dates come from the trading calendar, so weekends and exchange
      holidays are never gaps.
    - Providers are tried in order, one instrument at a time, and only for the
      range between the first and last missing date.
    - Only dates that are still missing are stored; existing prices and their
      provenance are never overwritten, and dates the calendar does not expect
      are ignored.
    - A provider with no data (PriceDataNotFoundError) is skipped. Any other
      provider failure propagates immediately; it is not hidden by a fallback.
    - Missing dates before the first date any source has a price for are
      treated as "not yet trading" (e.g. before a listing) and tolerated.
      Every other missing date raises IncompleteMarketDataError. Nothing is
      ever forward-filled.
    """

    def __init__(
        self,
        store: PriceStore,
        calendar: TradingCalendar,
        sources: tuple[ProviderSource, ...],
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._store = store
        self._calendar = calendar
        self._sources = sources
        self._clock = clock

    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        expected = self._calendar.expected_dates(start_date, end_date)
        return tuple(
            self._get_series(instrument, start_date, end_date, expected)
            for instrument in instruments
        )

    def _get_series(
        self,
        instrument: Instrument,
        start_date: date,
        end_date: date,
        expected: tuple[date, ...],
    ) -> PriceSeries:
        known = set(self._store.get_dates(instrument, start_date, end_date))
        missing = find_missing_dates(expected, known)

        for source in self._sources:
            if not missing:
                break
            known |= self._fill_from(source, instrument, missing)
            missing = find_missing_dates(missing, known)

        if not known:
            raise PriceDataNotFoundError(instrument, start_date, end_date)

        first_known = min(known)
        unresolved = tuple(day for day in missing if day > first_known)
        if unresolved:
            raise IncompleteMarketDataError(instrument, unresolved)

        series = self._store.get_series(instrument, start_date, end_date)
        if series is None:
            raise PriceDataNotFoundError(instrument, start_date, end_date)
        return series

    def _fill_from(
        self,
        source: ProviderSource,
        instrument: Instrument,
        missing: tuple[date, ...],
    ) -> set[date]:
        try:
            fetched = source.provider.get_price_series(
                (instrument,), missing[0], missing[-1]
            )[0]
        except PriceDataNotFoundError:
            return set()

        wanted = set(missing)
        points = tuple(point for point in fetched.points if point.date in wanted)
        if not points:
            return set()

        self._store.upsert_series(
            PriceSeries(instrument=instrument, points=points),
            source.name,
            self._clock(),
        )
        return {point.date for point in points}
