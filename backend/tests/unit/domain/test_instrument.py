import re

import pytest

from finscope.domain.instrument import Instrument


@pytest.mark.parametrize(
    "field_name",
    ["id", "symbol", "name", "currency"],
)
def test_rejects_blank_fields(field_name: str) -> None:
    values = {
        "id": "instrument-1",
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "currency": "USD",
    }
    values[field_name] = " "

    with pytest.raises(
        ValueError,
        match=re.escape(f"{field_name} must be a non-empty string"),
    ):
        Instrument(**values)


def test_rejects_non_string_field_value() -> None:
    with pytest.raises(
        ValueError,
        match=re.escape("symbol must be a non-empty string"),
    ):
        Instrument(
            id="instrument-1",
            symbol=123,  # type: ignore[arg-type]
            name="Apple Inc.",
            currency="USD",
        )