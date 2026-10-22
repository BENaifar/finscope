from dataclasses import dataclass
from datetime import date

from src.finscope.analytics.models.performance_metrics import PerformanceMetrics
from src.finscope.analytics.models.portfolio_value_point import PortfolioValuePoint


@dataclass(frozen=True)
class PerformanceResult:
    value_points: tuple[PortfolioValuePoint, ...]
    metrics: PerformanceMetrics
    from_date: date
    to_date: date
    