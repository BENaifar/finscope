from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.analytics.services.performance_calculation_service import (
    PerformanceCalculationService,
)
from src.finscope.analytics.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from src.finscope.domain.experiment_config import ExperimentConfig
from src.finscope.domain.portfolio import Portfolio
from src.finscope.market_data.models.price_series import PriceSeries


class PortfolioAnalysisEngine:
    def __init__(
        self,
        valuation_service: PortfolioValuationService | None = None,
        performance_calculation_service: PerformanceCalculationService | None = None,
    ) -> None:
        self._valuation_service = (
            valuation_service
            if valuation_service is not None
            else PortfolioValuationService()
        )
        self._performance_calculation_service = (
            performance_calculation_service
            if performance_calculation_service is not None
            else PerformanceCalculationService()
        )

    def analyze(
        self,
        portfolio: Portfolio,
        config: ExperimentConfig,
        price_series: tuple[PriceSeries, ...],
    ) -> PerformanceResult:
        if not isinstance(portfolio, Portfolio):
            raise TypeError("portfolio must be a Portfolio")
        if not isinstance(config, ExperimentConfig):
            raise TypeError("config must be an ExperimentConfig")
        if not isinstance(price_series, tuple):
            raise TypeError("price_series must be a tuple of PriceSeries")
        if any(not isinstance(series, PriceSeries) for series in price_series):
            raise TypeError("price_series must contain only PriceSeries instances")
        if config.portfolio_id != portfolio.id:
            raise ValueError(
                "config portfolio_id must match the supplied portfolio"
            )
        if config.start_date >= config.end_date:
            raise ValueError("config start_date must precede end_date")
        if not price_series:
            raise ValueError("At least one price series is required")

        value_points = self._valuation_service.calculate(
            portfolio,
            config,
            price_series,
        )
        if len(value_points) < 2:
            raise ValueError(
                "At least two portfolio valuation points are required"
            )

        metrics = self._performance_calculation_service.calculate(value_points)
        return PerformanceResult(
            value_points=value_points,
            metrics=metrics,
            from_date=value_points[0].valuation_date,
            to_date=value_points[-1].valuation_date,
        )