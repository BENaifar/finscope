from datetime import date
from decimal import Decimal

import pytest

from src.finscope.domain.instrument import Instrument
from src.finscope.market_data.errors import (
    InvalidDateRangeError,
    PriceDataNotFoundError,
)
from src.finscope.market_data.models.price_point import PricePoint
from src.finscope.market_data.providers.in_memory import (
    InMemoryPriceHistoryProvider,
)
from tests.fixtures.factories import make_instrument


def test_returns_series_in_instrument_request_order() -> None:
    instrument_a = make_instrument("inst-a")
    instrument_b = make_instrument("inst-b")
    prices = {
        "inst-b": [PricePoint(date(2024, 1, 2), Decimal("20"))],
        "inst-a": [PricePoint(date(2024, 1, 2), Decimal("10"))],
    }
    provider = InMemoryPriceHistoryProvider(prices)

    result = provider.get_price_series(
        (instrument_a, instrument_b),
        date(2024, 1, 1),
        date(2024, 1, 3),
    )

    assert [series.instrument for series in result] == [
        instrument_a,
        instrument_b,
    ]


def test_applies_the_requested_date_range() -> None:
    instrument = make_instrument("inst-a")
    provider = InMemoryPriceHistoryProvider(
        {
            instrument.id: [
                PricePoint(date(2024, 1, 1), Decimal("101")),
                PricePoint(date(2024, 1, 2), Decimal("102")),
                PricePoint(date(2024, 1, 4), Decimal("104")),
                PricePoint(date(2024, 1, 5), Decimal("105")),
            ]
        }
    )

    result = provider.get_price_series(
        (instrument,),
        date(2024, 1, 2),
        date(2024, 1, 4),
    )

    assert [point.date for point in result[0].points] == [
        date(2024, 1, 2),
        date(2024, 1, 4),
    ]


def test_looks_up_prices_by_instrument_id_not_symbol() -> None:
    instrument = Instrument(
        id="instrument-id",
        symbol="different-symbol",
        name="Instrument",
    )
    provider = InMemoryPriceHistoryProvider(
        {"instrument-id": [PricePoint(date(2024, 1, 2), Decimal("102"))]}
    )

    result = provider.get_price_series(
        (instrument,),
        date(2024, 1, 1),
        date(2024, 1, 3),
    )

    assert result[0].instrument is instrument
    assert result[0].points[0].adjusted_close == Decimal("102")


def test_missing_instrument_data_fails_the_whole_call() -> None:
    instrument_a = make_instrument("inst-a")
    instrument_b = make_instrument("inst-b")
    provider = InMemoryPriceHistoryProvider(
        {
            instrument_a.id: [
                PricePoint(date(2024, 1, 2), Decimal("102")),
            ]
        }
    )

    with pytest.raises(PriceDataNotFoundError):
        provider.get_price_series(
            (instrument_a, instrument_b),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


def test_rejects_start_after_end() -> None:
    instrument = make_instrument("inst-a")
    provider = InMemoryPriceHistoryProvider({})

    with pytest.raises(InvalidDateRangeError):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 3),
            date(2024, 1, 2),
        )


def test_original_mapping_and_lists_can_be_mutated_without_changing_results() -> None:
    instrument = make_instrument("inst-a")
    original_points = [
        PricePoint(date(2024, 1, 2), Decimal("102")),
    ]
    original_mapping = {instrument.id: original_points}
    provider = InMemoryPriceHistoryProvider(original_mapping)
    original_points.append(PricePoint(date(2024, 1, 3), Decimal("103")))
    original_mapping[instrument.id] = [
        PricePoint(date(2024, 1, 2), Decimal("999")),
    ]

    result = provider.get_price_series(
        (instrument,),
        date(2024, 1, 1),
        date(2024, 1, 4),
    )

    assert [point.date for point in result[0].points] == [date(2024, 1, 2)]
    assert [point.adjusted_close for point in result[0].points] == [
        Decimal("102"),
    ]
