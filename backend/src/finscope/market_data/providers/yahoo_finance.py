# providers/yahoo_finance.py
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from finscope.domain.instrument import Instrument
from finscope.market_data.errors import MarketDataError
from finscope.market_data.models.price_series import PricePoint, PriceSeries
from finscope.market_data.providers.series_builder import (
    build_price_series,
    validate_date_range,
)

HistoryLoader = Callable[[str, date, date], Sequence[tuple[date, float]]]

_PRICE_QUANTUM = Decimal("0.000001")


def load_yahoo_history(symbol: str, start_date: date, end_date: date) -> list[tuple[date, float]]:
    """Return (date, adjusted close) pairs. The only place that imports yfinance."""
    import yfinance as yf  # lazy: the dependency is only needed for live data

    frame = yf.Ticker(symbol).history(
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),  # Yahoo's end is exclusive
        auto_adjust=True,  # with this, "Close" is already split/dividend adjusted
        actions=False,
    )
    if frame.empty:
        return []
    closes = frame["Close"].dropna()
    return [(timestamp.date(), float(close)) for timestamp, close in closes.items()]


class YahooFinancePriceHistoryProvider:
    def __init__(self, history_loader: HistoryLoader = load_yahoo_history) -> None:
        self._history_loader = history_loader

    def get_price_series(
        self,
        instruments: tuple[Instrument, ...],
        start_date: date,
        end_date: date,
    ) -> tuple[PriceSeries, ...]:
        validate_date_range(start_date, end_date)
        return tuple(
            self._fetch_series(instrument, start_date, end_date) for instrument in instruments
        )

    def _fetch_series(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> PriceSeries:
        try:
            history = self._history_loader(instrument.symbol, start_date, end_date)
        except Exception as error:  # third-party I/O boundary: wrap whatever it raises
            raise MarketDataError(
                f"Yahoo Finance request failed for {instrument.symbol}"
            ) from error

        points:list = []

        for day, close in history:
            try:
                adjusted_close = Decimal(str(close)).quantize(_PRICE_QUANTUM)
            except InvalidOperation as error:
                raise MarketDataError(
                    f"Yahoo Finance returned an invalid price for {instrument.symbol}"
                ) from error
            if not adjusted_close.is_finite() or adjusted_close <= 0:
                raise MarketDataError(
                    f"Yahoo Finance returned an invalid price for {instrument.symbol}"
                )
            point = PricePoint(date=day, adjusted_close=adjusted_close)
            points.append(point)

        return build_price_series(instrument, points, start_date, end_date)