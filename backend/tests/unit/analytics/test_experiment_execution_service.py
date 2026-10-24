import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pytest

from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.analytics.services.experiment_execution_service import (
    ExperimentExecutionService,
)
from src.finscope.domain.experiment_run import ExperimentRun
from src.finscope.domain.experiment_run import ExperimentStatus
from src.finscope.domain.instrument import Instrument
from src.finscope.domain.portfolio import Portfolio
from tests.fixtures.factories import (
    jan,
    make_completed_run,
    make_experiment_running_run,
    make_experiment_run,
    make_failed_run,
    make_pending_run,
    make_portfolio,
    make_price_series,
)


def test_successful_execution_returns_completed_run_with_expected_result(
    analysis_engine_spy: Any,
    performance_result: PerformanceResult,
    instrument_a: Instrument,
    single_asset_portfolio: Portfolio,
) -> None:
    run = make_experiment_running_run(
        created_at=datetime(2024, 2, 1, 9, 0, tzinfo=timezone.utc),
    )
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    analysis_engine_spy.analyze.return_value = performance_result
    service = ExperimentExecutionService(analysis_engine_spy)

    result = service.execute(run, single_asset_portfolio, price_series)

    assert result.status is ExperimentStatus.COMPLETED
    assert result.result is performance_result
    analysis_engine_spy.analyze.assert_called_once_with(
        portfolio=single_asset_portfolio,
        config=run.config,
        price_series=price_series,
    )
    assert result.started_at is not None
    assert result.finished_at is not None
    assert result.created_at == run.created_at
    assert run.status is ExperimentStatus.RUNNING


def test_analysis_failure_returns_failed_run_with_error_message(
    analysis_engine_spy: Any,
    instrument_a: Instrument,
    single_asset_portfolio: Portfolio,
) -> None:
    run = make_experiment_running_run(
        created_at=datetime(2024, 2, 1, 9, 0, tzinfo=timezone.utc),
    )
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    analysis_engine_spy.analyze.side_effect = ValueError("analysis failed")
    service = ExperimentExecutionService(analysis_engine_spy)

    result = service.execute(run, single_asset_portfolio, price_series)

    assert result.status is ExperimentStatus.FAILED
    assert result.error_message == "analysis failed"


def test_mismatched_portfolio_is_rejected_before_execution_begins(
    analysis_engine_spy: Any,
    instrument_a: Instrument,
) -> None:
    run = make_experiment_running_run()
    portfolio = make_portfolio(
        ((instrument_a, "1.0"),),
        portfolio_id="other-portfolio",
    )
    service = ExperimentExecutionService(analysis_engine_spy)

    with pytest.raises(
        ValueError,
        match=re.escape("config portfolio_id must match the supplied portfolio"),
    ):
        service.execute(run, portfolio, ())

    analysis_engine_spy.analyze.assert_not_called()


def test_non_running_run_cannot_be_executed_again(
    analysis_engine_spy: Any,
    instrument_a: Instrument,
    single_asset_portfolio: Portfolio,
) -> None:
    run = make_experiment_run()
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    service = ExperimentExecutionService(analysis_engine_spy)

    with pytest.raises(
        ValueError,
        match=re.escape("Only a running run can be executed"),
    ):
        service.execute(run, single_asset_portfolio, price_series)

    analysis_engine_spy.analyze.assert_not_called()


@pytest.mark.parametrize(
    "run_factory",
    [
        pytest.param(make_pending_run, id="pending"),
        pytest.param(make_completed_run, id="completed"),
        pytest.param(make_failed_run, id="failed"),
    ],
)
def test_fail_run_rejects_runs_that_are_not_running(
    run_factory: Callable[[], ExperimentRun],
) -> None:
    service = ExperimentExecutionService()

    with pytest.raises(
        ValueError,
        match=re.escape("Only a running run can be failed"),
    ):
        service.fail_run(run_factory(), "failure")