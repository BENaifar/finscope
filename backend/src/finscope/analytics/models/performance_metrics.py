from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PerformanceMetrics: 
	initial_value: float
	final_value: float
	pnl: float
	total_return: float
	maximum_drawdown: float
	maximum_drawdown_peak_date: date
	maximum_drawdown_trough_date: date
	best_daily_return: float
	best_daily_return_date: date
	highest_portfolio_value_date: date
	lowest_portfolio_value_date: date

    
    