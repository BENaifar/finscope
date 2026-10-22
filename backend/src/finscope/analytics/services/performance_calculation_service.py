from src.finscope.analytics.models.performance_metrics import PerformanceMetrics
from src.finscope.analytics.models.portfolio_value_point import PortfolioValuePoint


class PerformanceCalculationService:
    def calculate(
        self,
        portfolio_values: tuple[PortfolioValuePoint, ...],
    ) -> PerformanceMetrics:
        if len(portfolio_values) < 2:
            raise ValueError("At least two portfolio values are required")

        values = tuple(
            (point.valuation_date, float(point.total_value))
            for point in portfolio_values
        )
        if any(
            current_date <= previous_date
            for (previous_date, _), (current_date, _) in zip(values, values[1:])
        ):
            raise ValueError("Portfolio values must be in strictly increasing date order")
        if any(value <= 0 for _, value in values):
            raise ValueError("Portfolio values must be positive")

        initial_date, initial_value = values[0]
        final_value = values[-1][1]
        pnl = final_value - initial_value
        total_return = pnl / initial_value

        highest_date, _ = max(values, key=lambda item: item[1])
        lowest_date, _ = min(values, key=lambda item: item[1])

        peak_date, peak_value = values[0]
        maximum_drawdown = 0.0
        maximum_drawdown_peak_date = initial_date
        maximum_drawdown_trough_date = initial_date
        for valuation_date, value in values[1:]:
            if value > peak_value:
                peak_date = valuation_date
                peak_value = value

            drawdown = (peak_value - value) / peak_value
            if drawdown > maximum_drawdown:
                maximum_drawdown = drawdown
                maximum_drawdown_peak_date = peak_date
                maximum_drawdown_trough_date = valuation_date

        best_daily_return = float("-inf")
        best_daily_return_date = values[1][0]
        for (_, previous_value), (valuation_date, value) in zip(
            values, values[1:]
        ):
            daily_return = (value - previous_value) / previous_value
            if daily_return > best_daily_return:
                best_daily_return = daily_return
                best_daily_return_date = valuation_date

        return PerformanceMetrics(
            initial_value=initial_value,
            final_value=final_value,
            pnl=pnl,
            total_return=total_return,
            maximum_drawdown=maximum_drawdown,
            maximum_drawdown_peak_date=maximum_drawdown_peak_date,
            maximum_drawdown_trough_date=maximum_drawdown_trough_date,
            best_daily_return=best_daily_return,
            best_daily_return_date=best_daily_return_date,
            highest_portfolio_value_date=highest_date,
            lowest_portfolio_value_date=lowest_date,
        )