# providers/series_builder.py
from collections.abc import Iterable
from datetime import date

from finscope.domain.instrument import Instrument
from finscope.market_data.errors import (
    InvalidDateRangeError,
    MarketDataError,
    PriceDataNotFoundError,
)
from finscope.market_data.models.price_series import PricePoint, PriceSeries


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise InvalidDateRangeError(start_date, end_date)


def build_price_series(
    instrument: Instrument,
    points: Iterable[PricePoint],
    start_date: date,
    end_date: date,
) -> PriceSeries:
    """Filter to the range, reject duplicate dates, sort, and wrap in a PriceSeries."""
    by_date: dict[date, PricePoint] = {}
    for point in points:
        if not (start_date <= point.date <= end_date):
            continue
        if point.date in by_date:
            raise MarketDataError(
                f"Duplicate price date {point.date} for {instrument.symbol}"
            )
        by_date[point.date] = point

    if not by_date:
        raise PriceDataNotFoundError(instrument, start_date, end_date)

    return PriceSeries(
        instrument=instrument,
        points=tuple(by_date[d] for d in sorted(by_date)),
    )