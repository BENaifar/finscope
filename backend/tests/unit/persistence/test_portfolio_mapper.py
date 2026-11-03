from decimal import Decimal

import pytest
from tests.fixtures.factories import make_instrument, make_portfolio

from finscope.domain.instrument import Instrument
from finscope.domain.portfolio import Portfolio
from finscope.persistence.mappings.instrument_mapper import (
    to_record as instrument_to_record,
)
from finscope.persistence.mappings.portfolio_mapper import to_domain, to_record
from finscope.persistence.models.portfolio import PortfolioRecord


def _make_two_asset_portfolio() -> tuple[Portfolio, Instrument, Instrument]:
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    portfolio = make_portfolio(
        [(instrument_a, "0.6"), (instrument_b, "0.4")],
        initial_capital="10000.123456",
        portfolio_id="portfolio-1",
    )
    return portfolio, instrument_a, instrument_b


def _attach_instruments(
    record: PortfolioRecord, *instruments: Instrument
) -> PortfolioRecord:
    """Simulate what the repository's eager loading does on a real read."""
    by_id = {instrument.id: instrument for instrument in instruments}
    for allocation in record.allocations:
        allocation.instrument = instrument_to_record(by_id[allocation.instrument_id])
    return record


def test_to_record_copies_portfolio_fields() -> None:
    portfolio, _, _ = _make_two_asset_portfolio()

    record = to_record(portfolio)

    assert (
        record.id,
        record.initial_capital,
        record.base_currency,
        record.strategy,
    ) == ("portfolio-1", Decimal("10000.123456"), "USD", "buy_and_hold")


def test_to_record_creates_one_allocation_record_per_allocation() -> None:
    portfolio, _, _ = _make_two_asset_portfolio()

    record = to_record(portfolio)

    assert [
        (allocation.instrument_id, allocation.weight)
        for allocation in record.allocations
    ] == [("inst-a", Decimal("0.6")), ("inst-b", Decimal("0.4"))]


def test_to_record_links_allocations_back_to_their_portfolio_record() -> None:
    portfolio, _, _ = _make_two_asset_portfolio()

    record = to_record(portfolio)

    # The portfolio_id FK column is filled by the ORM at flush time, not here.
    assert all(allocation.portfolio is record for allocation in record.allocations)


def test_round_trip_preserves_all_fields() -> None:
    portfolio, instrument_a, instrument_b = _make_two_asset_portfolio()

    record = _attach_instruments(to_record(portfolio), instrument_a, instrument_b)

    assert to_domain(record) == portfolio


def test_to_domain_returns_allocations_as_a_tuple() -> None:
    portfolio, instrument_a, instrument_b = _make_two_asset_portfolio()
    record = _attach_instruments(to_record(portfolio), instrument_a, instrument_b)

    result = to_domain(record)

    assert isinstance(result.allocations, tuple)
    assert result.instruments == (instrument_a, instrument_b)


def test_to_domain_rejects_weights_that_do_not_sum_to_one() -> None:
    portfolio, instrument_a, instrument_b = _make_two_asset_portfolio()
    record = _attach_instruments(to_record(portfolio), instrument_a, instrument_b)
    record.allocations[0].weight = Decimal("0.5")

    with pytest.raises(ValueError, match="sum to 1"):
        to_domain(record)


def test_to_domain_rejects_non_usd_currency() -> None:
    portfolio, instrument_a, instrument_b = _make_two_asset_portfolio()
    record = _attach_instruments(to_record(portfolio), instrument_a, instrument_b)
    record.base_currency = "EUR"

    with pytest.raises(ValueError, match="USD"):
        to_domain(record)


def test_to_domain_rejects_record_without_allocations() -> None:
    portfolio, _, _ = _make_two_asset_portfolio()
    record = to_record(portfolio)
    record.allocations = []

    with pytest.raises(ValueError, match="must have allocations"):
        to_domain(record)
