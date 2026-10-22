from decimal import Decimal
from datetime import date

from src.finscope.analytics.models.performance_metrics import PerformanceMetrics
from src.finscope.analytics.models.portfolio_value_point import PortfolioValuePoint


class PerformanceCalculationService:
    """Computes performance metrics from a cash-flow-free valuation series.

    Ties resolve to the earliest date. Returns are computed between
    consecutive observations, which may be more than one calendar day apart.
    """

    def calculate(
        self,
        portfolio_values: tuple[PortfolioValuePoint, ...],
    ) -> PerformanceMetrics:
        points = self._validate(portfolio_values)

        initial_value = points[0].total_value
        final_value = points[-1].total_value
        pnl = final_value - initial_value

        drawdown, peak_date, trough_date = self._maximum_drawdown(points)
        best_return, best_return_date = self._best_period_return(points)

        return PerformanceMetrics(
            initial_value=float(initial_value),
            final_value=float(final_value),
            pnl=float(pnl),
            total_return=float(pnl / initial_value),
            maximum_drawdown=float(drawdown),
            maximum_drawdown_peak_date=peak_date,
            maximum_drawdown_trough_date=trough_date,
            best_daily_return=float(best_return),
            best_daily_return_date=best_return_date,
            highest_portfolio_value_date=max(
                points, key=lambda p: p.total_value
            ).valuation_date,
            lowest_portfolio_value_date=min(
                points, key=lambda p: p.total_value
            ).valuation_date,
        )

    @staticmethod
    def _validate(
        portfolio_values: tuple[PortfolioValuePoint, ...],
    ) -> tuple[PortfolioValuePoint, ...]:
        if len(portfolio_values) < 2:
            raise ValueError("At least two portfolio values are required")
        if any(
            current.valuation_date <= previous.valuation_date
            for previous, current in zip(portfolio_values, portfolio_values[1:])
        ):
            raise ValueError("Portfolio values must be in strictly increasing date order")
        if any(
            not p.total_value.is_finite() or p.total_value <= 0
            for p in portfolio_values
        ):
            raise ValueError("Portfolio values must be positive and finite")
        return portfolio_values

    @staticmethod
    def _maximum_drawdown(points) -> tuple[Decimal, date, date]:
        peak = points[0]
        worst = Decimal(0)
        worst_peak_date = worst_trough_date = points[0].valuation_date
        for point in points[1:]:
            if point.total_value > peak.total_value:
                peak = point
            drawdown = (peak.total_value - point.total_value) / peak.total_value
            if drawdown > worst:
                worst = drawdown
                worst_peak_date = peak.valuation_date
                worst_trough_date = point.valuation_date
        return worst, worst_peak_date, worst_trough_date

    @staticmethod
    def _best_period_return(points) -> tuple[Decimal, date]:
        returns = (
            ((cur.total_value - prev.total_value) / prev.total_value, cur.valuation_date)
            for prev, cur in zip(points, points[1:])
        )
        return max(returns, key=lambda item: item[0])