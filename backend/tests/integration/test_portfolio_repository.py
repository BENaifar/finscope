from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.fixtures.factories import make_instrument, make_portfolio

from finscope.domain.instrument import Instrument
from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)
from finscope.persistence.repositories.portfolio_repository import (
    PortfolioRepository,
)


def _insert_instruments(session: Session) -> tuple[Instrument, Instrument]:
    # Ids are sorted: the repository loads allocations ordered by instrument_id.
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    repository = InstrumentRepository(session)
    repository.add(instrument_a)
    repository.add(instrument_b)
    return instrument_a, instrument_b


def _insert_portfolio_row(
    session: Session,
    portfolio_id: str = "raw-portfolio",
    initial_capital: str = "1000",
    base_currency: str = "USD",
    strategy: str = "buy_and_hold",
) -> None:
    session.execute(
        text(
            "INSERT INTO portfolios "
            "(id, initial_capital, base_currency, strategy) "
            "VALUES (:id, :initial_capital, :base_currency, :strategy)"
        ),
        {
            "id": portfolio_id,
            "initial_capital": Decimal(initial_capital),
            "base_currency": base_currency,
            "strategy": strategy,
        },
    )


def _insert_allocation_row(
    session: Session,
    portfolio_id: str,
    instrument_id: str,
    weight: str,
) -> None:
    session.execute(
        text(
            "INSERT INTO portfolio_allocations "
            "(portfolio_id, instrument_id, weight) "
            "VALUES (:portfolio_id, :instrument_id, :weight)"
        ),
        {
            "portfolio_id": portfolio_id,
            "instrument_id": instrument_id,
            "weight": Decimal(weight),
        },
    )


def _count(session: Session, table: str, column: str, value: str) -> int:
    count = session.scalar(
        text(f"SELECT count(*) FROM {table} WHERE {column} = :value"),
        {"value": value},
    )
    assert count is not None
    return count


def test_added_portfolio_round_trips_with_decimal_precision(
    session: Session,
) -> None:
    instrument_a, instrument_b = _insert_instruments(session)
    portfolio = make_portfolio(
        [(instrument_a, "0.600000"), (instrument_b, "0.400000")],
        initial_capital="10000.123456",
        portfolio_id="portfolio-1",
    )
    repository = PortfolioRepository(session)

    repository.add(portfolio)
    session.expire_all()

    result = repository.get_by_id("portfolio-1")
    assert result == portfolio
    assert result is not None
    assert result.initial_capital == Decimal("10000.123456")
    assert [allocation.weight for allocation in result.allocations] == [
        Decimal("0.6"),
        Decimal("0.4"),
    ]


def test_get_by_id_returns_none_when_portfolio_does_not_exist(
    session: Session,
) -> None:
    assert PortfolioRepository(session).get_by_id("missing") is None


def test_allocations_are_loaded_ordered_by_instrument_id(
    session: Session,
) -> None:
    instrument_a, instrument_b = _insert_instruments(session)
    portfolio = make_portfolio(
        [(instrument_b, "0.4"), (instrument_a, "0.6")],
        portfolio_id="portfolio-1",
    )
    repository = PortfolioRepository(session)

    repository.add(portfolio)
    session.expire_all()

    result = repository.get_by_id("portfolio-1")
    assert result is not None
    assert [a.instrument.id for a in result.allocations] == ["inst-a", "inst-b"]


def test_add_rejects_duplicate_portfolio_id(session: Session) -> None:
    instrument_a, instrument_b = _insert_instruments(session)
    PortfolioRepository(session).add(
        make_portfolio(
            [(instrument_a, "0.6"), (instrument_b, "0.4")],
            portfolio_id="portfolio-1",
        )
    )

    # Raw SQL: a second ORM object with the same PK would fail inside the
    # session's identity map (FlushError) before reaching the database.
    with pytest.raises(IntegrityError):
        _insert_portfolio_row(session, portfolio_id="portfolio-1")


def test_add_rejects_nonexistent_instrument_foreign_key(
    session: Session,
) -> None:
    instrument_a, _ = _insert_instruments(session)
    missing_instrument = make_instrument("inst-missing", symbol="MISSING")
    portfolio = make_portfolio(
        [(instrument_a, "0.6"), (missing_instrument, "0.4")],
        portfolio_id="portfolio-1",
    )

    with pytest.raises(IntegrityError):
        PortfolioRepository(session).add(portfolio)


@pytest.mark.parametrize(
    ("overrides"),
    [
        {"initial_capital": "0"},
        {"initial_capital": "-100"},
        {"base_currency": "EUR"},
        {"strategy": "rebalance"},
    ],
    ids=["zero-capital", "negative-capital", "non-usd-currency", "other-strategy"],
)
def test_database_rejects_invalid_portfolio_via_raw_sql(
    session: Session,
    overrides: dict[str, str],
) -> None:
    with pytest.raises(IntegrityError):
        _insert_portfolio_row(session, **overrides)


@pytest.mark.parametrize("weight", ["0", "-0.1", "1.5"])
def test_database_rejects_weight_outside_range_via_raw_sql(
    session: Session,
    weight: str,
) -> None:
    instrument_a, _ = _insert_instruments(session)
    _insert_portfolio_row(session, portfolio_id="portfolio-1")

    with pytest.raises(IntegrityError):
        _insert_allocation_row(session, "portfolio-1", instrument_a.id, weight)


def test_database_rejects_duplicate_instrument_in_portfolio_via_raw_sql(
    session: Session,
) -> None:
    instrument_a, _ = _insert_instruments(session)
    _insert_portfolio_row(session, portfolio_id="portfolio-1")
    _insert_allocation_row(session, "portfolio-1", instrument_a.id, "0.5")

    with pytest.raises(IntegrityError):
        _insert_allocation_row(session, "portfolio-1", instrument_a.id, "0.5")


def test_database_rejects_allocation_for_nonexistent_portfolio(
    session: Session,
) -> None:
    instrument_a, _ = _insert_instruments(session)

    with pytest.raises(IntegrityError):
        _insert_allocation_row(session, "no-such-portfolio", instrument_a.id, "1")


def test_deleting_instrument_used_by_portfolio_is_restricted(
    session: Session,
) -> None:
    instrument_a, instrument_b = _insert_instruments(session)
    PortfolioRepository(session).add(
        make_portfolio(
            [(instrument_a, "0.6"), (instrument_b, "0.4")],
            portfolio_id="portfolio-1",
        )
    )

    with pytest.raises(IntegrityError):
        session.execute(
            text("DELETE FROM instruments WHERE id = :id"),
            {"id": instrument_a.id},
        )


def test_deleting_portfolio_cascades_to_allocations(session: Session) -> None:
    instrument_a, instrument_b = _insert_instruments(session)
    PortfolioRepository(session).add(
        make_portfolio(
            [(instrument_a, "0.6"), (instrument_b, "0.4")],
            portfolio_id="portfolio-1",
        )
    )
    assert _count(session, "portfolio_allocations", "portfolio_id", "portfolio-1") == 2

    session.execute(text("DELETE FROM portfolios WHERE id = 'portfolio-1'"))

    assert _count(session, "portfolio_allocations", "portfolio_id", "portfolio-1") == 0
