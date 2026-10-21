from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    id: str
    symbol: str
    name: str
    currency: str = "USD"