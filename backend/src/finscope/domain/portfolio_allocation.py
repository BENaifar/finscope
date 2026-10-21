from dataclasses import dataclass
from decimal import Decimal

from backend.src.finscope.domain.instrument import Instrument


@dataclass(frozen=True)
class PortfolioAllocation:
    instrument: Instrument
    weight: Decimal

    def __post_init__(self) -> None:
        if not self.instrument:
            raise ValueError("instrument cannot be empty")

        if self.weight <= Decimal("0"):
            raise ValueError("weight must be positive")

        if self.weight > Decimal("1"):
            raise ValueError("weight cannot exceed 1")