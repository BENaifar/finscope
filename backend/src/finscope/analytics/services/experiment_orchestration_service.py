
from datetime import UTC, datetime

from finscope.analytics.services.experiment_execution_service import (
    ExperimentExecutionService,
)
from finscope.domain.experiment_run import ExperimentRun
from finscope.domain.portfolio import Portfolio
from finscope.market_data.errors import MarketDataError
from finscope.market_data.models.price_series import PriceSeries
from finscope.market_data.providers.price_history_provider import (
    PriceHistoryProvider,
)


class ExperimentOrchestrationService:
    def __init__(
        self,
        provider: PriceHistoryProvider,
        execution_service: ExperimentExecutionService,
    ) -> None:
        self._provider = provider
        self._execution_service = execution_service

    def orchestrate(
        self,
        portfolio: Portfolio,
        run: ExperimentRun,
    ) -> ExperimentRun:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio")

        if not isinstance(run, ExperimentRun):
            raise TypeError("run must be an ExperimentRun")

        if portfolio.id != run.config.portfolio_id:
            raise ValueError(
                "The portfolio and experiment run's portfolio do not match"
            )

        running_run = run.start(datetime.now(UTC))

        try:
            price_series: tuple[PriceSeries, ...] = (
                self._provider.get_price_series(
                    instruments=portfolio.instruments,
                    start_date=run.config.start_date,
                    end_date=run.config.end_date,
                )
            )
        except MarketDataError as exc:
            return self._execution_service.fail_run(
                running_run=running_run,
                error_message=str(exc) or type(exc).__name__,
            )

        return self._execution_service.execute(
            running_run=running_run,
            portfolio=portfolio,
            price_series=price_series,
        )
