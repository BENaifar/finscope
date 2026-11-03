from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.factories import make_instrument, make_price_series
from tests.fixtures.market_data_fakes import SpyProvider, make_provider

from finscope.domain.instrument import Instrument
from finscope.market_data.market_data_service import (
    MarketDataService,
    ProviderSource,
)
from finscope.market_data.nyse_trading_calendar import NyseTradingCalendar
from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)
from finscope.persistence.repositories.price_point_repository import (
    PricePointRepository,
)

NOW = datetime(2024, 2, 1, 12, 0, tzinfo=UTC)
# January 1 is a holiday and Jan 6 to 7 a weekend: sessions are 2, 3, 4, 5, 8.
PRICES = {2: "10", 3: "11", 4: "12", 5: "13", 8: "14"}


def _insert_instrument(session: Session) -> Instrument:
    instrument = make_instrument("inst-a", symbol="AAA")
    InstrumentRepository(session).add(instrument)
    return instrument


def _make_service(session: Session, spy: SpyProvider) -> MarketDataService:
    return MarketDataService(
        PricePointRepository(session),
        NyseTradingCalendar(),
        (ProviderSource("memory", spy),),
        clock=lambda: NOW,
    )


def test_first_request_fetches_and_the_second_is_served_from_the_database(
    session: Session,
) -> None:
    instrument = _insert_instrument(session)
    spy = SpyProvider(make_provider({"inst-a": PRICES}))
    service = _make_service(session, spy)

    first = service.get_price_series((instrument,), date(2024, 1, 1), date(2024, 1, 8))
    second = service.get_price_series(
        (instrument,), date(2024, 1, 1), date(2024, 1, 8)
    )

    assert first == second
    assert len(spy.calls) == 1
    providers = session.scalars(
        text("SELECT DISTINCT provider FROM price_points")
    ).all()
    assert providers == ["memory"]


def test_only_the_gap_left_in_the_database_is_fetched(session: Session) -> None:
    instrument = _insert_instrument(session)
    PricePointRepository(session).upsert_series(
        make_price_series(
            instrument,
            {
                date(2024, 1, 2): "10",
                date(2024, 1, 3): "11",
                date(2024, 1, 5): "13",
                date(2024, 1, 8): "14",
            },
        ),
        "seed",
        NOW,
    )
    spy = SpyProvider(make_provider({"inst-a": PRICES}))
    service = _make_service(session, spy)

    result = service.get_price_series(
        (instrument,), date(2024, 1, 2), date(2024, 1, 8)
    )

    assert spy.calls == [(("inst-a",), date(2024, 1, 4), date(2024, 1, 4))]
    assert len(result[0].points) == 5
    provider_by_date = dict(
        session.execute(
            text("SELECT price_date, provider FROM price_points")
        ).all()
    )
    assert provider_by_date[date(2024, 1, 4)] == "memory"
    assert provider_by_date[date(2024, 1, 3)] == "seed"
