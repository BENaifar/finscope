from datetime import date
from decimal import Decimal
import re

import pytest

from src.finscope.domain.instrument import Instrument
from src.finscope.market_data.errors import (
    InvalidDateRangeError,
    MarketDataError,
    PriceDataNotFoundError,
)
from src.finscope.market_data.models.price_point import PricePoint
from src.finscope.market_data.providers.series_builder import (
    build_price_series,
    validate_date_range,
)
from tests.fixtures.factories import make_instrument


def test_validate_date_range_accepts_equal_dates() -> None:
    validate_date_range(date(2024, 1, 2), date(2024, 1, 2))


def test_validate_date_range_rejects_start_after_end() -> None:
    with pytest.raises(InvalidDateRangeError):
        validate_date_range(date(2024, 1, 3), date(2024, 1, 2))


def test_build_price_series_filters_inclusively_and_sorts_points() -> None:
    instrument = make_instrument("inst-a")
    points = (
        PricePoint(date(2024, 1, 5), Decimal("105")),
        PricePoint(date(2024, 1, 4), Decimal("104")),
        PricePoint(date(2024, 1, 2), Decimal("102")),
        PricePoint(date(2024, 1, 1), Decimal("101")),
    )

    result = build_price_series(
        instrument,
        points,
        date(2024, 1, 2),
        date(2024, 1, 4),
    )

    assert result.instrument is instrument
    assert isinstance(result.points, tuple)
    assert [point.date for point in result.points] == [
        date(2024, 1, 2),
        date(2024, 1, 4),
    ]
    assert [point.adjusted_close for point in result.points] == [
        Decimal("102"),
        Decimal("104"),
    ]


def test_build_price_series_rejects_duplicate_dates_in_range() -> None:
    instrument = make_instrument("inst-a")
    points = (
        PricePoint(date(2024, 1, 2), Decimal("102")),
        PricePoint(date(2024, 1, 2), Decimal("103")),
    )

    with pytest.raises(
        MarketDataError,
        match=re.escape("Duplicate price date 2024-01-02 for inst-a"),
    ):
        build_price_series(
            instrument,
            points,
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


def test_build_price_series_raises_when_no_points_remain_in_range() -> None:
    instrument = make_instrument("inst-a")
    points = (PricePoint(date(2024, 1, 1), Decimal("101")),)

    with pytest.raises(PriceDataNotFoundError):
        build_price_series(
            instrument,
            points,
            date(2024, 1, 2),
            date(2024, 1, 3),
        )
