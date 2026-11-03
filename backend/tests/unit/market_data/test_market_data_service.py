from datetime import UTC, datetime
from decimal import Decimal

import pytest
from tests.fixtures.factories import jan, make_instrument
from tests.fixtures.market_data_fakes import (
    FailingProvider,
    FakePriceStore,
    FixedCalendar,
    SpyProvider,
    make_provider,
)

from finscope.market_data.errors import (
    IncompleteMarketDataError,
    InvalidDateRangeError,
    MarketDataError,
    PriceDataNotFoundError,
)
from finscope.market_data.market_data_service import (
    MarketDataService,
    ProviderSource,
)
from finscope.market_data.providers.price_history_provider import (
    PriceHistoryProvider,
)

NOW = datetime(2024, 2, 1, 12, 0, tzinfo=UTC)
A = make_instrument("inst-a", symbol="AAA")
B = make_instrument("inst-b", symbol="BBB")

# Jan 6 and 7 are a weekend, so the sessions in January 2..8 are 2, 3, 4, 5, 8.
SESSIONS = (2, 3, 4, 5, 8)
ALL_SESSIONS_PRICES = {2: "10", 3: "11", 4: "12", 5: "13", 8: "14"}


def make_service(
    store: FakePriceStore, *sources: ProviderSource, days: tuple[int, ...] = SESSIONS
) -> MarketDataService:
    return MarketDataService(
        store, FixedCalendar(*days), tuple(sources), clock=lambda: NOW
    )


def test_serves_from_the_store_without_calling_providers() -> None:
    store = FakePriceStore()
    store.seed(A, ALL_SESSIONS_PRICES)
    spy = SpyProvider(make_provider({"inst-a": ALL_SESSIONS_PRICES}))
    service = make_service(store, ProviderSource("csv", spy))

    result = service.get_price_series((A,), jan(2), jan(8))

    assert spy.calls == []
    assert store.upserts == []
    assert [point.date for point in result[0].points] == [jan(d) for d in SESSIONS]


def test_fetches_persists_and_returns_when_nothing_is_stored() -> None:
    store = FakePriceStore()
    spy = SpyProvider(make_provider({"inst-a": ALL_SESSIONS_PRICES}))
    service = make_service(store, ProviderSource("csv", spy))

    result = service.get_price_series((A,), jan(2), jan(8))

    assert spy.calls == [(("inst-a",), jan(2), jan(8))]
    assert store.upserts == [("csv", tuple(jan(d) for d in SESSIONS), NOW)]
    assert result[0].get_price_on(jan(4)) == Decimal("12")


def test_fetches_only_the_missing_range_and_never_overwrites_stored_prices() -> None:
    store = FakePriceStore()
    store.seed(A, {2: "10", 8: "14"})
    store.seed(A, {4: "12"}, provider="legacy")
    spy = SpyProvider(
        make_provider({"inst-a": {2: "99", 3: "99", 4: "99", 5: "99", 8: "99"}})
    )
    service = make_service(store, ProviderSource("csv", spy))

    result = service.get_price_series((A,), jan(2), jan(8))

    assert spy.calls == [(("inst-a",), jan(3), jan(5))]
    assert store.upserts == [("csv", (jan(3), jan(5)), NOW)]
    assert store.rows[("inst-a", jan(4))] == (Decimal("12"), "legacy")
    assert result[0].get_price_on(jan(3)) == Decimal("99")


def test_falls_back_to_the_next_provider_when_one_has_no_data() -> None:
    store = FakePriceStore()
    empty = SpyProvider(make_provider({}))
    full = SpyProvider(make_provider({"inst-a": ALL_SESSIONS_PRICES}))
    service = make_service(
        store, ProviderSource("csv", empty), ProviderSource("yahoo", full)
    )

    service.get_price_series((A,), jan(2), jan(8))

    assert len(empty.calls) == 1
    assert len(full.calls) == 1
    assert [upsert[0] for upsert in store.upserts] == ["yahoo"]


def test_a_second_provider_is_asked_only_for_what_is_still_missing() -> None:
    store = FakePriceStore()
    csv = make_provider({"inst-a": {2: "10", 3: "11"}})
    yahoo = SpyProvider(make_provider({"inst-a": ALL_SESSIONS_PRICES}))
    service = make_service(
        store, ProviderSource("csv", csv), ProviderSource("yahoo", yahoo)
    )

    service.get_price_series((A,), jan(2), jan(8))

    assert yahoo.calls == [(("inst-a",), jan(4), jan(8))]
    assert store.upserts == [
        ("csv", (jan(2), jan(3)), NOW),
        ("yahoo", (jan(4), jan(5), jan(8)), NOW),
    ]


def test_stops_asking_providers_once_the_range_is_complete() -> None:
    store = FakePriceStore()
    csv = make_provider({"inst-a": ALL_SESSIONS_PRICES})
    yahoo = SpyProvider(make_provider({"inst-a": ALL_SESSIONS_PRICES}))
    service = make_service(
        store, ProviderSource("csv", csv), ProviderSource("yahoo", yahoo)
    )

    service.get_price_series((A,), jan(2), jan(8))

    assert yahoo.calls == []


def test_raises_with_the_missing_dates_when_a_hole_cannot_be_filled() -> None:
    store = FakePriceStore()
    csv = make_provider({"inst-a": {2: "10", 3: "11", 8: "14"}})
    yahoo = make_provider({})
    service = make_service(
        store, ProviderSource("csv", csv), ProviderSource("yahoo", yahoo)
    )

    with pytest.raises(IncompleteMarketDataError) as error:
        service.get_price_series((A,), jan(2), jan(8))

    assert error.value.instrument == A
    assert error.value.missing_dates == (jan(4), jan(5))


def test_dates_before_the_first_available_price_are_tolerated() -> None:
    store = FakePriceStore()
    csv = make_provider({"inst-a": {4: "12", 5: "13", 8: "14"}})
    service = make_service(store, ProviderSource("csv", csv))

    result = service.get_price_series((A,), jan(2), jan(8))

    assert [point.date for point in result[0].points] == [jan(4), jan(5), jan(8)]


def test_a_missing_tail_is_never_tolerated() -> None:
    store = FakePriceStore()
    csv = make_provider({"inst-a": {2: "10", 3: "11", 4: "12", 5: "13"}})
    service = make_service(store, ProviderSource("csv", csv))

    with pytest.raises(IncompleteMarketDataError) as error:
        service.get_price_series((A,), jan(2), jan(8))

    assert error.value.missing_dates == (jan(8),)


def test_raises_not_found_when_no_source_has_any_data() -> None:
    store = FakePriceStore()
    service = make_service(
        store,
        ProviderSource("csv", make_provider({})),
        ProviderSource("yahoo", make_provider({})),
    )

    with pytest.raises(PriceDataNotFoundError):
        service.get_price_series((A,), jan(2), jan(8))


def test_a_real_provider_failure_propagates_and_skips_later_providers() -> None:
    store = FakePriceStore()
    later = SpyProvider(make_provider({"inst-a": ALL_SESSIONS_PRICES}))
    service = make_service(
        store,
        ProviderSource("yahoo", FailingProvider("rate limited")),
        ProviderSource("csv", later),
    )

    with pytest.raises(MarketDataError, match="rate limited"):
        service.get_price_series((A,), jan(2), jan(8))

    assert later.calls == []


def test_dates_the_calendar_does_not_expect_are_not_stored() -> None:
    store = FakePriceStore()
    csv = make_provider({"inst-a": {**ALL_SESSIONS_PRICES, 6: "99"}})
    service = make_service(store, ProviderSource("csv", csv))

    service.get_price_series((A,), jan(2), jan(8))

    assert ("inst-a", jan(6)) not in store.rows


def test_each_instrument_is_handled_independently_and_in_order() -> None:
    store = FakePriceStore()
    store.seed(A, ALL_SESSIONS_PRICES)
    spy = SpyProvider(
        make_provider(
            {"inst-a": ALL_SESSIONS_PRICES, "inst-b": ALL_SESSIONS_PRICES}
        )
    )
    service = make_service(store, ProviderSource("csv", spy))

    result = service.get_price_series((B, A), jan(2), jan(8))

    assert [series.instrument for series in result] == [B, A]
    assert spy.calls == [(("inst-b",), jan(2), jan(8))]


def test_inverted_range_raises() -> None:
    service = make_service(FakePriceStore())

    with pytest.raises(InvalidDateRangeError):
        service.get_price_series((A,), jan(8), jan(2))


def test_range_without_sessions_raises_not_found() -> None:
    service = make_service(
        FakePriceStore(),
        ProviderSource("csv", make_provider({"inst-a": ALL_SESSIONS_PRICES})),
    )

    with pytest.raises(PriceDataNotFoundError):
        service.get_price_series((A,), jan(6), jan(7))


def test_can_be_used_wherever_a_price_history_provider_is_expected() -> None:
    store = FakePriceStore()
    store.seed(A, ALL_SESSIONS_PRICES)
    provider: PriceHistoryProvider = make_service(store)

    result = provider.get_price_series((A,), jan(2), jan(8))

    assert len(result) == 1
