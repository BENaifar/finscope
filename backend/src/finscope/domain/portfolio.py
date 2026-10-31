from dataclasses import dataclass, field
from decimal import Decimal

from finscope.domain.instrument import Instrument
from finscope.domain.portfolio_allocation import PortfolioAllocation


@dataclass(frozen=True)
class Portfolio:
    id: str
    initial_capital: Decimal
    allocations: tuple[PortfolioAllocation, ...]
    base_currency: str = field(default="USD")
    strategy: str = field(default="buy_and_hold")

    def __post_init__(self) -> None:
        if self.initial_capital <= Decimal("0"):
            raise ValueError("initial_capital must be positive")

        if not self.allocations:
            raise ValueError("portfolio must have allocations")

        instruments = [
            allocation.instrument
            for allocation in self.allocations
        ]

        if len(instruments) != len(set(instruments)):
            raise ValueError("duplicate instrument allocations")

        total_weight = sum(
            (allocation.weight for allocation in self.allocations),
            start=Decimal("0"),
        )

        if abs(total_weight - Decimal("1")) > Decimal("0.000001"):
            raise ValueError("allocation weights must sum to 1")

        if self.base_currency != "USD":
            raise ValueError("MVP supports USD portfolios only")

        if self.strategy != "buy_and_hold":
            raise ValueError("unsupported portfolio strategy")

    @property
    def instruments(self) -> tuple[Instrument, ...]:
        return tuple(
            allocation.instrument
            for allocation in self.allocations
        )

    def get_weight(self, instrument_id: str) -> Decimal:
        for allocation in self.allocations:
            if allocation.instrument.id == instrument_id:
                return allocation.weight

        raise ValueError(
            f"Instrument {instrument_id} is not in portfolio {self.id}"
        )