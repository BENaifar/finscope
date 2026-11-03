from datetime import date

from finscope.market_data.coverage import find_missing_dates
from finscope.market_data.nyse_trading_calendar import NyseTradingCalendar

JAN_2 = date(2024, 1, 2)
JAN_3 = date(2024, 1, 3)
JAN_4 = date(2024, 1, 4)
JAN_5 = date(2024, 1, 5)


def test_returns_empty_tuple_when_every_expected_date_is_stored() -> None:
    expected = (JAN_2, JAN_3, JAN_4)

    assert find_missing_dates(expected, frozenset(expected)) == ()


def test_returns_every_expected_date_when_nothing_is_stored() -> None:
    assert find_missing_dates((JAN_2, JAN_3, JAN_4), frozenset()) == (
        JAN_2,
        JAN_3,
        JAN_4,
    )


def test_detects_a_hole_in_the_middle_of_the_range() -> None:
    expected = (JAN_2, JAN_3, JAN_4, JAN_5)
    stored = frozenset({JAN_2, JAN_5})

    assert find_missing_dates(expected, stored) == (JAN_3, JAN_4)


def test_stored_dates_outside_expected_are_ignored() -> None:
    expected = (JAN_2, JAN_3)
    stored = frozenset({JAN_3, date(2024, 1, 6)})

    assert find_missing_dates(expected, stored) == (JAN_2,)


def test_result_is_ascending_without_duplicates_for_unordered_input() -> None:
    expected = (JAN_4, JAN_2, JAN_4, JAN_3)

    assert find_missing_dates(expected, frozenset({JAN_3})) == (JAN_2, JAN_4)


def test_empty_expected_range_has_nothing_missing() -> None:
    assert find_missing_dates((), frozenset({JAN_2})) == ()


def test_holidays_and_weekends_are_not_reported_as_missing() -> None:
    calendar = NyseTradingCalendar()
    expected = calendar.expected_dates(date(2024, 1, 1), date(2024, 1, 8))
    stored = frozenset({JAN_2, JAN_3, JAN_4, JAN_5, date(2024, 1, 8)})

    assert find_missing_dates(expected, stored) == ()


def test_a_genuinely_missing_session_is_reported_next_to_a_holiday() -> None:
    calendar = NyseTradingCalendar()
    expected = calendar.expected_dates(date(2024, 1, 1), date(2024, 1, 8))
    stored = frozenset({JAN_2, JAN_3, JAN_5, date(2024, 1, 8)})

    assert find_missing_dates(expected, stored) == (JAN_4,)
