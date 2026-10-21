from dataclasses import dataclass
from datetime import date

from backend.src.finscope.domain.portfolio import Portfolio


@dataclass(frozen=True)
class ExperimentConfig:
    portfolio: Portfolio
    start_date: date
    end_date: date
    price_convention: str = "adjusted_close"

    def __post_init__(self) -> None:
        if not self.portfolio:
            raise ValueError("portfolio cannot be empty")

        if self.start_date >= self.end_date:
            raise ValueError("start_date must precede end_date")

        if self.price_convention != "adjusted_close":
            raise ValueError("unsupported price convention")