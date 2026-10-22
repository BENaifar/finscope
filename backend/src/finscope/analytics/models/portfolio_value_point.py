from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class PortfolioValuePoint:
    valuation_date: date
    total_value: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if type(self.valuation_date) is not date:
            raise TypeError("valuation_date must be a date")
        if self.valuation_date >= date.today():
            raise ValueError("valuation_date must be in the past")
        if not isinstance(self.total_value, float):
            raise TypeError("total_value must be a float")
        if self.currency != "USD":
            raise ValueError("Only USD is implemented in this version of the app")