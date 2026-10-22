from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instrument:
    id: str
    symbol: str
    name: str
    currency: str = field(default="USD")