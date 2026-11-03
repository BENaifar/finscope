from datetime import date

import pytest

from finscope.market_data.errors import CalendarRangeError, InvalidDateRangeError
from finscope.market_data.nyse_trading_calendar import NyseTradingCalendar
from finscope.market_data.trading_calendar import TradingCalendar


@pytest.fixture(scope="module")
def calendar() -> TradingCalendar:
    return NyseTradingCalendar()


def test_normal_weekday_is_expected(calendar: TradingCalendar) -> None:
    assert calendar.expected_dates(date(2024, 1, 3), date(2024, 1, 3)) == (
        date(2024, 1, 3),
    )


def test_regular_week_skips_new_years_day_and_weekend(
    calendar: TradingCalendar,
) -> None:
    assert calendar.expected_dates(date(2024, 1, 1), date(2024, 1, 8)) == (
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 4),
        date(2024, 1, 5),
        date(2024, 1, 8),
    )


def test_weekend_only_range_has_no_expected_dates(
    calendar: TradingCalendar,
) -> None:
    assert calendar.expected_dates(date(2024, 1, 6), date(2024, 1, 7)) == ()


@pytest.mark.parametrize(
    "holiday",
    [
        date(2024, 1, 1),
        date(2024, 3, 29),
        date(2024, 7, 4),
        date(2024, 11, 28),
        date(2024, 12, 25),
    ],
    ids=["new-years", "good-friday", "july-4", "thanksgiving", "christmas"],
)
def test_regular_market_holidays_are_not_expected(
    calendar: TradingCalendar, holiday: date
) -> None:
    assert calendar.expected_dates(holiday, holiday) == ()


@pytest.mark.parametrize(
    "closure",
    [date(2001, 9, 12), date(2012, 10, 29), date(2025, 1, 9)],
    ids=["september-11-aftermath", "hurricane-sandy", "carter-day-of-mourning"],
)
def test_special_closures_are_not_expected(
    calendar: TradingCalendar, closure: date
) -> None:
    assert calendar.expected_dates(closure, closure) == ()


@pytest.mark.parametrize(
    "early_close",
    [date(2024, 7, 3), date(2024, 11, 29)],
    ids=["july-3", "day-after-thanksgiving"],
)
def test_early_close_days_are_still_expected(
    calendar: TradingCalendar, early_close: date
) -> None:
    assert calendar.expected_dates(early_close, early_close) == (early_close,)


def test_range_is_inclusive_at_both_ends(calendar: TradingCalendar) -> None:
    result = calendar.expected_dates(date(2024, 1, 2), date(2024, 1, 4))

    assert result == (date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4))


def test_full_year_session_counts(calendar: TradingCalendar) -> None:
    assert len(calendar.expected_dates(date(2023, 1, 1), date(2023, 12, 31))) == 250
    assert len(calendar.expected_dates(date(2024, 1, 1), date(2024, 12, 31))) == 252


def test_result_is_ascending_tuple_of_plain_dates(
    calendar: TradingCalendar,
) -> None:
    result = calendar.expected_dates(date(2024, 1, 1), date(2024, 3, 31))

    assert isinstance(result, tuple)
    assert all(type(item) is date for item in result)
    assert list(result) == sorted(result)


def test_inverted_range_raises(calendar: TradingCalendar) -> None:
    with pytest.raises(InvalidDateRangeError):
        calendar.expected_dates(date(2024, 2, 1), date(2024, 1, 1))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (date(1980, 1, 2), date(1980, 1, 10)),
        (date(2024, 1, 2), date(2100, 1, 1)),
    ],
    ids=["before-supported-range", "after-supported-range"],
)
def test_dates_outside_supported_range_raise(
    calendar: TradingCalendar, start: date, end: date
) -> None:
    with pytest.raises(CalendarRangeError):
        calendar.expected_dates(start, end)
