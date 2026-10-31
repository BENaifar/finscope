from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instrument:
    id: str
    symbol: str
    name: str
    currency: str = field(default="USD")

    def __post_init__(self) -> None:
        for field_name in ("id", "symbol", "name", "currency"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")