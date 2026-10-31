import re
from decimal import Decimal
from typing import Any
from unittest.mock import create_autospec

import pytest
from tests.fixtures.factories import (
    jan,
    make_config,
    make_instrument,
    make_performance_metrics,
    make_portfolio,
    make_price_series,
    make_value_points,
)

from finscope.analytics.services.performance_calculation_service import (
    PerformanceCalculationService,
)
from finscope.analytics.services.portfolio_analysis_engine import (
    PortfolioAnalysisEngine,
)
from finscope.analytics.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from finscope.domain.experiment_config import ExperimentConfig
from finscope.domain.instrument import Instrument


def test_passes_inputs_to_valuation_service(
    valuation_spy: Any,
    performance_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    valuation_spy.calculate.return_value = make_value_points("1000", "1100")
    performance_spy.calculate.return_value = make_performance_metrics()
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    engine.analyze(portfolio, default_config, price_series)

    valuation_spy.calculate.assert_called_once_with(
        portfolio,
        default_config,
        price_series,
    )


def test_passes_valuation_points_to_performance_service(
    valuation_spy: Any,
    performance_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    points = make_value_points("1000", "1100")
    valuation_spy.calculate.return_value = points
    performance_spy.calculate.return_value = make_performance_metrics()
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    engine.analyze(portfolio, default_config, price_series)

    performance_spy.calculate.assert_called_once_with(points)


def test_result_is_built_from_service_outputs(
    valuation_spy: Any,
    performance_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    points = make_value_points("1000", "1500", "750")
    metrics = make_performance_metrics(total_return=-0.25)
    valuation_spy.calculate.return_value = points
    performance_spy.calculate.return_value = metrics
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    result = engine.analyze(portfolio, default_config, price_series)

    assert result.value_points == points
    assert result.metrics is metrics
    assert result.from_date == points[0].valuation_date
    assert result.to_date == points[-1].valuation_date


def test_uses_injected_valuation_service_with_default_performance_service(
    valuation_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    valuation_spy.calculate.return_value = make_value_points(
        "1000",
        "1500",
        "750",
    )
    engine = PortfolioAnalysisEngine(valuation_spy)

    result = engine.analyze(portfolio, default_config, price_series)

    assert result.metrics.total_return == pytest.approx(-0.25)
    assert result.metrics.maximum_drawdown == pytest.approx(0.5)


def test_uses_injected_performance_service_with_default_valuation_service(
    performance_spy: Any,
    instrument_a: Instrument,
    instrument_b: Instrument,
    default_config: ExperimentConfig,
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
    metrics = make_performance_metrics(total_return=-0.25)
    performance_spy.calculate.return_value = metrics
    engine = PortfolioAnalysisEngine(
        performance_calculation_service=performance_spy,
    )

    result = engine.analyze(portfolio, default_config, price_series)

    assert result.metrics is metrics
    assert [point.total_value for point in result.value_points] == [
        Decimal("1000"),
        Decimal("1500"),
        Decimal("750"),
    ]


def test_analyzes_portfolio_end_to_end(
    analysis_engine: PortfolioAnalysisEngine,
    instrument_a: Instrument,
    instrument_b: Instrument,
    default_config: ExperimentConfig,
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

    result = analysis_engine.analyze(portfolio, default_config, price_series)

    assert [point.total_value for point in result.value_points] == [
        Decimal("1000"),
        Decimal("1500"),
        Decimal("750"),
    ]
    assert result.metrics.initial_value == pytest.approx(1000)
    assert result.metrics.final_value == pytest.approx(750)
    assert result.metrics.pnl == pytest.approx(-250)
    assert result.metrics.total_return == pytest.approx(-0.25)
    assert result.metrics.maximum_drawdown == pytest.approx(0.5)
    assert result.metrics.maximum_drawdown_peak_date == jan(2)
    assert result.metrics.maximum_drawdown_trough_date == jan(3)
    assert result.metrics.best_daily_return == pytest.approx(0.5)
    assert result.metrics.best_daily_return_date == jan(2)
    assert result.metrics.highest_portfolio_value_date == jan(2)
    assert result.metrics.lowest_portfolio_value_date == jan(3)
    assert result.from_date == jan(1)
    assert result.to_date == jan(3)


def test_engine_is_reusable_across_calls(
    analysis_engine: PortfolioAnalysisEngine,
    instrument_a: Instrument,
    instrument_b: Instrument,
    default_config: ExperimentConfig,
) -> None:
    first_portfolio = make_portfolio(
        ((instrument_a, "0.5"), (instrument_b, "0.5")),
    )
    first_series = (
        make_price_series(
            instrument_a,
            {jan(1): "100", jan(2): "200", jan(3): "100"},
        ),
        make_price_series(
            instrument_b,
            {jan(1): "100", jan(2): "100", jan(3): "50"},
        ),
    )
    second_portfolio = make_portfolio(((instrument_a, "1.0"),))
    second_series = (
        make_price_series(
            instrument_a,
            {jan(1): "100", jan(2): "110", jan(3): "132"},
        ),
    )

    first_result = analysis_engine.analyze(
        first_portfolio,
        default_config,
        first_series,
    )
    second_result = analysis_engine.analyze(
        second_portfolio,
        default_config,
        second_series,
    )
    third_result = analysis_engine.analyze(
        first_portfolio,
        default_config,
        first_series,
    )

    assert [point.total_value for point in first_result.value_points] == [
        Decimal("1000"),
        Decimal("1500"),
        Decimal("750"),
    ]
    assert first_result.metrics.total_return == pytest.approx(-0.25)
    assert first_result.metrics.maximum_drawdown == pytest.approx(0.5)
    assert [point.total_value for point in second_result.value_points] == [
        Decimal("1000"),
        Decimal("1100"),
        Decimal("1320"),
    ]
    assert second_result.metrics.final_value == pytest.approx(1320)
    assert second_result.metrics.pnl == pytest.approx(320)
    assert second_result.metrics.total_return == pytest.approx(0.32)
    assert second_result.metrics.best_daily_return == pytest.approx(0.2)
    assert second_result.metrics.best_daily_return_date == jan(3)
    assert second_result.metrics.highest_portfolio_value_date == jan(3)
    assert second_result.metrics.lowest_portfolio_value_date == jan(1)
    assert first_result == third_result


@pytest.mark.parametrize(
    ("overrides", "exception_type", "message"),
    [
        pytest.param(
            {"portfolio": "not-a-portfolio"},
            TypeError,
            "portfolio must be a Portfolio",
            id="portfolio-not-a-portfolio",
        ),
        pytest.param(
            {"config": None},
            TypeError,
            "config must be an ExperimentConfig",
            id="config-not-a-config",
        ),
        pytest.param(
            {"price_series": []},
            TypeError,
            "price_series must be a tuple of PriceSeries",
            id="price-series-is-a-list",
        ),
        pytest.param(
            {"price_series": ("x",)},
            TypeError,
            "price_series must contain only PriceSeries instances",
            id="price-series-has-non-series",
        ),
        pytest.param(
            {"config": make_config(jan(1), jan(31), portfolio_id="other")},
            ValueError,
            "config portfolio_id must match the supplied portfolio",
            id="config-for-other-portfolio",
        ),
        pytest.param(
            {"price_series": ()},
            ValueError,
            "At least one price series is required",
            id="empty-price-series",
        ),
    ],
)
def test_rejects_invalid_input_before_calling_any_service(
    overrides: dict[str, Any],
    exception_type: type[Exception],
    message: str,
) -> None:
    instrument = make_instrument("inst-a")
    arguments: dict[str, Any] = {
        "portfolio": make_portfolio(((instrument, "1.0"),)),
        "config": make_config(jan(1), jan(31)),
        "price_series": (
            make_price_series(instrument, {jan(1): "100", jan(2): "110"}),
        ),
    }
    arguments.update(overrides)
    valuation_spy = create_autospec(PortfolioValuationService, instance=True)
    performance_spy = create_autospec(
        PerformanceCalculationService,
        instance=True,
    )
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    with pytest.raises(exception_type, match=re.escape(message)):
        engine.analyze(**arguments)

    valuation_spy.calculate.assert_not_called()
    performance_spy.calculate.assert_not_called()


def test_rejects_fewer_than_two_valuation_points(
    valuation_spy: Any,
    performance_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    valuation_spy.calculate.return_value = make_value_points("1000")
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    with pytest.raises(
        ValueError,
        match=re.escape("At least two portfolio valuation points are required"),
    ):
        engine.analyze(portfolio, default_config, price_series)

    performance_spy.calculate.assert_not_called()


def test_propagates_valuation_service_errors(
    valuation_spy: Any,
    performance_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    error = ValueError("valuation failed")
    valuation_spy.calculate.side_effect = error
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    with pytest.raises(ValueError) as excinfo:
        engine.analyze(portfolio, default_config, price_series)

    assert excinfo.value is error
    performance_spy.calculate.assert_not_called()


def test_propagates_performance_service_errors(
    valuation_spy: Any,
    performance_spy: Any,
    instrument_a: Instrument,
    default_config: ExperimentConfig,
) -> None:
    portfolio = make_portfolio(((instrument_a, "1.0"),))
    price_series = (
        make_price_series(instrument_a, {jan(1): "100", jan(2): "110"}),
    )
    valuation_spy.calculate.return_value = make_value_points("1000", "1100")
    error = ValueError("performance failed")
    performance_spy.calculate.side_effect = error
    engine = PortfolioAnalysisEngine(valuation_spy, performance_spy)

    with pytest.raises(ValueError) as excinfo:
        engine.analyze(portfolio, default_config, price_series)

    assert excinfo.value is error