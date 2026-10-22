
from datetime import datetime, timezone

from src.finscope.analytics.services.portfolio_analysis_engine import (
    PortfolioAnalysisEngine,
)
from src.finscope.domain.experiment_run import ExperimentRun
from src.finscope.domain.portfolio import Portfolio
from src.finscope.market_data.models.price_series import PriceSeries


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

    def execute(
        self,
        run: ExperimentRun,
        portfolio: Portfolio,
        price_series: tuple[PriceSeries, ...],
    ) -> ExperimentRun:
        if run.config.portfolio_id != portfolio.id:
            raise ValueError(
                "config portfolio_id must match the supplied portfolio"
            )

        running_run = run.start(datetime.now(timezone.utc))

        try:
            result = self._analysis_engine.analyze(
                portfolio=portfolio,
                config=running_run.config,
                price_series=price_series,
            )
        except Exception as exc:
            return running_run.fail(
                finished_at=datetime.now(timezone.utc),
                error_message=str(exc) or type(exc).__name__,
            )

        return running_run.complete(
            finished_at=datetime.now(timezone.utc),
            result=result,
        )
