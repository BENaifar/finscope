from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PricePoint:
    date: date
    adjusted_close: Decimal

    def __post_init__(self) -> None:
        if self.adjusted_close <= Decimal("0"):
            raise ValueError("adjusted_close must be positive")