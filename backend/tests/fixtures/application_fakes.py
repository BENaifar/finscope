from datetime import timedelta
from typing import Literal

from tests.fixtures.factories import make_performance_result

from finscope.domain.experiment_config import ExperimentConfig
from finscope.domain.experiment_run import ExperimentRun
from finscope.domain.portfolio import Portfolio

OrchestratorMode = Literal["completed", "failed", "raises"]


class FakeExperimentReader:
    def __init__(self, *configs: ExperimentConfig) -> None:
        self._configs = {config.id: config for config in configs}

    def get_by_id(self, experiment_id: str) -> ExperimentConfig | None:
        return self._configs.get(experiment_id)


class FakePortfolioReader:
    def __init__(self, *portfolios: Portfolio) -> None:
        self._portfolios = {portfolio.id: portfolio for portfolio in portfolios}

    def get_by_id(self, portfolio_id: str) -> Portfolio | None:
        return self._portfolios.get(portfolio_id)


class FakeRunStore:
    """Records add/update calls in the shared event log as 'add:<status>'."""

    def __init__(self, events: list[str]) -> None:
        self._events = events
        self.added: list[ExperimentRun] = []
        self.updated: list[ExperimentRun] = []

    def add(self, run: ExperimentRun) -> None:
        self._events.append(f"add:{run.status.value}")
        self.added.append(run)

    def update(self, run: ExperimentRun) -> None:
        self._events.append(f"update:{run.status.value}")
        self.updated.append(run)


class FakeOrchestrator:
    """Stands in for ExperimentOrchestrationService using real domain transitions."""

    def __init__(self, events: list[str], mode: OrchestratorMode = "completed") -> None:
        self._events = events
        self._mode = mode
        self.received: list[tuple[Portfolio, ExperimentRun]] = []

    def orchestrate(self, portfolio: Portfolio, run: ExperimentRun) -> ExperimentRun:
        self._events.append("orchestrate")
        self.received.append((portfolio, run))

        if self._mode == "raises":
            raise RuntimeError("unexpected orchestration failure")

        started_at = run.created_at + timedelta(minutes=1)
        finished_at = run.created_at + timedelta(minutes=5)
        running = run.start(started_at)
        if self._mode == "failed":
            return running.fail(finished_at, "provider unavailable")
        return running.complete(finished_at, make_performance_result())
