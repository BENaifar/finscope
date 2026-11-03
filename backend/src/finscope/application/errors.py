class ApplicationError(Exception):
    """Base class for use-case level failures."""


class ExperimentNotFoundError(ApplicationError):
    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id
        super().__init__(f"Experiment {experiment_id} does not exist")


class PortfolioNotFoundError(ApplicationError):
    def __init__(self, portfolio_id: str) -> None:
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio {portfolio_id} does not exist")
