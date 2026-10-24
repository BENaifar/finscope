import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.analytics.services.experiment_execution_service import (
    ExperimentExecutionService,
)
from src.finscope.analytics.services.experiment_orchestration_service import (
    ExperimentOrchestrationService,
)
from src.finscope.analytics.services.portfolio_analysis_engine import (
    PortfolioAnalysisEngine,
)
from src.finscope.domain.experiment_run import ExperimentRun, ExperimentStatus
from src.finscope.domain.instrument import Instrument
from src.finscope.domain.portfolio import Portfolio
from src.finscope.market_data.errors import MarketDataError
from src.finscope.market_data.models.price_series import PriceSeries
from tests.fixtures.factories import (
    FROZEN_NOW,
    make_completed_run,
    make_failed_run,
    make_portfolio,
    make_running_run,
)


def test_orchestrate_returns_completed_run_with_result(
    frozen_now: datetime,
    provider_spy: Any,
    real_execution_service: ExperimentExecutionService,
    orchestration_portfolio: Portfolio,
    orchestration_price_series: tuple[PriceSeries, ...],
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.return_value = orchestration_price_series
    service = ExperimentOrchestrationService(provider_spy, real_execution_service)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    assert result.status is ExperimentStatus.COMPLETED
    assert isinstance(result.result, PerformanceResult)
    assert result.result.metrics.total_return == pytest.approx(-0.25)
    assert result.error_message is None


def test_orchestrate_preserves_run_identity_and_stamps_start_and_finish_times(
    frozen_now: datetime,
    provider_spy: Any,
    real_execution_service: ExperimentExecutionService,
    orchestration_portfolio: Portfolio,
    orchestration_price_series: tuple[PriceSeries, ...],
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.return_value = orchestration_price_series
    service = ExperimentOrchestrationService(provider_spy, real_execution_service)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    assert result.id == pending_run.id
    assert result.config is pending_run.config
    assert result.created_at == pending_run.created_at
    assert result.started_at == FROZEN_NOW
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.finished_at.utcoffset() is not None
    assert result.finished_at >= result.started_at


def test_orchestrate_does_not_mutate_the_original_run(
    frozen_now: datetime,
    provider_spy: Any,
    real_execution_service: ExperimentExecutionService,
    orchestration_portfolio: Portfolio,
    orchestration_price_series: tuple[PriceSeries, ...],
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.return_value = orchestration_price_series
    service = ExperimentOrchestrationService(provider_spy, real_execution_service)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    assert pending_run.status is ExperimentStatus.PENDING
    assert pending_run.started_at is None
    assert result is not pending_run


def test_orchestrate_requests_prices_for_portfolio_instruments_and_config_period(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    orchestration_portfolio: Portfolio,
    pending_run: ExperimentRun,
) -> None:
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    service.orchestrate(orchestration_portfolio, pending_run)

    provider_spy.get_price_series.assert_called_once_with(
        instruments=orchestration_portfolio.instruments,
        start_date=pending_run.config.start_date,
        end_date=pending_run.config.end_date,
    )


def test_orchestrate_executes_started_run_with_provider_prices(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    orchestration_portfolio: Portfolio,
    orchestration_price_series: tuple[PriceSeries, ...],
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.return_value = orchestration_price_series
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    service.orchestrate(orchestration_portfolio, pending_run)

    execution_spy.execute.assert_called_once()
    call_kwargs = execution_spy.execute.call_args.kwargs
    running_run = call_kwargs["running_run"]
    assert running_run.status is ExperimentStatus.RUNNING
    assert running_run.started_at == FROZEN_NOW
    assert running_run.id == pending_run.id
    assert call_kwargs["portfolio"] is orchestration_portfolio
    assert call_kwargs["price_series"] is orchestration_price_series


def test_orchestrate_returns_execution_service_result(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    orchestration_portfolio: Portfolio,
    orchestration_price_series: tuple[PriceSeries, ...],
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.return_value = orchestration_price_series
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    assert result is execution_spy.execute.return_value


def test_orchestrate_returns_failed_run_when_provider_raises_market_data_error(
    frozen_now: datetime,
    provider_spy: Any,
    real_execution_service: ExperimentExecutionService,
    orchestration_portfolio: Portfolio,
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.side_effect = MarketDataError(
        "price source unavailable"
    )
    service = ExperimentOrchestrationService(provider_spy, real_execution_service)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    assert result.status is ExperimentStatus.FAILED
    assert result.error_message == "price source unavailable"
    assert result.result is None
    assert result.id == pending_run.id
    assert result.started_at == FROZEN_NOW


@pytest.mark.parametrize(
    ("raised_message", "expected_error_message"),
    [
        pytest.param(
            "price source unavailable",
            "price source unavailable",
            id="message-present",
        ),
        pytest.param("", "MarketDataError", id="empty-message"),
    ],
)
def test_orchestrate_hands_provider_failure_to_fail_run(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    orchestration_portfolio: Portfolio,
    pending_run: ExperimentRun,
    raised_message: str,
    expected_error_message: str,
) -> None:
    provider_spy.get_price_series.side_effect = MarketDataError(raised_message)
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    execution_spy.fail_run.assert_called_once()
    call_kwargs = execution_spy.fail_run.call_args.kwargs
    assert call_kwargs["running_run"].status is ExperimentStatus.RUNNING
    assert call_kwargs["running_run"].started_at == FROZEN_NOW
    assert call_kwargs["error_message"] == expected_error_message
    execution_spy.execute.assert_not_called()
    assert result is execution_spy.fail_run.return_value


def test_orchestrate_returns_failed_run_when_analysis_engine_raises(
    frozen_now: datetime,
    provider_spy: Any,
    analysis_engine_spy: Any,
    orchestration_portfolio: Portfolio,
    orchestration_price_series: tuple[PriceSeries, ...],
    pending_run: ExperimentRun,
) -> None:
    provider_spy.get_price_series.return_value = orchestration_price_series
    analysis_engine_spy.analyze.side_effect = RuntimeError("engine exploded")
    real_service = ExperimentExecutionService(analysis_engine_spy)
    service = ExperimentOrchestrationService(provider_spy, real_service)

    result = service.orchestrate(orchestration_portfolio, pending_run)

    assert result.status is ExperimentStatus.FAILED
    assert result.result is None
    assert result.error_message == "engine exploded"


def test_orchestrate_rejects_portfolio_not_matching_run(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    instrument_a: Instrument,
    orchestration_portfolio: Portfolio,
    pending_run: ExperimentRun,
) -> None:
    other_portfolio = make_portfolio(
        ((instrument_a, "1.0"),),
        portfolio_id="other",
    )
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "The portfolio and experiment run's portfolio do not match"
        ),
    ):
        service.orchestrate(other_portfolio, pending_run)

    provider_spy.get_price_series.assert_not_called()
    execution_spy.execute.assert_not_called()
    execution_spy.fail_run.assert_not_called()


@pytest.mark.parametrize(
    "run_factory",
    [
        pytest.param(make_running_run, id="running"),
        pytest.param(make_completed_run, id="completed"),
        pytest.param(make_failed_run, id="failed"),
    ],
)
def test_orchestrate_rejects_runs_that_are_not_pending(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    orchestration_portfolio: Portfolio,
    run_factory: Callable[[], ExperimentRun],
) -> None:
    run = run_factory()
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    with pytest.raises(
        ValueError,
        match=re.escape("only a pending run can be started"),
    ):
        service.orchestrate(orchestration_portfolio, run)

    provider_spy.get_price_series.assert_not_called()
    execution_spy.execute.assert_not_called()
    execution_spy.fail_run.assert_not_called()


@pytest.mark.parametrize(
    "provider_result",
    [
        pytest.param([], id="list"),
        pytest.param("not-a-tuple", id="string"),
        pytest.param(None, id="none"),
    ],
)
def test_orchestrate_propagates_type_error_for_invalid_provider_result(
    frozen_now: datetime,
    provider_spy: Any,
    real_execution_service: ExperimentExecutionService,
    orchestration_portfolio: Portfolio,
    pending_run: ExperimentRun,
    provider_result: Any,
) -> None:
    provider_spy.get_price_series.return_value = provider_result
    service = ExperimentOrchestrationService(provider_spy, real_execution_service)

    with pytest.raises(TypeError):
        service.orchestrate(orchestration_portfolio, pending_run)


@pytest.mark.parametrize(
    ("argument_name", "invalid_value", "message"),
    [
        pytest.param(
            "portfolio",
            "x",
            "portfolio must be a Portfolio",
            id="portfolio-not-a-portfolio",
        ),
        pytest.param(
            "run",
            None,
            "run must be an ExperimentRun",
            id="run-not-an-experiment-run",
        ),
    ],
)
def test_orchestrate_rejects_invalid_argument_types(
    frozen_now: datetime,
    provider_spy: Any,
    execution_spy: Any,
    orchestration_portfolio: Portfolio,
    pending_run: ExperimentRun,
    argument_name: str,
    invalid_value: Any,
    message: str,
) -> None:
    arguments: dict[str, Any] = {
        "portfolio": orchestration_portfolio,
        "run": pending_run,
    }
    arguments[argument_name] = invalid_value
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    with pytest.raises(TypeError, match=re.escape(message)):
        service.orchestrate(**arguments)

    provider_spy.get_price_series.assert_not_called()

def test_orchestrate_propagates_unexpected_provider_exception(
    provider_spy,
    execution_spy,
    orchestration_portfolio,
    pending_run,
):
    provider_spy.get_price_series.side_effect = RuntimeError(
        "unexpected provider bug"
    )
    service = ExperimentOrchestrationService(provider_spy, execution_spy)

    with pytest.raises(RuntimeError, match="unexpected provider bug"):
        service.orchestrate(orchestration_portfolio, pending_run)

    execution_spy.execute.assert_not_called()
    execution_spy.fail_run.assert_not_called()