from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.fixtures.factories import make_instrument, make_price_series

from finscope.domain.instrument import Instrument
from finscope.market_data.models.price_series import PriceSeries
from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)
from finscope.persistence.repositories.price_point_repository import (
    PricePointRepository,
)


def _insert_instrument(session: Session) -> Instrument:
    instrument = make_instrument("inst-a", symbol="AAA")
    InstrumentRepository(session).add(instrument)
    return instrument


def test_upserted_series_round_trips_with_decimal_precision(
    session: Session,
) -> None:
    instrument = _insert_instrument(session)
    series = make_price_series(
        instrument,
        {
            date(2024, 1, 2): "123.456789",
            date(2024, 1, 3): "0.000001",
            date(2024, 1, 4): "987654321.123456",
        },
    )
    repository = PricePointRepository(session)

    repository.upsert_series(
        series,
        provider="test-provider",
        fetched_at=datetime(2024, 1, 5, tzinfo=UTC),
    )

    result = repository.get_series(
        instrument, date(2024, 1, 2), date(2024, 1, 4)
    )
    assert result == series
    assert result is not None
    assert [point.adjusted_close for point in result.points] == [
        Decimal("123.456789"),
        Decimal("0.000001"),
        Decimal("987654321.123456"),
    ]


def test_upserting_series_twice_is_idempotent(session: Session) -> None:
    instrument = _insert_instrument(session)
    series = make_price_series(
        instrument,
        {
            date(2024, 1, 2): "100.25",
            date(2024, 1, 3): "101.50",
            date(2024, 1, 4): "102.75",
        },
    )
    repository = PricePointRepository(session)
    fetched_at = datetime(2024, 1, 5, tzinfo=UTC)

    repository.upsert_series(series, "test-provider", fetched_at)
    repository.upsert_series(series, "test-provider", fetched_at)

    row_count = session.scalar(
        text(
            "SELECT count(*) FROM price_points "
            "WHERE instrument_id = :instrument_id"
        ),
        {"instrument_id": instrument.id},
    )
    assert row_count == 3


def test_upsert_updates_prices_and_provider_on_conflict(
    session: Session,
) -> None:
    instrument = _insert_instrument(session)
    repository = PricePointRepository(session)
    fetched_at = datetime(2024, 1, 5, tzinfo=UTC)
    original_series = make_price_series(
        instrument,
        {
            date(2024, 1, 2): "100.25",
            date(2024, 1, 3): "101.50",
        },
    )
    updated_series = make_price_series(
        instrument,
        {
            date(2024, 1, 2): "200.75",
            date(2024, 1, 3): "202.00",
        },
    )

    repository.upsert_series(original_series, "old-provider", fetched_at)
    repository.upsert_series(updated_series, "new-provider", fetched_at)

    assert repository.get_series(
        instrument, date(2024, 1, 2), date(2024, 1, 3)
    ) == updated_series
    providers = session.scalars(
        text(
            "SELECT provider FROM price_points "
            "WHERE instrument_id = :instrument_id ORDER BY price_date"
        ),
        {"instrument_id": instrument.id},
    ).all()
    assert providers == ["new-provider", "new-provider"]


def test_get_series_filters_to_inclusive_date_range(session: Session) -> None:
    instrument = _insert_instrument(session)
    series = make_price_series(
        instrument,
        {
            date(2024, 1, 2): "100",
            date(2024, 1, 3): "101",
            date(2024, 1, 4): "102",
        },
    )
    repository = PricePointRepository(session)
    repository.upsert_series(
        series,
        "test-provider",
        datetime(2024, 1, 5, tzinfo=UTC),
    )

    assert repository.get_series(
        instrument, date(2024, 1, 3), date(2024, 1, 4)
    ) == make_price_series(
        instrument,
        {
            date(2024, 1, 3): "101",
            date(2024, 1, 4): "102",
        },
    )


def test_get_series_returns_none_when_range_has_no_data(
    session: Session,
) -> None:
    instrument = _insert_instrument(session)
    series = make_price_series(
        instrument,
        {date(2024, 1, 2): "100"},
    )
    repository = PricePointRepository(session)
    repository.upsert_series(
        series,
        "test-provider",
        datetime(2024, 1, 5, tzinfo=UTC),
    )

    assert repository.get_series(
        instrument, date(2024, 2, 1), date(2024, 2, 2)
    ) is None


def test_upsert_rejects_nonexistent_instrument_foreign_key(
    session: Session,
) -> None:
    _insert_instrument(session)
    missing_instrument = make_instrument("inst-missing", symbol="MISSING")
    series = make_price_series(
        missing_instrument,
        {date(2024, 1, 2): "100"},
    )

    with pytest.raises(IntegrityError):
        PricePointRepository(session).upsert_series(
            series,
            "test-provider",
            datetime(2024, 1, 5, tzinfo=UTC),
        )


def test_database_rejects_non_positive_price_via_raw_sql(
    session: Session,
) -> None:
    instrument = _insert_instrument(session)

    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO price_points "
                "(instrument_id, price_date, adjusted_close, provider, fetched_at) "
                "VALUES (:instrument_id, :price_date, :adjusted_close, "
                ":provider, :fetched_at)"
            ),
            {
                "instrument_id": instrument.id,
                "price_date": date(2024, 1, 2),
                "adjusted_close": Decimal("0"),
                "provider": "test-provider",
                "fetched_at": datetime(2024, 1, 5, tzinfo=UTC),
            },
        )


def test_weekend_gap_is_not_filled_by_repository(session: Session) -> None:
    instrument = _insert_instrument(session)
    series = make_price_series(
        instrument,
        {
            date(2024, 1, 5): "100",
            date(2024, 1, 8): "101",
        },
    )
    repository = PricePointRepository(session)
    repository.upsert_series(
        series,
        "test-provider",
        datetime(2024, 1, 9, tzinfo=UTC),
    )

    assert repository.get_series(
        instrument, date(2024, 1, 5), date(2024, 1, 8)
    ) == series