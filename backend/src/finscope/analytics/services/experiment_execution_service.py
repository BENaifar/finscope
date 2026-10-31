
from datetime import UTC, datetime

from finscope.analytics.services.portfolio_analysis_engine import (
    PortfolioAnalysisEngine,
)
from finscope.domain.experiment_run import ExperimentRun, ExperimentStatus
from finscope.domain.portfolio import Portfolio
from finscope.market_data.models.price_series import PriceSeries


class ExperimentExecutionService:
    def __init__(
        self,
        analysis_engine: PortfolioAnalysisEngine | None = None,
    ) -> None:
        self._analysis_engine = (
            analysis_engine
            if analysis_engine is not None
            else PortfolioAnalysisEngine()
        )

    def fail_run(
        self,
        running_run: ExperimentRun,
        error_message: str,
    ) -> ExperimentRun:
        if running_run.status != ExperimentStatus.RUNNING:
            raise ValueError("Only a running run can be failed")

        return running_run.fail(
            finished_at=datetime.now(UTC),
            error_message=error_message,
        )

    def execute(
        self,
        running_run: ExperimentRun,
        portfolio: Portfolio,
        price_series: tuple[PriceSeries, ...],
    ) -> ExperimentRun:
        if not isinstance(running_run, ExperimentRun):
            raise TypeError("running_run must be an ExperimentRun")

        if running_run.status != ExperimentStatus.RUNNING:
            raise ValueError("Only a running run can be executed")

        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio")

        if running_run.config.portfolio_id != portfolio.id:
            raise ValueError(
                "config portfolio_id must match the supplied portfolio"
            )

        if not isinstance(price_series, tuple):
            raise TypeError("price_series must be a tuple of PriceSeries")

        if any(not isinstance(series, PriceSeries) for series in price_series):
            raise TypeError("price_series must contain only PriceSeries instances")

        try:
            result = self._analysis_engine.analyze(
                portfolio=portfolio,
                config=running_run.config,
                price_series=price_series,
            )
        except Exception as exc:
            return self.fail_run(
                running_run=running_run,
                error_message=str(exc) or type(exc).__name__,
            )

        return running_run.complete(
            finished_at=datetime.now(UTC),
            result=result,
        )
