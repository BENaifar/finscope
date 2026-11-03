from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from finscope.application.errors import (
    ExperimentNotFoundError,
    PortfolioNotFoundError,
)
from finscope.application.ports import (
    ExperimentReader,
    PortfolioReader,
    RunOrchestrator,
    RunStore,
)
from finscope.domain.experiment_run import ExperimentRun


def _new_run_id() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ExperimentWorkflowService:
    """Run one experiment end to end.

    Commits exactly twice: once after saving the pending run, once after
    saving the final state. The caller owns the session, including rollback.
    A crash during orchestration leaves a committed PENDING run that nothing
    recovers yet.
    """

    def __init__(
        self,
        experiments: ExperimentReader,
        portfolios: PortfolioReader,
        runs: RunStore,
        orchestrator: RunOrchestrator,
        commit: Callable[[], None],
        id_factory: Callable[[], str] = _new_run_id,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._experiments = experiments
        self._portfolios = portfolios
        self._runs = runs
        self._orchestrator = orchestrator
        self._commit = commit
        self._id_factory = id_factory
        self._clock = clock

    def run_experiment(self, experiment_id: str) -> ExperimentRun:
        config = self._experiments.get_by_id(experiment_id)
        if config is None:
            raise ExperimentNotFoundError(experiment_id)

        portfolio = self._portfolios.get_by_id(config.portfolio_id)
        if portfolio is None:
            raise PortfolioNotFoundError(config.portfolio_id)

        pending = ExperimentRun(
            id=self._id_factory(),
            config=config,
            created_at=self._clock(),
            started_at=None,
            finished_at=None,
        )
        self._runs.add(pending)
        self._commit()

        final = self._orchestrator.orchestrate(portfolio, pending)
        self._runs.update(final)
        self._commit()

        return final
