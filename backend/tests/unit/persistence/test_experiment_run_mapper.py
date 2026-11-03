from collections.abc import Callable
from decimal import Decimal

import pytest
from tests.fixtures.factories import (
    make_completed_run,
    make_failed_run,
    make_pending_run,
    make_running_run,
    ts,
)

from finscope.domain.experiment_run import ExperimentRun
from finscope.persistence.mappings.experiment_mapper import (
    to_record as experiment_to_record,
)
from finscope.persistence.mappings.experiment_run_mapper import (
    apply_state,
    to_domain,
    to_record,
)

RUN_FACTORIES = [
    make_pending_run,
    make_running_run,
    make_completed_run,
    make_failed_run,
]


def test_to_record_for_pending_run_has_no_result_rows() -> None:
    record = to_record(make_pending_run())

    assert record.id == "run-1"
    assert record.experiment_id == "test-experiment"
    assert record.status == "pending"
    assert record.started_at is None
    assert record.value_points == []
    assert record.metrics is None


def test_to_record_for_completed_run_flattens_result() -> None:
    run = make_completed_run()
    assert run.result is not None

    record = to_record(run)

    assert record.status == "completed"
    assert [p.valuation_date for p in record.value_points] == [
        p.valuation_date for p in run.result.value_points
    ]
    assert record.metrics is not None
    assert record.metrics.initial_value == run.result.metrics.initial_value
    assert record.metrics.from_date == run.result.from_date


def test_to_record_for_failed_run_keeps_error_message() -> None:
    record = to_record(make_failed_run())

    assert record.status == "failed"
    assert record.error_message == "boom"


@pytest.mark.parametrize("factory", RUN_FACTORIES)
def test_round_trip_returns_equal_run(factory: Callable[[], ExperimentRun]) -> None:
    run = factory()
    record = to_record(run)
    record.experiment = experiment_to_record(run.config)

    assert to_domain(record) == run


def test_to_domain_rejects_completed_record_without_metrics() -> None:
    record = to_record(make_completed_run())
    record.experiment = experiment_to_record(make_completed_run().config)
    record.metrics = None

    with pytest.raises(ValueError, match="completed run must have a result"):
        to_domain(record)


def test_apply_state_moves_pending_record_to_running() -> None:
    record = to_record(make_pending_run())

    apply_state(record, make_running_run())

    assert record.status == "running"
    assert record.started_at == ts(1)
    assert record.finished_at is None


def test_apply_state_attaches_result_on_completion() -> None:
    record = to_record(make_running_run())

    apply_state(record, make_completed_run())

    assert record.status == "completed"
    assert record.finished_at == ts(5)
    assert record.metrics is not None
    assert len(record.value_points) == 2
    assert record.metrics.final_value == Decimal("1000")


def test_apply_state_refuses_to_replace_an_existing_result() -> None:
    record = to_record(make_completed_run())

    with pytest.raises(ValueError, match="cannot be replaced"):
        apply_state(record, make_completed_run())