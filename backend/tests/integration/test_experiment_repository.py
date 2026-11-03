from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.fixtures.factories import jan, make_config, make_instrument, make_portfolio

from finscope.persistence.repositories.experiment_repository import (
    ExperimentRepository,
)
from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)
from finscope.persistence.repositories.portfolio_repository import (
    PortfolioRepository,
)


def _insert_portfolio(session: Session) -> None:
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    instruments = InstrumentRepository(session)
    instruments.add(instrument_a)
    instruments.add(instrument_b)
    PortfolioRepository(session).add(
        make_portfolio([(instrument_a, "0.6"), (instrument_b, "0.4")])
    )


def test_experiment_round_trips(session: Session) -> None:
    _insert_portfolio(session)
    config = make_config(jan(1), jan(31))
    repository = ExperimentRepository(session)

    repository.add(config)

    assert repository.get_by_id(config.id) == config


def test_get_by_id_returns_none_for_unknown_experiment(session: Session) -> None:
    assert ExperimentRepository(session).get_by_id("missing") is None


def test_duplicate_experiment_id_is_rejected(session: Session) -> None:
    _insert_portfolio(session)
    repository = ExperimentRepository(session)
    repository.add(make_config(jan(1), jan(31)))

    with pytest.raises(IntegrityError):
        repository.add(make_config(jan(2), jan(30)))


def test_experiment_requires_an_existing_portfolio(session: Session) -> None:
    with pytest.raises(IntegrityError):
        ExperimentRepository(session).add(
            make_config(jan(1), jan(31), portfolio_id="no-such-portfolio")
        )


def test_portfolio_with_experiments_cannot_be_deleted(session: Session) -> None:
    _insert_portfolio(session)
    ExperimentRepository(session).add(make_config(jan(1), jan(31)))

    with pytest.raises(IntegrityError):
        session.execute(text("DELETE FROM portfolios WHERE id = 'test-portfolio'"))


@pytest.mark.parametrize(
    ("start_date", "end_date", "price_convention"),
    [
        (date(2024, 1, 31), date(2024, 1, 1), "adjusted_close"),
        (date(2024, 1, 1), date(2024, 1, 1), "adjusted_close"),
        (date(2024, 1, 1), date(2024, 1, 31), "close"),
    ],
    ids=["start-after-end", "start-equals-end", "unsupported-convention"],
)
def test_database_rejects_invalid_experiment_via_raw_sql(
    session: Session,
    start_date: date,
    end_date: date,
    price_convention: str,
) -> None:
    _insert_portfolio(session)

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO experiments "
                "(id, portfolio_id, start_date, end_date, price_convention) "
                "VALUES ('exp-sql', 'test-portfolio', :start_date, :end_date, "
                ":price_convention)"
            ),
            {
                "start_date": start_date,
                "end_date": end_date,
                "price_convention": price_convention,
            },
        )