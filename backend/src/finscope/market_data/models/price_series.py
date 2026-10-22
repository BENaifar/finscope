from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.src.finscope.domain.instrument import Instrument
from finscope.market_data.models.price_point import PricePoint


@dataclass(frozen=True)
class PriceSeries:
    instrument: Instrument
    points: tuple[PricePoint, ...]

    def __post_init__(self) -> None:
        if not self.instrument:
            raise ValueError("instrument cannot be empty")

        if not self.points:
            raise ValueError("price series cannot be empty")

        dates = [point.date for point in self.points]

        if dates != sorted(dates):
            raise ValueError("price points must be sorted by date")

        if len(dates) != len(set(dates)):
            raise ValueError("duplicate price dates are not allowed")

    def get_price_on(self, target_date: date) -> Decimal:
        for point in self.points:
            if point.date == target_date:
                return point.adjusted_close

        raise ValueError(
            f"No price found for {self.instrument.name} on {target_date}"
        )