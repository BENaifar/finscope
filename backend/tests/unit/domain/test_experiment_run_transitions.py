import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from tests.fixtures.factories import (
    make_completed_run,
    make_experiment_run,
    make_failed_run,
    make_pending_run,
    ts,
)

from finscope.analytics.models.performance_result import PerformanceResult
from finscope.domain.experiment_run import ExperimentRun, ExperimentStatus


def test_start_accepts_start_time_equal_to_creation() -> None:
    run = make_experiment_run()

    running_run = run.start(ts(0))

    assert running_run.status is ExperimentStatus.RUNNING
    assert running_run.started_at == ts(0)

def test_complete_returns_completed_run_with_result_and_finish_time(
    running_run: ExperimentRun,
    performance_result: PerformanceResult,
) -> None:
    completed_run = running_run.complete(ts(5), performance_result)

    assert completed_run.status is ExperimentStatus.COMPLETED
    assert completed_run.result is performance_result
    assert completed_run.finished_at == ts(5)
    assert completed_run.error_message is None


def test_complete_preserves_identity_config_and_timestamps(
    running_run: ExperimentRun,
    performance_result: PerformanceResult,
) -> None:
    completed_run = running_run.complete(ts(5), performance_result)

    assert completed_run.id == running_run.id
    assert completed_run.config is running_run.config
    assert completed_run.created_at == ts(0)
    assert completed_run.started_at == ts(1)


def test_complete_does_not_mutate_the_original_run(
    running_run: ExperimentRun,
    performance_result: PerformanceResult,
) -> None:
    completed_run = running_run.complete(ts(5), performance_result)

    assert completed_run is not running_run
    assert running_run.status is ExperimentStatus.RUNNING
    assert running_run.result is None
    assert running_run.finished_at is None


@pytest.mark.parametrize(
    "run_factory",
    [
        pytest.param(make_pending_run, id="pending"),
        pytest.param(make_completed_run, id="completed"),
        pytest.param(make_failed_run, id="failed"),
    ],
)
def test_complete_rejects_runs_that_are_not_running(
    run_factory: Callable[[], ExperimentRun],
    performance_result: PerformanceResult,
) -> None:
    run = run_factory()

    with pytest.raises(
        ValueError,
        match=re.escape("only a running run can be completed"),
    ):
        run.complete(ts(10), performance_result)


@pytest.mark.parametrize(
    ("finished_at", "exception_type", "message"),
    [
        pytest.param(
            ts(0),
            ValueError,
            "started_at must not be after finished_at",
            id="before-start",
        ),
        pytest.param(
            datetime(2024, 2, 1, 9, 1),
            ValueError,
            "finished_at must be timezone-aware",
            id="naive-datetime",
        ),
        pytest.param(
            None,
            ValueError,
            "a completed or failed run must have start and finish times",
            id="none",
        ),
        pytest.param(
            "2024-02-01",
            TypeError,
            "finished_at must be a datetime or None",
            id="not-a-datetime",
        ),
    ],
)
def test_complete_rejects_invalid_finish_time(
    running_run: ExperimentRun,
    performance_result: PerformanceResult,
    finished_at: Any,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=re.escape(message)):
        running_run.complete(finished_at, performance_result)


@pytest.mark.parametrize(
    ("result", "exception_type", "message"),
    [
        pytest.param(
            None,
            ValueError,
            "a completed run must have a result",
            id="none",
        ),
        pytest.param(
            "not-a-result",
            TypeError,
            "result must be a PerformanceResult or None",
            id="not-a-performance-result",
        ),
    ],
)
def test_complete_rejects_invalid_result(
    running_run: ExperimentRun,
    result: Any,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=re.escape(message)):
        running_run.complete(ts(5), result)


def test_fail_returns_failed_run_with_error_and_finish_time(
    running_run: ExperimentRun,
) -> None:
    failed_run = running_run.fail(ts(5), "boom")

    assert failed_run.status is ExperimentStatus.FAILED
    assert failed_run.error_message == "boom"
    assert failed_run.finished_at == ts(5)
    assert failed_run.result is None


def test_fail_preserves_identity_config_and_timestamps(
    running_run: ExperimentRun,
) -> None:
    failed_run = running_run.fail(ts(5), "boom")

    assert failed_run.id == running_run.id
    assert failed_run.config is running_run.config
    assert failed_run.created_at == ts(0)
    assert failed_run.started_at == ts(1)


def test_fail_does_not_mutate_the_original_run(
    running_run: ExperimentRun,
) -> None:
    failed_run = running_run.fail(ts(5), "boom")

    assert failed_run is not running_run
    assert running_run.status is ExperimentStatus.RUNNING
    assert running_run.error_message is None
    assert running_run.finished_at is None


@pytest.mark.parametrize(
    "run_factory",
    [
        pytest.param(make_pending_run, id="pending"),
        pytest.param(make_completed_run, id="completed"),
        pytest.param(make_failed_run, id="failed"),
    ],
)
def test_fail_rejects_runs_that_are_not_running(
    run_factory: Callable[[], ExperimentRun],
) -> None:
    run = run_factory()

    with pytest.raises(
        ValueError,
        match=re.escape("only a running run can be failed"),
    ):
        run.fail(ts(10), "boom")


@pytest.mark.parametrize(
    ("finished_at", "exception_type", "message"),
    [
        pytest.param(
            ts(0),
            ValueError,
            "started_at must not be after finished_at",
            id="before-start",
        ),
        pytest.param(
            datetime(2024, 2, 1, 9, 1),
            ValueError,
            "finished_at must be timezone-aware",
            id="naive-datetime",
        ),
        pytest.param(
            None,
            ValueError,
            "a completed or failed run must have start and finish times",
            id="none",
        ),
        pytest.param(
            "2024-02-01",
            TypeError,
            "finished_at must be a datetime or None",
            id="not-a-datetime",
        ),
    ],
)
def test_fail_rejects_invalid_finish_time(
    running_run: ExperimentRun,
    finished_at: Any,
    exception_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(exception_type, match=re.escape(message)):
        running_run.fail(finished_at, "boom")

def test_complete_accepts_finish_time_equal_to_start_time(
    running_run: ExperimentRun,
    performance_result: PerformanceResult,
) -> None:
    completed_run = running_run.complete(ts(1), performance_result)

    assert completed_run.status is ExperimentStatus.COMPLETED
    assert completed_run.finished_at == ts(1)


def test_fail_accepts_finish_time_equal_to_start_time(
    running_run: ExperimentRun,
) -> None:
    failed_run = running_run.fail(ts(1), "boom")

    assert failed_run.status is ExperimentStatus.FAILED
    assert failed_run.finished_at == ts(1)


@pytest.mark.parametrize(
    ("error_message", "message"),
    [
        pytest.param(
            None,
            "a failed run must have an error message",
            id="none",
        ),
        pytest.param(
            "",
            "error_message must be non-empty when provided",
            id="empty",
        ),
        pytest.param(
            "   ",
            "error_message must be non-empty when provided",
            id="whitespace",
        ),
    ],
)

def test_fail_rejects_invalid_error_message(
    running_run: ExperimentRun,
    error_message: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        running_run.fail(ts(5), error_message)


def test_start_returns_a_new_running_run() -> None:
    run = make_experiment_run()
    started_at = datetime(2024, 2, 1, 9, 1, tzinfo=UTC)

    running_run = run.start(started_at)

    assert running_run is not run
    assert running_run.id == run.id
    assert running_run.config == run.config
    assert running_run.status is ExperimentStatus.RUNNING
    assert running_run.started_at == started_at
    assert running_run.finished_at is None
    assert running_run.result is None
    assert running_run.error_message is None


def test_start_does_not_modify_original_run() -> None:
    run = make_experiment_run()

    run.start(datetime(2024, 2, 1, 9, 1, tzinfo=UTC))

    assert run.status is ExperimentStatus.PENDING
    assert run.started_at is None


def test_start_rejects_non_pending_run() -> None:
    run = make_experiment_run(
        status=ExperimentStatus.RUNNING,
        started_at=datetime(2024, 2, 1, 9, 1, tzinfo=UTC),
    )

    with pytest.raises(
        ValueError,
        match="only a pending run can be started",
    ):
        run.start(datetime(2024, 2, 1, 9, 2, tzinfo=UTC))

def test_fail_rejects_non_string_error_message(
    running_run: ExperimentRun,
) -> None:
    with pytest.raises(
        TypeError,
        match=re.escape("error_message must be a string or None"),
    ):
        running_run.fail(ts(5), 123)  # type: ignore[arg-type]
