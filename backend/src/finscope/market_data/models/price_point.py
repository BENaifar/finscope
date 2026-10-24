from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PricePoint:
    date: date
    adjusted_close: Decimal
    
    def __post_init__(self) -> None:
        if not isinstance(self.date, date):
            raise TypeError("date must be a datetime.date")

        if not isinstance(self.adjusted_close, Decimal):
            raise TypeError("adjusted_close must be a Decimal")

        if not self.adjusted_close.is_finite():
            raise ValueError("adjusted_close must be finite")

        if self.adjusted_close <= Decimal("0"):
            raise ValueError("adjusted_close must be positive")
