import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.fixtures.factories import make_instrument

from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)


def test_added_instrument_can_be_read_back_by_id(session: Session) -> None:
    repository = InstrumentRepository(session)
    instrument = make_instrument("inst-a", symbol="AAA")

    repository.add(instrument)

    assert repository.get_by_id("inst-a") == instrument


def test_instrument_can_be_found_by_symbol(session: Session) -> None:
    repository = InstrumentRepository(session)
    instrument = make_instrument("inst-a", symbol="AAA")
    repository.add(instrument)

    assert repository.get_by_symbol("AAA") == instrument


def test_missing_instrument_returns_none(session: Session) -> None:
    repository = InstrumentRepository(session)

    assert repository.get_by_id("nope") is None
    assert repository.get_by_symbol("NOPE") is None


def test_duplicate_symbol_is_rejected_by_the_database(session: Session) -> None:
    repository = InstrumentRepository(session)
    repository.add(make_instrument("inst-a", symbol="AAA"))

    with pytest.raises(IntegrityError):
        repository.add(make_instrument("inst-b", symbol="AAA"))


def test_non_usd_currency_is_rejected_by_the_database(session: Session) -> None:
    repository = InstrumentRepository(session)
    instrument = make_instrument("inst-a", symbol="AAA", currency="EUR")

    with pytest.raises(IntegrityError):
        repository.add(instrument)

def test_blank_symbol_is_rejected_by_the_database(session: Session) -> None:
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "insert into instruments (id, symbol, name, currency) "
                "values ('i1', '   ', 'Name', 'USD')"
            )
        )

