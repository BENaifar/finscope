from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from tests.fixtures.factories import jan, make_config, make_instrument, make_portfolio
from tests.fixtures.market_data_fakes import SpyProvider, make_provider

from finscope.analytics.services.experiment_execution_service import (
    ExperimentExecutionService,
)
from finscope.analytics.services.experiment_orchestration_service import (
    ExperimentOrchestrationService,
)
from finscope.application.errors import ExperimentNotFoundError
from finscope.application.experiment_workflow_service import (
    ExperimentWorkflowService,
)
from finscope.domain.experiment_config import ExperimentConfig
from finscope.domain.experiment_run import ExperimentStatus
from finscope.market_data.market_data_service import (
    MarketDataService,
    ProviderSource,
)
from finscope.market_data.nyse_trading_calendar import NyseTradingCalendar
from finscope.persistence.repositories.experiment_repository import (
    ExperimentRepository,
)
from finscope.persistence.repositories.experiment_run_repository import (
    ExperimentRunRepository,
)
from finscope.persistence.repositories.instrument_repository import (
    InstrumentRepository,
)
from finscope.persistence.repositories.portfolio_repository import (
    PortfolioRepository,
)
from finscope.persistence.repositories.price_point_repository import (
    PricePointRepository,
)

# CLAUDE.md reference scenario: $10,000, 60% A (100 -> 110 -> 90) and
# 40% B (50 -> 55 -> 60) buys 60 A and 80 B units, so the portfolio is worth
# 10,000 / 11,000 / 10,200 and returns 2%. Jan 2 to 4 2024 are NYSE sessions.
PRICES_A = {2: "100", 3: "110", 4: "90"}
PRICES_B = {2: "50", 3: "55", 4: "60"}


def _seed_experiment(session: Session) -> ExperimentConfig:
    instrument_a = make_instrument("inst-a", symbol="AAA")
    instrument_b = make_instrument("inst-b", symbol="BBB")
    instruments = InstrumentRepository(session)
    instruments.add(instrument_a)
    instruments.add(instrument_b)
    PortfolioRepository(session).add(
        make_portfolio(
            [(instrument_a, "0.6"), (instrument_b, "0.4")],
            initial_capital="10000",
        )
    )
    config = make_config(jan(2), jan(4))
    ExperimentRepository(session).add(config)
    return config


def _build_service(session: Session, spy: SpyProvider) -> ExperimentWorkflowService:
    market_data = MarketDataService(
        PricePointRepository(session),
        NyseTradingCalendar(),
        (ProviderSource("memory", spy),),
    )
    return ExperimentWorkflowService(
        experiments=ExperimentRepository(session),
        portfolios=PortfolioRepository(session),
        runs=ExperimentRunRepository(session),
        orchestrator=ExperimentOrchestrationService(
            provider=market_data,
            execution_service=ExperimentExecutionService(),
        ),
        commit=session.commit,
    )


def _count(session: Session, table: str) -> int:
    return session.scalar(text(f"SELECT count(*) FROM {table}")) or 0


def test_reference_scenario_runs_end_to_end_and_is_persisted(
    session: Session,
) -> None:
    config = _seed_experiment(session)
    spy = SpyProvider(make_provider({"inst-a": PRICES_A, "inst-b": PRICES_B}))
    service = _build_service(session, spy)

    run = service.run_experiment(config.id)

    assert run.status == ExperimentStatus.COMPLETED
    assert run.result is not None
    metrics = run.result.metrics
    assert metrics.initial_value == Decimal("10000")
    assert metrics.final_value == Decimal("10200")
    assert metrics.pnl == Decimal("200")
    assert metrics.total_return == Decimal("0.02")
    assert [point.total_value for point in run.result.value_points] == [
        Decimal("10000"),
        Decimal("11000"),
        Decimal("10200"),
    ]
    assert ExperimentRunRepository(session).get_by_id(run.id) == run
    assert _count(session, "price_points") == 6
    assert _count(session, "portfolio_value_points") == 3


def test_a_second_run_reuses_stored_prices_and_is_a_separate_run(
    session: Session,
) -> None:
    config = _seed_experiment(session)
    spy = SpyProvider(make_provider({"inst-a": PRICES_A, "inst-b": PRICES_B}))
    service = _build_service(session, spy)

    first = service.run_experiment(config.id)
    calls_after_first_run = len(spy.calls)
    second = service.run_experiment(config.id)

    assert calls_after_first_run == 2
    assert len(spy.calls) == calls_after_first_run
    assert first.id != second.id
    assert first.config == second.config
    assert first.result == second.result
    assert _count(session, "experiment_runs") == 2
    assert _count(session, "experiments") == 1


def test_missing_price_data_is_saved_as_a_failed_run_and_keeps_fetched_prices(
    session: Session,
) -> None:
    config = _seed_experiment(session)
    spy = SpyProvider(make_provider({"inst-a": PRICES_A}))
    service = _build_service(session, spy)

    run = service.run_experiment(config.id)

    assert run.status == ExperimentStatus.FAILED
    assert run.error_message is not None
    assert "BBB" in run.error_message
    assert ExperimentRunRepository(session).get_by_id(run.id) == run
    assert _count(session, "portfolio_value_points") == 0
    assert _count(session, "performance_metrics") == 0
    stored_for_a = session.scalar(
        text("SELECT count(*) FROM price_points WHERE instrument_id = 'inst-a'")
    )
    assert stored_for_a == 3


def test_unknown_experiment_raises_and_creates_no_run(session: Session) -> None:
    _seed_experiment(session)
    spy = SpyProvider(make_provider({}))
    service = _build_service(session, spy)

    with pytest.raises(ExperimentNotFoundError):
        service.run_experiment("no-such-experiment")

    assert _count(session, "experiment_runs") == 0
    assert spy.calls == []
