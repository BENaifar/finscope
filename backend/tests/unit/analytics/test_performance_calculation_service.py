from datetime import date
from decimal import Decimal

import pytest

from finscope.analytics.models.portfolio_value_point import (
    PortfolioValuePoint,
)
from finscope.analytics.services.performance_calculation_service import (
    PerformanceCalculationService,
)


@pytest.fixture
def service() -> PerformanceCalculationService:
    return PerformanceCalculationService()


def make_point(day: int, value: str) -> PortfolioValuePoint:
    return PortfolioValuePoint(
        valuation_date=date(2026, 1, day),
        total_value=Decimal(value),
    )


def make_series(*values: str) -> tuple[PortfolioValuePoint, ...]:
    """Build points on consecutive days starting 2026-01-01."""
    return tuple(
        make_point(day, value) for day, value in enumerate(values, start=1)
    )


# 1. Total return and P&L


@pytest.mark.parametrize(
    ("initial", "final", "expected_pnl", "expected_return"),
    [
        ("100", "110", 10.0, 0.10),
        ("100", "80", -20.0, -0.20),
        ("100", "100", 0.0, 0.0),
    ],
)
def test_calculates_total_return_and_pnl(
    service: PerformanceCalculationService,
    initial: str,
    final: str,
    expected_pnl: float,
    expected_return: float,
) -> None:
    result = service.calculate(make_series(initial, final))

    assert result.initial_value == pytest.approx(float(initial))
    assert result.final_value == pytest.approx(float(final))
    assert result.pnl == pytest.approx(expected_pnl)
    assert result.total_return == pytest.approx(expected_return)


def test_total_return_uses_first_and_last_values_only(
    service: PerformanceCalculationService,
) -> None:
    result = service.calculate(make_series("100", "150", "60", "110"))

    assert result.pnl == pytest.approx(10.0)
    assert result.total_return == pytest.approx(0.10)


# 2. Best period return


def test_finds_best_period_return_with_mixed_returns(
    service: PerformanceCalculationService,
) -> None:
    # +10%, -20%, +12.5%
    result = service.calculate(make_series("100", "110", "88", "99"))

    assert result.best_daily_return == pytest.approx(0.125)
    assert result.best_daily_return_date == date(2026, 1, 4)


def test_best_period_return_can_be_in_the_first_period(
    service: PerformanceCalculationService,
) -> None:
    # +20%, -5%, +2.63%
    result = service.calculate(make_series("100", "120", "114", "117"))

    assert result.best_daily_return == pytest.approx(0.20)
    assert result.best_daily_return_date == date(2026, 1, 2)


def test_best_period_return_is_least_negative_when_all_returns_are_losses(
    service: PerformanceCalculationService,
) -> None:
    # -10%, -5.56%
    result = service.calculate(make_series("100", "90", "85"))

    assert result.best_daily_return == pytest.approx(-5 / 90)
    assert result.best_daily_return_date == date(2026, 1, 3)


def test_best_period_return_tie_resolves_to_earliest_date(
    service: PerformanceCalculationService,
) -> None:
    # +10%, +10%
    result = service.calculate(make_series("100", "110", "121"))

    assert result.best_daily_return == pytest.approx(0.10)
    assert result.best_daily_return_date == date(2026, 1, 2)


# 3. Lowest value date


def test_finds_lowest_value_date(
    service: PerformanceCalculationService,
) -> None:
    result = service.calculate(make_series("100", "110", "88", "99"))

    assert result.lowest_portfolio_value_date == date(2026, 1, 3)


def test_lowest_value_tie_resolves_to_earliest_date(
    service: PerformanceCalculationService,
) -> None:
    result = service.calculate(make_series("100", "80", "90", "80"))

    assert result.lowest_portfolio_value_date == date(2026, 1, 2)


# 4. Non-increasing dates


def test_rejects_duplicate_dates(
    service: PerformanceCalculationService,
) -> None:
    portfolio_values = (make_point(1, "100"), make_point(1, "110"))

    with pytest.raises(ValueError, match="increasing date order"):
        service.calculate(portfolio_values)


def test_rejects_dates_in_reverse_order(
    service: PerformanceCalculationService,
) -> None:
    portfolio_values = (make_point(2, "100"), make_point(1, "110"))

    with pytest.raises(ValueError, match="increasing date order"):
        service.calculate(portfolio_values)


def test_rejects_out_of_order_date_in_the_middle_of_series(
    service: PerformanceCalculationService,
) -> None:
    portfolio_values = (
        make_point(1, "100"),
        make_point(3, "110"),
        make_point(2, "105"),
        make_point(4, "120"),
    )

    with pytest.raises(ValueError, match="increasing date order"):
        service.calculate(portfolio_values)


# 5. Zero and negative values


@pytest.mark.parametrize("bad_value", ["0", "-1"])
@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_rejects_nonpositive_portfolio_values(
    service: PerformanceCalculationService,
    bad_value: str,
    position: str,
) -> None:
    values = {
        "first": (bad_value, "100", "110"),
        "middle": ("100", bad_value, "110"),
        "last": ("100", "110", bad_value),
    }[position]

    with pytest.raises(ValueError, match="must be positive"):
        service.calculate(make_series(*values))


# 6. Fewer than two points


def test_rejects_empty_series(
    service: PerformanceCalculationService,
) -> None:
    with pytest.raises(ValueError, match="At least two"):
        service.calculate(())


def test_rejects_single_observation(
    service: PerformanceCalculationService,
) -> None:
    with pytest.raises(ValueError, match="At least two"):
        service.calculate(make_series("100"))


def test_accepts_exactly_two_points(
    service: PerformanceCalculationService,
) -> None:
    result = service.calculate(make_series("100", "110"))

    assert result.total_return == pytest.approx(0.10)


# 7. Declining series


def test_declining_series_has_positive_drawdown_with_correct_dates(
    service: PerformanceCalculationService,
) -> None:
    result = service.calculate(make_series("100", "90", "80", "70"))

    assert result.maximum_drawdown == pytest.approx(0.30)
    assert result.maximum_drawdown_peak_date == date(2026, 1, 1)
    assert result.maximum_drawdown_trough_date == date(2026, 1, 4)
    assert result.total_return == pytest.approx(-0.30)
    assert result.pnl == pytest.approx(-30.0)


def test_drawdown_peak_and_trough_with_recovery(
    service: PerformanceCalculationService,
) -> None:
    # Peak 110 on Jan 2, trough 88 on Jan 3, partial recovery to 99
    result = service.calculate(make_series("100", "110", "88", "99"))

    assert result.maximum_drawdown == pytest.approx(0.20)
    assert result.maximum_drawdown_peak_date == date(2026, 1, 2)
    assert result.maximum_drawdown_trough_date == date(2026, 1, 3)