from datetime import date
from decimal import Decimal
from pathlib import Path
import re

import pytest

from src.finscope.market_data.errors import (
    InvalidDateRangeError,
    MarketDataError,
    PriceDataNotFoundError,
)
from src.finscope.market_data.providers.csv_provider import (
    CsvPriceHistoryProvider,
)
from tests.fixtures.factories import make_instrument


FIXTURE_DATA_DIR = Path(__file__).parents[2] / "fixtures" / "price_history"


def test_loads_fixture_csv_with_sorted_inclusive_decimal_values() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    provider = CsvPriceHistoryProvider(FIXTURE_DATA_DIR)

    result = provider.get_price_series(
        (instrument,),
        date(2024, 1, 2),
        date(2024, 1, 4),
    )

    assert result[0].instrument is instrument
    assert isinstance(result[0].points, tuple)
    assert [point.date for point in result[0].points] == [
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 4),
    ]
    assert [point.adjusted_close for point in result[0].points] == [
        Decimal("188.75"),
        Decimal("189.50"),
        Decimal("191.25"),
    ]


def test_multiple_csv_instruments_keep_input_order() -> None:
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    provider = CsvPriceHistoryProvider(FIXTURE_DATA_DIR)

    result = provider.get_price_series(
        (instrument_b, instrument_a),
        date(2024, 1, 2),
        date(2024, 1, 4),
    )

    assert [series.instrument for series in result] == [
        instrument_b,
        instrument_a,
    ]


def test_missing_csv_file_raises_price_data_not_found(tmp_path: Path) -> None:
    instrument = make_instrument("inst-a", symbol="MISSING")
    provider = CsvPriceHistoryProvider(tmp_path)

    with pytest.raises(PriceDataNotFoundError):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


def test_header_only_csv_raises_price_data_not_found(tmp_path: Path) -> None:
    instrument = make_instrument("inst-a", symbol="EMPTY")
    (tmp_path / "EMPTY.csv").write_text(
        "date,adjusted_close\n",
        encoding="utf-8",
    )
    provider = CsvPriceHistoryProvider(tmp_path)

    with pytest.raises(PriceDataNotFoundError):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


@pytest.mark.parametrize(
    ("content", "filename"),
    [
        pytest.param(
            "date,adjusted_close\nnot-a-date,10.00\n",
            "BAD_DATE.csv",
            id="bad-date",
        ),
        pytest.param(
            "date,adjusted_close\n2024-01-02,not-a-decimal\n",
            "BAD_DECIMAL.csv",
            id="bad-decimal",
        ),
        pytest.param(
            "date\n2024-01-02\n",
            "MISSING_COLUMN.csv",
            id="missing-column",
        ),
    ],
)
def test_malformed_csv_rows_report_filename_and_line_number(
    tmp_path: Path,
    content: str,
    filename: str,
) -> None:
    (tmp_path / filename).write_text(content, encoding="utf-8")
    instrument = make_instrument("inst-a", symbol=Path(filename).stem)
    provider = CsvPriceHistoryProvider(tmp_path)

    with pytest.raises(
        MarketDataError,
        match=re.escape(f"{filename} line 2"),
    ):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 1),
            date(2024, 1, 3),
        )


def test_start_after_end_raises_before_accessing_data_directory(
    tmp_path: Path,
) -> None:
    instrument = make_instrument("inst-a", symbol="AAA")
    missing_directory = tmp_path / "does-not-exist"
    provider = CsvPriceHistoryProvider(missing_directory)

    with pytest.raises(InvalidDateRangeError):
        provider.get_price_series(
            (instrument,),
            date(2024, 1, 3),
            date(2024, 1, 2),
        )
