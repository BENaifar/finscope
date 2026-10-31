from datetime import datetime, tzinfo
from typing import Any
from unittest.mock import create_autospec

import pytest
from tests.fixtures.factories import (
    FROZEN_NOW,
    jan,
    make_config,
    make_instrument,
    make_pending_run,
    make_performance_result,
    make_portfolio,
    make_price_series,
    make_running_run,
)

from finscope.analytics.models.performance_result import PerformanceResult
from finscope.analytics.services import experiment_orchestration_service
from finscope.analytics.services.experiment_execution_service import (
    ExperimentExecutionService,
)
from finscope.analytics.services.performance_calculation_service import (
    PerformanceCalculationService,
)
from finscope.analytics.services.portfolio_analysis_engine import (
    PortfolioAnalysisEngine,
)
from finscope.analytics.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from finscope.domain.experiment_config import ExperimentConfig
from finscope.domain.experiment_run import ExperimentRun
from finscope.domain.instrument import Instrument
from finscope.domain.portfolio import Portfolio
from finscope.market_data.models.price_series import PriceSeries
from finscope.market_data.providers.price_history_provider import (
    PriceHistoryProvider,
)


@pytest.fixture
def valuation_service() -> PortfolioValuationService:
    return PortfolioValuationService()


@pytest.fixture
def instrument_a() -> Instrument:
    return make_instrument("inst-a")


@pytest.fixture
def instrument_b() -> Instrument:
    return make_instrument("inst-b")


@pytest.fixture
def default_config() -> ExperimentConfig:
    return make_config(jan(1), jan(31))


@pytest.fixture
def single_asset_portfolio(instrument_a: Instrument) -> Portfolio:
    return make_portfolio(((instrument_a, "1.0"),))


@pytest.fixture
def two_asset_portfolio(
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> Portfolio:
    return make_portfolio(
        ((instrument_a, "0.6"), (instrument_b, "0.4")),
    )


@pytest.fixture
def valuation_spy() -> Any:
    return create_autospec(PortfolioValuationService, instance=True)


@pytest.fixture
def performance_spy() -> Any:
    return create_autospec(PerformanceCalculationService, instance=True)


@pytest.fixture
def analysis_engine() -> PortfolioAnalysisEngine:
    return PortfolioAnalysisEngine()


@pytest.fixture
def analysis_engine_spy() -> Any:
    return create_autospec(PortfolioAnalysisEngine, instance=True)


@pytest.fixture
def performance_result() -> PerformanceResult:
    return make_performance_result()


@pytest.fixture
def running_run():
    return make_running_run()


@pytest.fixture
def frozen_now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            return FROZEN_NOW

    monkeypatch.setattr(experiment_orchestration_service, "datetime", FrozenDateTime)
    return FROZEN_NOW


@pytest.fixture
def provider_spy() -> Any:
    return create_autospec(PriceHistoryProvider, instance=True)


@pytest.fixture
def execution_spy() -> Any:
    return create_autospec(ExperimentExecutionService, instance=True)


@pytest.fixture
def real_execution_service() -> ExperimentExecutionService:
    return ExperimentExecutionService(PortfolioAnalysisEngine())


@pytest.fixture
def orchestration_portfolio(
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> Portfolio:
    return make_portfolio(
        ((instrument_a, "0.5"), (instrument_b, "0.5")),
        initial_capital="1000",
        portfolio_id="test-portfolio",
    )


@pytest.fixture
def orchestration_price_series(
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> tuple[PriceSeries, ...]:
    return (
        make_price_series(
            instrument_a,
            {jan(1): "100", jan(2): "200", jan(3): "100"},
        ),
        make_price_series(
            instrument_b,
            {jan(1): "100", jan(2): "100", jan(3): "50"},
        ),
    )


@pytest.fixture
def pending_run() -> ExperimentRun:
    return make_pending_run()
