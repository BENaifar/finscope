from finscope.analytics.models.performance_metrics import PerformanceMetrics
from finscope.analytics.models.performance_result import PerformanceResult
from finscope.analytics.models.portfolio_value_point import PortfolioValuePoint
from finscope.domain.experiment_run import ExperimentRun, ExperimentStatus
from finscope.persistence.mappings.experiment_mapper import (
    to_domain as experiment_to_domain,
)
from finscope.persistence.models.experiment_run import ExperimentRunRecord
from finscope.persistence.models.performance_metrics import PerformanceMetricsRecord
from finscope.persistence.models.portfolio_value_point import (
    PortfolioValuePointRecord,
)


def _attach_result(record: ExperimentRunRecord, result: PerformanceResult) -> None:
    metrics = result.metrics
    record.value_points = [
        PortfolioValuePointRecord(
            valuation_date=point.valuation_date,
            total_value=point.total_value,
            currency=point.currency,
        )
        for point in result.value_points
    ]
    record.metrics = PerformanceMetricsRecord(
        from_date=result.from_date,
        to_date=result.to_date,
        initial_value=metrics.initial_value,
        final_value=metrics.final_value,
        pnl=metrics.pnl,
        total_return=metrics.total_return,
        maximum_drawdown=metrics.maximum_drawdown,
        maximum_drawdown_peak_date=metrics.maximum_drawdown_peak_date,
        maximum_drawdown_trough_date=metrics.maximum_drawdown_trough_date,
        best_daily_return=metrics.best_daily_return,
        best_daily_return_date=metrics.best_daily_return_date,
        highest_portfolio_value_date=metrics.highest_portfolio_value_date,
        lowest_portfolio_value_date=metrics.lowest_portfolio_value_date,
    )


def to_record(run: ExperimentRun) -> ExperimentRunRecord:
    record = ExperimentRunRecord(
        id=run.id,
        experiment_id=run.config.id,
        status=run.status.value,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
    )
    if run.result is not None:
        _attach_result(record, run.result)
    return record


def apply_state(record: ExperimentRunRecord, run: ExperimentRun) -> None:
    """Copy the mutable lifecycle fields of a domain run onto its record."""
    record.status = run.status.value
    record.started_at = run.started_at
    record.finished_at = run.finished_at
    record.error_message = run.error_message
    if run.result is not None:
        if record.metrics is not None:
            raise ValueError("a saved run result cannot be replaced")
        _attach_result(record, run.result)


def _to_domain_result(record: ExperimentRunRecord) -> PerformanceResult | None:
    metrics = record.metrics
    if metrics is None:
        return None
    return PerformanceResult(
        value_points=tuple(
            PortfolioValuePoint(
                valuation_date=point.valuation_date,
                total_value=point.total_value,
                currency=point.currency,
            )
            for point in record.value_points
        ),
        metrics=PerformanceMetrics(
            initial_value=metrics.initial_value,
            final_value=metrics.final_value,
            pnl=metrics.pnl,
            total_return=metrics.total_return,
            maximum_drawdown=metrics.maximum_drawdown,
            maximum_drawdown_peak_date=metrics.maximum_drawdown_peak_date,
            maximum_drawdown_trough_date=metrics.maximum_drawdown_trough_date,
            best_daily_return=metrics.best_daily_return,
            best_daily_return_date=metrics.best_daily_return_date,
            highest_portfolio_value_date=metrics.highest_portfolio_value_date,
            lowest_portfolio_value_date=metrics.lowest_portfolio_value_date,
        ),
        from_date=metrics.from_date,
        to_date=metrics.to_date,
    )


def to_domain(record: ExperimentRunRecord) -> ExperimentRun:
    return ExperimentRun(
        id=record.id,
        config=experiment_to_domain(record.experiment),
        created_at=record.created_at,
        started_at=record.started_at,
        finished_at=record.finished_at,
        status=ExperimentStatus(record.status),
        result=_to_domain_result(record),
        error_message=record.error_message,
    )