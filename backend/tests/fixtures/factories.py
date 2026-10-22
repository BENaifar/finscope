from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from src.finscope.domain.experiment_config import ExperimentConfig
from src.finscope.domain.instrument import Instrument
from src.finscope.domain.portfolio import Portfolio
from src.finscope.domain.portfolio_allocation import PortfolioAllocation
from src.finscope.market_data.models.price_point import PricePoint
from src.finscope.market_data.models.price_series import PriceSeries


def jan(day: int) -> date:
    return date(2024, 1, day)


def make_instrument(
    instrument_id: str,
    symbol: str | None = None,
) -> Instrument:
    return Instrument(
        id=instrument_id,
        symbol=symbol if symbol is not None else instrument_id,
        name=instrument_id,
    )


def make_portfolio(
    allocations: Sequence[tuple[Instrument, str]],
    initial_capital: str = "1000",
    portfolio_id: str = "test-portfolio",
) -> Portfolio:
    return Portfolio(
        id=portfolio_id,
        initial_capital=Decimal(initial_capital),
        allocations=tuple(
            PortfolioAllocation(
                instrument=instrument,
                weight=Decimal(weight),
            )
            for instrument, weight in allocations
        ),
    )


def make_config(
    start: date,
    end: date,
    portfolio_id: str = "test-portfolio",
) -> ExperimentConfig:
    return ExperimentConfig(
        portfolio_id=portfolio_id,
        start_date=start,
        end_date=end,
    )


def make_price_series(
    instrument: Instrument,
    prices: Mapping[date, str],
) -> PriceSeries:
    return PriceSeries(
        instrument=instrument,
        points=tuple(
            PricePoint(date=price_date, adjusted_close=Decimal(price))
            for price_date, price in sorted(prices.items())
        ),
    )
