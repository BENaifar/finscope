import re
from datetime import date
from decimal import Decimal

import pytest

from src.finscope.analytics.models.portfolio_value_point import (
    PortfolioValuePoint,
)
from src.finscope.analytics.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from src.finscope.domain.experiment_config import ExperimentConfig
from src.finscope.domain.instrument import Instrument
from src.finscope.domain.portfolio import Portfolio
from src.finscope.market_data.models.price_series import PriceSeries
from tests.fixtures.factories import (
    jan,
    make_config,
    make_instrument,
    make_portfolio,
    make_price_series,
)


def test_single_instrument_value_tracks_price_ratio(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
) -> None:
    price_series = (
        make_price_series(
            instrument_a,
            {jan(1): "100", jan(2): "110", jan(3): "121"},
        ),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        default_config,
        price_series,
    )

    assert [point.total_value for point in result] == [
        Decimal("1000"),
        Decimal("1100"),
        Decimal("1210"),
    ]


def test_two_instruments_use_fixed_initial_quantities(
    valuation_service: PortfolioValuationService,
    two_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> None:
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
        make_price_series(instrument_b, {jan(1): "50", jan(2): "40"}),
    )

    result = valuation_service.calculate(
        two_asset_portfolio,
        default_config,
        price_series,
    )

    assert [point.total_value for point in result] == [
        Decimal("1000"),
        Decimal("980"),
    ]


def test_buy_and_hold_does_not_rebalance(
    valuation_service: PortfolioValuationService,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> None:
    portfolio = make_portfolio(
        ((instrument_a, "0.5"), (instrument_b, "0.5")),
    )
    price_series = (
        make_price_series(
            instrument_a,
            {jan(1): "100", jan(2): "200", jan(3): "100"},
        ),
        make_price_series(
            instrument_b,
            {jan(1): "100", jan(2): "100", jan(3): "50"},
        ),
    )

    result = valuation_service.calculate(portfolio, default_config, price_series)

    assert [point.total_value for point in result] == [
        Decimal("1000"),
        Decimal("1500"),
        Decimal("750"),
    ]


def test_initial_value_equals_initial_capital_with_non_divisible_prices(
    valuation_service: PortfolioValuationService,
    default_config: ExperimentConfig,
) -> None:
    instrument_a = make_instrument("inst-a")
    instrument_b = make_instrument("inst-b")
    instrument_c = make_instrument("inst-c")
    portfolio = make_portfolio(
        (
            (instrument_a, "0.5"),
            (instrument_b, "0.3"),
            (instrument_c, "0.2"),
        ),
        initial_capital="10000",
    )
    price_series = (
        make_price_series(instrument_a, {jan(1): "7", jan(2): "8"}),
        make_price_series(instrument_b, {jan(1): "3", jan(2): "4"}),
        make_price_series(instrument_c, {jan(1): "13", jan(2): "14"}),
    )

    result = valuation_service.calculate(portfolio, default_config, price_series)

    assert result[0].total_value == pytest.approx(
        Decimal("10000"),
        abs=Decimal("1e-9"),
    )


def test_returns_one_usd_point_per_date_in_ascending_order(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
) -> None:
    price_series = (
        make_price_series(
            instrument_a,
            {jan(3): "121", jan(1): "100", jan(2): "110"},
        ),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        default_config,
        price_series,
    )

    assert isinstance(result, tuple)
    assert isinstance(result[0], PortfolioValuePoint)
    assert isinstance(result[1], PortfolioValuePoint)
    assert isinstance(result[2], PortfolioValuePoint)
    assert [point.valuation_date for point in result] == [
        jan(1),
        jan(2),
        jan(3),
    ]
    assert result[0].valuation_date < result[1].valuation_date
    assert result[1].valuation_date < result[2].valuation_date
    assert [point.currency for point in result] == ["USD", "USD", "USD"]


def test_result_does_not_depend_on_price_series_order(
    valuation_service: PortfolioValuationService,
    two_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> None:
    series_a = make_price_series(instrument_a, {jan(1): "100", jan(2): "110"})
    series_b = make_price_series(instrument_b, {jan(1): "50", jan(2): "40"})

    result_ab = valuation_service.calculate(
        two_asset_portfolio,
        default_config,
        (series_a, series_b),
    )
    result_ba = valuation_service.calculate(
        two_asset_portfolio,
        default_config,
        (series_b, series_a),
    )

    assert result_ab == result_ba


def test_ignores_price_series_for_instruments_outside_portfolio(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
) -> None:
    outside_instrument = make_instrument("outside")
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
        make_price_series(
            outside_instrument,
            {jan(1): "10", jan(2): "11", jan(15): "15"},
        ),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        default_config,
        price_series,
    )

    assert [point.valuation_date for point in result] == [jan(1), jan(2)]


def test_includes_points_on_start_and_end_dates(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    instrument_a: Instrument,
) -> None:
    config = make_config(jan(2), jan(4))
    price_series = (
        make_price_series(
            instrument_a,
            {jan(2): "100", jan(3): "110", jan(4): "120"},
        ),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        config,
        price_series,
    )

    assert [point.valuation_date for point in result] == [
        jan(2),
        jan(3),
        jan(4),
    ]


def test_excludes_points_outside_period(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    instrument_a: Instrument,
) -> None:
    config = make_config(jan(3), jan(4))
    price_series = (
        make_price_series(
            instrument_a,
            {
                jan(1): "100",
                jan(2): "110",
                jan(3): "120",
                jan(4): "130",
                jan(5): "140",
                jan(6): "150",
            },
        ),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        config,
        price_series,
    )

    assert [point.valuation_date for point in result] == [jan(3), jan(4)]


def test_initial_quantities_ignore_pre_period_prices(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    instrument_a: Instrument,
) -> None:
    config = make_config(jan(2), jan(3))
    price_series = (
        make_price_series(
            instrument_a,
            {jan(1): "50", jan(2): "100", jan(3): "200"},
        ),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        config,
        price_series,
    )

    assert [point.total_value for point in result] == [
        Decimal("1000"),
        Decimal("2000"),
    ]


def test_initial_allocation_uses_first_available_date_after_start(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    instrument_a: Instrument,
) -> None:
    config = make_config(jan(1), jan(10))
    price_series = (
        make_price_series(instrument_a, {jan(3): "100", jan(4): "200"}),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        config,
        price_series,
    )

    assert [point.valuation_date for point in result] == [jan(3), jan(4)]
    assert [point.total_value for point in result] == [
        Decimal("1000"),
        Decimal("2000"),
    ]


def test_single_date_in_period_returns_initial_capital(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    instrument_a: Instrument,
) -> None:
    config = make_config(jan(1), jan(3))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(5): "110"}),
    )

    result = valuation_service.calculate(
        single_asset_portfolio,
        config,
        price_series,
    )

    assert len(result) == 1
    assert result[0].valuation_date == jan(1)
    assert result[0].total_value == Decimal("1000")


def test_raises_when_no_price_series_provided(
    valuation_service: PortfolioValuationService,
    default_config: ExperimentConfig,
) -> None:
    zeta = make_instrument("zeta")
    alpha = make_instrument("alpha")
    portfolio = make_portfolio(((zeta, "0.5"), (alpha, "0.5")))

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Missing price series for portfolio instruments: alpha, zeta"
        ),
    ):
        valuation_service.calculate(portfolio, default_config, ())


def test_raises_when_one_instrument_has_no_series(
    valuation_service: PortfolioValuationService,
    two_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
) -> None:
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )

    with pytest.raises(
        ValueError,
        match=re.escape("Missing price series for portfolio instruments: inst-b"),
    ) as error:
        valuation_service.calculate(
            two_asset_portfolio,
            default_config,
            price_series,
        )

    assert "inst-a" not in str(error.value)


def test_raises_when_instrument_has_multiple_series(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
) -> None:
    price_series = (
        make_price_series(instrument_a, {jan(1): "100"}),
        make_price_series(instrument_a, {jan(2): "110"}),
    )

    with pytest.raises(
        ValueError,
        match=re.escape("Multiple price series found for instrument inst-a"),
    ):
        valuation_service.calculate(
            single_asset_portfolio,
            default_config,
            price_series,
        )


def test_raises_when_no_prices_fall_within_period(
    valuation_service: PortfolioValuationService,
    single_asset_portfolio: Portfolio,
    instrument_a: Instrument,
) -> None:
    config = make_config(jan(10), jan(20))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "No price data found within the configured valuation period"
        ),
    ):
        valuation_service.calculate(single_asset_portfolio, config, price_series)


@pytest.mark.parametrize(
    ("prices_b", "missing_date"),
    [
        ({jan(2): "50", jan(3): "50"}, "2024-01-01"),
        ({jan(1): "50", jan(3): "50"}, "2024-01-02"),
        ({jan(1): "50", jan(2): "50"}, "2024-01-03"),
    ],
)
def test_raises_when_instrument_missing_price_on_a_valuation_date(
    valuation_service: PortfolioValuationService,
    default_config: ExperimentConfig,
    instrument_a: Instrument,
    instrument_b: Instrument,
    prices_b: dict[date, str],
    missing_date: str,
) -> None:
    portfolio = make_portfolio(
        ((instrument_a, "0.5"), (instrument_b, "0.5")),
    )
    price_series = (
        make_price_series(
            instrument_a,
            {jan(1): "100", jan(2): "100", jan(3): "100"},
        ),
        make_price_series(instrument_b, prices_b),
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            f"Missing price for instrument inst-b on {missing_date}"
        ),
    ):
        valuation_service.calculate(portfolio, default_config, price_series)


def test_raises_when_instrument_has_no_prices_inside_period(
    valuation_service: PortfolioValuationService,
    instrument_a: Instrument,
    instrument_b: Instrument,
) -> None:
    config = make_config(jan(1), jan(10))
    portfolio = make_portfolio(
        ((instrument_a, "0.5"), (instrument_b, "0.5")),
    )
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
        make_price_series(instrument_b, {jan(20): "50", jan(21): "60"}),
    )

    with pytest.raises(
        ValueError,
        match=re.escape("Missing price for instrument inst-b on 2024-01-01"),
    ):
        valuation_service.calculate(portfolio, config, price_series)