from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from tests.fixtures.application_fakes import (
    FakeExperimentReader,
    FakeOrchestrator,
    FakePortfolioReader,
    FakeRunStore,
    OrchestratorMode,
)
from tests.fixtures.factories import jan, make_config, make_instrument, make_portfolio

from finscope.application.errors import (
    ApplicationError,
    ExperimentNotFoundError,
    PortfolioNotFoundError,
)
from finscope.application.experiment_workflow_service import (
    ExperimentWorkflowService,
)
from finscope.domain.experiment_run import ExperimentStatus

NOW = datetime(2024, 2, 1, 9, 0, tzinfo=UTC)
CONFIG = make_config(jan(1), jan(31))
PORTFOLIO = make_portfolio(
    [(make_instrument("inst-a"), "0.6"), (make_instrument("inst-b"), "0.4")]
)


@dataclass
class Harness:
    service: ExperimentWorkflowService
    runs: FakeRunStore
    orchestrator: FakeOrchestrator
    events: list[str] = field(default_factory=list)


def build(
    *,
    mode: OrchestratorMode = "completed",
    with_experiment: bool = True,
    with_portfolio: bool = True,
    deterministic: bool = True,
) -> Harness:
    events: list[str] = []
    runs = FakeRunStore(events)
    orchestrator = FakeOrchestrator(events, mode)
    experiments = FakeExperimentReader(*([CONFIG] if with_experiment else []))
    portfolios = FakePortfolioReader(*([PORTFOLIO] if with_portfolio else []))

    def commit() -> None:
        events.append("commit")

    extra = (
        {"id_factory": lambda: "run-fixed", "clock": lambda: NOW}
        if deterministic
        else {}
    )
    service = ExperimentWorkflowService(
        experiments=experiments,
        portfolios=portfolios,
        runs=runs,
        orchestrator=orchestrator,
        commit=commit,
        **extra,
    )
    return Harness(service, runs, orchestrator, events)


def test_completed_run_is_saved_pending_first_then_final_with_a_commit_each() -> None:
    harness = build()

    result = harness.service.run_experiment(CONFIG.id)

    assert harness.events == [
        "add:pending",
        "commit",
        "orchestrate",
        "update:completed",
        "commit",
    ]
    assert result.status == ExperimentStatus.COMPLETED
    assert result.result is not None
    assert harness.runs.updated == [result]


def test_orchestrator_receives_a_new_pending_run_for_the_loaded_experiment() -> None:
    harness = build()

    harness.service.run_experiment(CONFIG.id)

    portfolio, run = harness.orchestrator.received[0]
    assert portfolio == PORTFOLIO
    assert run.id == "run-fixed"
    assert run.config == CONFIG
    assert run.status == ExperimentStatus.PENDING
    assert run.created_at == NOW
    assert run.started_at is None
    assert harness.runs.added == [run]


def test_failed_run_is_persisted_and_returned_not_raised() -> None:
    harness = build(mode="failed")

    result = harness.service.run_experiment(CONFIG.id)

    assert harness.events[-2:] == ["update:failed", "commit"]
    assert result.status == ExperimentStatus.FAILED
    assert result.error_message == "provider unavailable"
    assert harness.runs.updated == [result]


def test_unknown_experiment_raises_before_anything_is_saved() -> None:
    harness = build(with_experiment=False)

    with pytest.raises(ExperimentNotFoundError, match=CONFIG.id) as error:
        harness.service.run_experiment(CONFIG.id)

    assert error.value.experiment_id == CONFIG.id
    assert harness.events == []


def test_unknown_portfolio_raises_before_anything_is_saved() -> None:
    harness = build(with_portfolio=False)

    with pytest.raises(PortfolioNotFoundError, match=CONFIG.portfolio_id) as error:
        harness.service.run_experiment(CONFIG.id)

    assert error.value.portfolio_id == CONFIG.portfolio_id
    assert harness.events == []


def test_not_found_errors_share_an_application_error_base() -> None:
    assert issubclass(ExperimentNotFoundError, ApplicationError)
    assert issubclass(PortfolioNotFoundError, ApplicationError)


def test_unexpected_orchestrator_error_propagates_and_leaves_a_committed_pending_run(
) -> None:
    harness = build(mode="raises")

    with pytest.raises(RuntimeError, match="unexpected orchestration failure"):
        harness.service.run_experiment(CONFIG.id)

    assert harness.events == ["add:pending", "commit", "orchestrate"]
    assert harness.runs.updated == []


def test_default_run_ids_are_unique_and_default_clock_is_timezone_aware() -> None:
    harness = build(deterministic=False)

    first = harness.service.run_experiment(CONFIG.id)
    second = harness.service.run_experiment(CONFIG.id)

    assert first.id.strip() and second.id.strip()
    assert first.id != second.id
    created_at = harness.runs.added[0].created_at
    assert created_at.utcoffset() == timedelta(0)
