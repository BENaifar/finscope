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
from src.finscope.market_data.providers.yahoo_finance import (
    YahooFinancePriceHistoryProvider,
)
from tests.fixtures.factories import make_instrument


def test_converts_loader_floats_to_six_decimal_places() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    provider = YahooFinancePriceHistoryProvider(
        history_loader=lambda symbol, start, end: [
            (date(2024, 1, 2), 189.9499969482422),
        ]
    )

    result = provider.get_price_series(
        (instrument,),
        date(2024, 1, 1),
        date(2024, 1, 3),
    )

    assert result[0].points[0].adjusted_close == Decimal("189.949997")


def test_calls_loader_once_per_instrument_with_exact_arguments() -> None:
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    start_date = date(2024, 1, 2)
    end_date = date(2024, 1, 4)
    calls: list[tuple[str, date, date]] = []

    def history_loader(
        symbol: str,
        start: date,
        end: date,
    ) -> list[tuple[date, float]]:
        calls.append((symbol, start, end))
        return [(date(2024, 1, 2), 100.0)]

    provider = YahooFinancePriceHistoryProvider(history_loader)

    provider.get_price_series(
        (instrument_b, instrument_a),
        start_date,
        end_date,
    )

    assert calls == [
        ("BBB", start_date, end_date),
        ("AAA", start_date, end_date),
    ]


def test_sorts_unsorted_loader_output() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    provider = YahooFinancePriceHistoryProvider(
        history_loader=lambda symbol, start, end: [
            (date(2024, 1, 3), 103.0),
            (date(2024, 1, 1), 101.0),
            (date(2024, 1, 2), 102.0),
        ]
    )

    result = provider.get_price_series(
        (instrument,),
        date(2024, 1, 1),
        date(2024, 1, 3),
    )

    assert [point.date for point in result[0].points] == [
        date(2024, 1, 1),
        date(2024, 1, 2),
        date(2024, 1, 3),
    ]


def test_duplicate_loader_dates_raise_market_data_error() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    provider = YahooFinancePriceHistoryProvider(
        history_loader=lambda symbol, start, end: [
            (date(2024, 1, 2), 102.0),
            (date(2024, 1, 2), 103.0),
        ]
    )

    with pytest.raises(
        MarketDataError,
        match=re.escape("Duplicate price date 2024-01-02 for AAA"),
    ):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


def test_loader_exception_is_wrapped_with_original_cause() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    error = RuntimeError("loader failed")

    def history_loader(
        symbol: str,
        start: date,
        end: date,
    ) -> list[tuple[date, float]]:
        raise error

    provider = YahooFinancePriceHistoryProvider(history_loader)

    with pytest.raises(
        MarketDataError,
        match=re.escape("Yahoo Finance request failed for AAA"),
    ) as error_info:
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )

    assert error_info.value.__cause__ is error


def test_empty_loader_result_raises_price_data_not_found() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    provider = YahooFinancePriceHistoryProvider(
        history_loader=lambda symbol, start, end: []
    )

    with pytest.raises(PriceDataNotFoundError):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


def test_start_after_end_raises_without_calling_loader() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    calls: list[tuple[str, date, date]] = []

    def history_loader(
        symbol: str,
        start: date,
        end: date,
    ) -> list[tuple[date, float]]:
        calls.append((symbol, start, end))
        return [(date(2024, 1, 2), 102.0)]

    provider = YahooFinancePriceHistoryProvider(history_loader)

    with pytest.raises(InvalidDateRangeError):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 3),
            date(2024, 1, 2),
        )

    assert calls == []
