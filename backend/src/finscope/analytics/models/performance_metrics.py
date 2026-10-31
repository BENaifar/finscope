from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PerformanceMetrics: 
	initial_value: Decimal
	final_value: Decimal
	pnl: Decimal
	total_return: Decimal
	maximum_drawdown: Decimal
	maximum_drawdown_peak_date: date
	maximum_drawdown_trough_date: date
	best_daily_return: Decimal
	best_daily_return_date: date
	highest_portfolio_value_date: date
	lowest_portfolio_value_date: date

    
    