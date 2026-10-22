from typing import Any
from unittest.mock import create_autospec

import pytest

from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.analytics.services.performance_calculation_service import (
    PerformanceCalculationService,
)
from src.finscope.analytics.services.portfolio_analysis_engine import (
    PortfolioAnalysisEngine,
)
from src.finscope.analytics.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from src.finscope.domain.experiment_config import ExperimentConfig
from src.finscope.domain.instrument import Instrument
from src.finscope.domain.portfolio import Portfolio
from tests.fixtures.factories import (
    jan,
    make_config,
    make_instrument,
    make_performance_result,
    make_portfolio,
    make_running_run,
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
def performance_result() -> PerformanceResult:
    return make_performance_result()


@pytest.fixture
def running_run():
    return make_running_run()
