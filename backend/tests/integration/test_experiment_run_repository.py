from collections.abc import Callable
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.fixtures.factories import (
    jan,
    make_completed_run,
    make_config,
    make_failed_run,
    make_instrument,
    make_pending_run,
    make_performance_metrics,
    make_portfolio,
    make_running_run,
    ts,
)

from finscope.analytics.models.performance_result import PerformanceResult
from finscope.analytics.models.portfolio_value_point import PortfolioValuePoint
from finscope.domain.experiment_run import ExperimentRun
from finscope.persistence.repositories.experiment_repository import (
    ExperimentRepository,
)
from finscope.persistence.repositories.experiment_run_repository import (
    ExperimentRunRepository,
)
from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)
from finscope.persistence.repositories.portfolio_repository import (
    PortfolioRepository,
)

RUN_FACTORIES = [
    make_pending_run,
    make_running_run,
    make_completed_run,
    make_failed_run,
]


def _insert_experiment(session: Session) -> None:
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    instruments = InstrumentRepository(session)
    instruments.add(instrument_a)
    instruments.add(instrument_b)
    PortfolioRepository(session).add(
        make_portfolio([(instrument_a, "0.6"), (instrument_b, "0.4")])
    )
    ExperimentRepository(session).add(make_config(jan(1), jan(31)))


def _insert_raw_run(session: Session, **overrides: Any) -> None:
    params: dict[str, Any] = {
        "id": "run-sql",
        "experiment_id": "test-experiment",
        "status": "pending",
        "created_at": ts(0),
        "started_at": None,
        "finished_at": None,
        "error_message": None,
    }
    params.update(overrides)
    session.execute(
        text(
            "INSERT INTO experiment_runs "
            "(id, experiment_id, status, created_at, started_at, finished_at, "
            "error_message) VALUES (:id, :experiment_id, :status, :created_at, "
            ":started_at, :finished_at, :error_message)"
        ),
        params,
    )


def _count(session: Session, table: str) -> int:
    return session.scalar(text(f"SELECT count(*) FROM {table}")) or 0


@pytest.mark.parametrize("factory", RUN_FACTORIES)
def test_run_round_trips_in_every_status(
    session: Session, factory: Callable[[], ExperimentRun]
) -> None:
    _insert_experiment(session)
    run = factory()
    repository = ExperimentRunRepository(session)

    repository.add(run)

    assert repository.get_by_id(run.id) == run


def test_completed_result_keeps_full_decimal_precision(session: Session) -> None:
    _insert_experiment(session)
    exact = Decimal("10200.123456789012345678")
    result = PerformanceResult(
        value_points=(
            PortfolioValuePoint(jan(1), Decimal("10000")),
            PortfolioValuePoint(jan(2), exact),
        ),
        metrics=make_performance_metrics(
            initial_value=Decimal("10000"),
            final_value=exact,
            pnl=Decimal("200.123456789012345678"),
            total_return=Decimal("0.0200123456789012345678"),
        ),
        from_date=jan(1),
        to_date=jan(2),
    )
    run = replace(make_completed_run(), result=result)
    repository = ExperimentRunRepository(session)

    repository.add(run)

    loaded = repository.get_by_id(run.id)
    assert loaded is not None
    assert loaded.result == result
    assert loaded.result.metrics.total_return == Decimal("0.0200123456789012345678")


def test_get_by_id_returns_none_for_unknown_run(session: Session) -> None:
    assert ExperimentRunRepository(session).get_by_id("missing") is None


def test_run_requires_an_existing_experiment(session: Session) -> None:
    with pytest.raises(IntegrityError):
        ExperimentRunRepository(session).add(make_pending_run())


def test_one_experiment_can_have_many_runs(session: Session) -> None:
    _insert_experiment(session)
    repository = ExperimentRunRepository(session)
    first = make_pending_run()
    second = replace(make_pending_run(), id="run-2")

    repository.add(first)
    repository.add(second)

    assert repository.get_by_id("run-1") == first
    assert repository.get_by_id("run-2") == second
    assert first.config == second.config


def test_update_walks_a_run_through_to_completion(session: Session) -> None:
    _insert_experiment(session)
    repository = ExperimentRunRepository(session)
    pending = make_pending_run()
    repository.add(pending)

    running = pending.start(ts(1))
    repository.update(running)
    assert repository.get_by_id(pending.id) == running

    completed = running.complete(ts(5), make_completed_run().result)
    repository.update(completed)
    assert repository.get_by_id(pending.id) == completed


def test_update_records_a_failure(session: Session) -> None:
    _insert_experiment(session)
    repository = ExperimentRunRepository(session)
    running = make_pending_run().start(ts(1))
    repository.add(running)

    failed = running.fail(ts(2), "provider timed out")
    repository.update(failed)

    assert repository.get_by_id(failed.id) == failed


def test_update_unknown_run_raises(session: Session) -> None:
    with pytest.raises(LookupError):
        ExperimentRunRepository(session).update(make_pending_run())


def test_update_refuses_to_move_run_to_another_experiment(session: Session) -> None:
    _insert_experiment(session)
    repository = ExperimentRunRepository(session)
    repository.add(make_pending_run())
    moved = replace(
        make_pending_run(),
        config=make_config(jan(1), jan(31), config_id="other-experiment"),
    )

    with pytest.raises(ValueError, match="different experiment"):
        repository.update(moved)


def test_update_refuses_to_replace_a_saved_result(session: Session) -> None:
    _insert_experiment(session)
    repository = ExperimentRunRepository(session)
    completed = make_completed_run()
    repository.add(completed)

    with pytest.raises(ValueError, match="cannot be replaced"):
        repository.update(completed)


def test_deleting_a_run_cascades_to_its_results(session: Session) -> None:
    _insert_experiment(session)
    ExperimentRunRepository(session).add(make_completed_run())
    assert _count(session, "portfolio_value_points") == 2
    assert _count(session, "performance_metrics") == 1

    session.execute(text("DELETE FROM experiment_runs WHERE id = 'run-1'"))

    assert _count(session, "portfolio_value_points") == 0
    assert _count(session, "performance_metrics") == 0


def test_experiment_with_runs_cannot_be_deleted(session: Session) -> None:
    _insert_experiment(session)
    ExperimentRunRepository(session).add(make_pending_run())

    with pytest.raises(IntegrityError):
        session.execute(text("DELETE FROM experiments WHERE id = 'test-experiment'"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "bogus"},
        {"status": "pending", "started_at": ts(1)},
        {"status": "running", "started_at": None},
        {"status": "running", "started_at": ts(1), "finished_at": ts(2)},
        {"status": "completed", "started_at": ts(1), "finished_at": None},
        {"status": "failed", "started_at": ts(1), "finished_at": ts(2)},
        {"status": "pending", "error_message": "unexpected"},
        {
            "status": "failed",
            "started_at": ts(1),
            "finished_at": ts(2),
            "error_message": "   ",
        },
        {"status": "running", "created_at": ts(5), "started_at": ts(1)},
        {
            "status": "completed",
            "started_at": ts(3),
            "finished_at": ts(2),
        },
    ],
    ids=[
        "unknown-status",
        "pending-with-start",
        "running-without-start",
        "running-with-finish",
        "completed-without-finish",
        "failed-without-error",
        "error-on-non-failed",
        "blank-error",
        "created-after-started",
        "started-after-finished",
    ],
)
def test_database_rejects_invalid_run_via_raw_sql(
    session: Session, overrides: dict[str, Any]
) -> None:
    _insert_experiment(session)

    with pytest.raises(IntegrityError):
        _insert_raw_run(session, **overrides)


def test_database_accepts_a_valid_raw_run(session: Session) -> None:
    _insert_experiment(session)

    _insert_raw_run(session)

    assert _count(session, "experiment_runs") == 1


def test_database_rejects_non_usd_value_point_via_raw_sql(session: Session) -> None:
    _insert_experiment(session)
    ExperimentRunRepository(session).add(make_pending_run())

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO portfolio_value_points "
                "(run_id, valuation_date, total_value, currency) "
                "VALUES ('run-1', :d, 100, 'EUR')"
            ),
            {"d": date(2024, 1, 1)},
        )


def test_database_rejects_metrics_with_inverted_dates_via_raw_sql(
    session: Session,
) -> None:
    _insert_experiment(session)
    ExperimentRunRepository(session).add(make_pending_run())
    d = date(2024, 1, 1)

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO performance_metrics (run_id, from_date, to_date, "
                "initial_value, final_value, pnl, total_return, maximum_drawdown, "
                "maximum_drawdown_peak_date, maximum_drawdown_trough_date, "
                "best_daily_return, best_daily_return_date, "
                "highest_portfolio_value_date, lowest_portfolio_value_date) "
                "VALUES ('run-1', :to_d, :from_d, 1, 1, 0, 0, 0, :d, :d, 0, :d, "
                ":d, :d)"
            ),
            {"from_d": d, "to_d": date(2024, 1, 5), "d": d},
        )