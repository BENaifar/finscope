# providers/csv_provider.py
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.finscope.domain.instrument import Instrument
from src.finscope.market_data.errors import MarketDataError, PriceDataNotFoundError
from src.finscope.market_data.models.price_series import PricePoint, PriceSeries
from src.finscope.market_data.providers.series_builder import (
    build_price_series,
    validate_date_range,
)


class CsvPriceHistoryProvider:
    """Reads <data_dir>/<symbol>.csv with columns: date (ISO), adjusted_close."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        validate_date_range(start_date, end_date)
        return tuple(
            self._load_series(instrument, start_date, end_date) for instrument in instruments
        )

    def _load_series(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> PriceSeries:
        path = self._data_dir / f"{instrument.symbol}.csv"
        if not path.is_file():
            raise PriceDataNotFoundError(instrument, start_date, end_date)

        points: list[PricePoint] = []
        try:
            with path.open(newline="", encoding="utf-8") as file:
                for line_number, row in enumerate(csv.DictReader(file), start=2):
                    try:
                        points.append(
                            PricePoint(
                                date=date.fromisoformat(row["date"]),
                                adjusted_close=Decimal(row["adjusted_close"]),
                            )
                        )
                    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
                        raise MarketDataError(
                            f"{path.name} line {line_number}: invalid row {row!r}"
                        ) from error
        except MarketDataError:
            raise
        except (OSError, UnicodeError, csv.Error) as error:
            raise MarketDataError(
                f"Could not read price data from {path.name}"
            ) from error

        return build_price_series(instrument, points, start_date, end_date)