from typing import Protocol

from finscope.domain.experiment_config import ExperimentConfig
from finscope.domain.experiment_run import ExperimentRun
from finscope.domain.portfolio import Portfolio


class ExperimentReader(Protocol):
    """Loads saved experiment configurations."""

    def get_by_id(self, experiment_id: str) -> ExperimentConfig | None: ...


class PortfolioReader(Protocol):
    """Loads saved portfolios."""

    def get_by_id(self, portfolio_id: str) -> Portfolio | None: ...


class RunStore(Protocol):
    """Saves experiment runs; never commits."""

    def add(self, run: ExperimentRun) -> None: ...

    def update(self, run: ExperimentRun) -> None: ...


class RunOrchestrator(Protocol):
    """Executes a pending run and returns its completed or failed state."""

    def orchestrate(
        self, portfolio: Portfolio, run: ExperimentRun
    ) -> ExperimentRun: ...
