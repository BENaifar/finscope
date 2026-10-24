from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from src.finscope.analytics.models.performance_metrics import PerformanceMetrics
from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.analytics.models.portfolio_value_point import PortfolioValuePoint
from src.finscope.domain.experiment_config import ExperimentConfig
from src.finscope.domain.experiment_run import ExperimentRun, ExperimentStatus
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


def make_value_points(*values: str) -> tuple[PortfolioValuePoint, ...]:
    return tuple(
        PortfolioValuePoint(
            valuation_date=jan(day),
            total_value=Decimal(value),
        )
        for day, value in enumerate(values, start=1)
    )


def make_performance_metrics(**overrides: Any) -> PerformanceMetrics:
    values: dict[str, Any] = {
        "initial_value": 1000.0,
        "final_value": 1000.0,
        "pnl": 0.0,
        "total_return": 0.0,
        "maximum_drawdown": 0.0,
        "maximum_drawdown_peak_date": jan(1),
        "maximum_drawdown_trough_date": jan(1),
        "best_daily_return": 0.0,
        "best_daily_return_date": jan(2),
        "highest_portfolio_value_date": jan(1),
        "lowest_portfolio_value_date": jan(1),
    }
    values.update(overrides)
    return PerformanceMetrics(**values)


def make_performance_result() -> PerformanceResult:
    value_points = make_value_points("1000", "1100")
    return PerformanceResult(
        value_points=value_points,
        metrics=make_performance_metrics(),
        from_date=value_points[0].valuation_date,
        to_date=value_points[-1].valuation_date,
    )


def make_experiment_run(**overrides: Any) -> ExperimentRun:
    values: dict[str, Any] = {
        "id": "run-1",
        "config": make_config(jan(1), jan(31)),
        "created_at": datetime(2024, 2, 1, 9, 0, tzinfo=timezone.utc),
        "started_at": None,
        "finished_at": None,
        "status": ExperimentStatus.PENDING,
        "result": None,
        "error_message": None,
    }
    values.update(overrides)
    return ExperimentRun(**values)

def make_experiment_running_run(**overrides: Any) -> ExperimentRun:
    values: dict[str, Any] = {
        "id": "run-1",
        "config": make_config(jan(1), jan(31)),
        "created_at": datetime(2024, 2, 1, 9, 0, tzinfo=timezone.utc),
        "started_at": datetime(2024, 2, 1, 9, 1, tzinfo=timezone.utc),
        "finished_at": None,
        "status": ExperimentStatus.RUNNING,
        "result": None,
        "error_message": None,
    }
    values.update(overrides)
    return ExperimentRun(**values)


def ts(minute: int) -> datetime:
    return datetime(2024, 2, 1, 9, minute, tzinfo=timezone.utc)


FROZEN_NOW = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)


def make_pending_run() -> ExperimentRun:
    return ExperimentRun(
        id="run-1",
        config=make_config(jan(1), jan(31)),
        created_at=ts(0),
        started_at=None,
        finished_at=None,
        status=ExperimentStatus.PENDING,
    )


def make_running_run() -> ExperimentRun:
    return ExperimentRun(
        id="run-1",
        config=make_config(jan(1), jan(31)),
        created_at=ts(0),
        started_at=ts(1),
        finished_at=None,
        status=ExperimentStatus.RUNNING,
    )


def make_completed_run() -> ExperimentRun:
    return ExperimentRun(
        id="run-1",
        config=make_config(jan(1), jan(31)),
        created_at=ts(0),
        started_at=ts(1),
        finished_at=ts(5),
        status=ExperimentStatus.COMPLETED,
        result=make_performance_result(),
    )


def make_failed_run() -> ExperimentRun:
    return ExperimentRun(
        id="run-1",
        config=make_config(jan(1), jan(31)),
        created_at=ts(0),
        started_at=ts(1),
        finished_at=ts(5),
        status=ExperimentStatus.FAILED,
        error_message="boom",
    )
