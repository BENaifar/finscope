import re
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from typing import Any

import pytest

from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.domain.experiment_config import ExperimentConfig
from src.finscope.domain.experiment_run import ExperimentRun, ExperimentStatus
from tests.fixtures.factories import (
    jan,
    make_config,
    make_experiment_run,
    make_performance_result,
)


def test_status_values_are_stable() -> None:
    assert {status.value for status in ExperimentStatus} == {
        "pending",
        "running",
        "completed",
        "failed",
    }
    assert ExperimentStatus("failed") is ExperimentStatus.FAILED


def test_defaults_to_pending_without_result_or_error() -> None:
    config = make_config(jan(1), jan(31))
    created_at = datetime(2024, 2, 1, 9, 0)

    run = ExperimentRun(
        id="run-1",
        config=config,
        created_at=created_at,
        started_at=None,
        finished_at=None,
    )

    assert run.status is ExperimentStatus.PENDING
    assert run.started_at is None
    assert run.finished_at is None
    assert run.result is None
    assert run.error_message is None


@pytest.mark.parametrize(
    ("status", "has_result", "error_message", "started_at", "finished_at"),
    [
        pytest.param(
            ExperimentStatus.PENDING,
            False,
            None,
            None,
            None,
            id="pending",
        ),
        pytest.param(
            ExperimentStatus.RUNNING,
            False,
            None,
            datetime(2024, 2, 1, 9, 1),
            None,
            id="running",
        ),
        pytest.param(
            ExperimentStatus.COMPLETED,
            True,
            None,
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            id="completed",
        ),
        pytest.param(
            ExperimentStatus.FAILED,
            False,
            "boom",
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            id="failed",
        ),
    ],
)
def test_accepts_valid_status_result_error_combinations(
    status: ExperimentStatus,
    has_result: bool,
    error_message: str | None,
    started_at: datetime | None,
    finished_at: datetime | None,
    performance_result: PerformanceResult,
) -> None:
    result = performance_result if has_result else None

    run = make_experiment_run(
        status=status,
        result=result,
        error_message=error_message,
        started_at=started_at,
        finished_at=finished_at,
    )

    assert run.id == "run-1"
    assert run.config == make_config(jan(1), jan(31))
    assert run.created_at == datetime(2024, 2, 1, 9, 0)
    assert run.started_at == started_at
    assert run.finished_at == finished_at
    assert run.status is status
    assert run.result is result
    assert run.error_message == error_message


@pytest.mark.parametrize(
    "invalid_id",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace"),
        pytest.param(None, id="none"),
        pytest.param(123, id="integer"),
    ],
)
def test_rejects_invalid_id(invalid_id: Any) -> None:
    with pytest.raises(ValueError, match=re.escape("id must be a non-empty string")):
        make_experiment_run(id=invalid_id)


@pytest.mark.parametrize(
    "invalid_config",
    [
        pytest.param(None, id="none"),
        pytest.param("config", id="string"),
    ],
)
def test_rejects_invalid_config_type(invalid_config: Any) -> None:
    with pytest.raises(
        TypeError,
        match=re.escape("config must be an ExperimentConfig"),
    ):
        make_experiment_run(config=invalid_config)


@pytest.mark.parametrize(
    "invalid_created_at",
    [
        pytest.param("2024-02-01", id="string"),
        pytest.param(date(2024, 2, 1), id="date-not-datetime"),
        pytest.param(None, id="none"),
    ],
)
def test_rejects_invalid_created_at_type(invalid_created_at: Any) -> None:
    with pytest.raises(TypeError, match=re.escape("created_at must be a datetime")):
        make_experiment_run(created_at=invalid_created_at)


@pytest.mark.parametrize(
    ("invalid_status", "started_at", "finished_at"),
    [
        pytest.param("pending", None, None, id="bare-string"),
        pytest.param(
            None,
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            id="none",
        ),
    ],
)
def test_rejects_invalid_status_type(
    invalid_status: Any,
    started_at: datetime | None,
    finished_at: datetime | None,
) -> None:
    with pytest.raises(
        TypeError,
        match=re.escape("status must be an ExperimentStatus"),
    ):
        make_experiment_run(
            status=invalid_status,
            started_at=started_at,
            finished_at=finished_at,
        )


@pytest.mark.parametrize(
    "invalid_result",
    [
        pytest.param("result", id="string"),
        pytest.param({}, id="dictionary"),
    ],
)
def test_rejects_invalid_result_type(invalid_result: Any) -> None:
    with pytest.raises(
        TypeError,
        match=re.escape("result must be a PerformanceResult or None"),
    ):
        make_experiment_run(
            status=ExperimentStatus.COMPLETED,
            result=invalid_result,
            started_at=datetime(2024, 2, 1, 9, 1),
            finished_at=datetime(2024, 2, 1, 9, 5),
        )


@pytest.mark.parametrize(
    "error_message",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace"),
    ],
)
def test_rejects_blank_error_message(error_message: str) -> None:
    with pytest.raises(
        ValueError,
        match=re.escape("error_message must be non-empty when provided"),
    ):
        make_experiment_run(
            status=ExperimentStatus.FAILED,
            error_message=error_message,
            started_at=datetime(2024, 2, 1, 9, 1),
            finished_at=datetime(2024, 2, 1, 9, 5),
        )


@pytest.mark.parametrize(
    (
        "status",
        "has_result",
        "error_message",
        "started_at",
        "finished_at",
        "message",
    ),
    [
        pytest.param(
            ExperimentStatus.COMPLETED,
            False,
            None,
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            "a completed run must have a result",
            id="completed-without-result",
        ),
        pytest.param(
            ExperimentStatus.FAILED,
            False,
            None,
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            "a failed run must have an error message",
            id="failed-without-error",
        ),
        pytest.param(
            ExperimentStatus.PENDING,
            True,
            None,
            None,
            None,
            "only a completed run can have a result",
            id="pending-with-result",
        ),
        pytest.param(
            ExperimentStatus.RUNNING,
            True,
            None,
            datetime(2024, 2, 1, 9, 1),
            None,
            "only a completed run can have a result",
            id="running-with-result",
        ),
        pytest.param(
            ExperimentStatus.FAILED,
            True,
            "boom",
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            "only a completed run can have a result",
            id="failed-with-result",
        ),
        pytest.param(
            ExperimentStatus.PENDING,
            False,
            "boom",
            None,
            None,
            "only a failed run can have an error message",
            id="pending-with-error",
        ),
        pytest.param(
            ExperimentStatus.RUNNING,
            False,
            "boom",
            datetime(2024, 2, 1, 9, 1),
            None,
            "only a failed run can have an error message",
            id="running-with-error",
        ),
        pytest.param(
            ExperimentStatus.COMPLETED,
            True,
            "boom",
            datetime(2024, 2, 1, 9, 1),
            datetime(2024, 2, 1, 9, 5),
            "only a failed run can have an error message",
            id="completed-with-error",
        ),
    ],
)
def test_rejects_inconsistent_status_result_and_error(
    status: ExperimentStatus,
    has_result: bool,
    error_message: str | None,
    started_at: datetime | None,
    finished_at: datetime | None,
    message: str,
    performance_result: PerformanceResult,
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        make_experiment_run(
            status=status,
            result=performance_result if has_result else None,
            error_message=error_message,
            started_at=started_at,
            finished_at=finished_at,
        )


def test_run_is_immutable() -> None:
    run = make_experiment_run()

    with pytest.raises(FrozenInstanceError):
        setattr(run, "status", ExperimentStatus.RUNNING)