from finscope.domain.portfolio import Portfolio
from finscope.domain.portfolio_allocation import PortfolioAllocation
from finscope.persistence.mappings.instrument_mapper import to_domain as instrument_to_domain
from finscope.persistence.models.portfolio import PortfolioRecord
from finscope.persistence.models.portfolio_allocation import PortfolioAllocationRecord


def to_record(portfolio: Portfolio) -> PortfolioRecord:
    return PortfolioRecord(
        id=portfolio.id,
        initial_capital=portfolio.initial_capital,
        base_currency=portfolio.base_currency,
        strategy=portfolio.strategy,
        allocations=[
            PortfolioAllocationRecord(
                instrument_id=allocation.instrument.id,
                weight=allocation.weight,
            )
            for allocation in portfolio.allocations
        ],
    )


def to_domain(record: PortfolioRecord) -> Portfolio:
    return Portfolio(
        id=record.id,
        initial_capital=record.initial_capital,
        base_currency=record.base_currency,
        strategy=record.strategy,
        allocations=tuple(
            PortfolioAllocation(
                instrument=instrument_to_domain(allocation.instrument),
                weight=allocation.weight,
            )
            for allocation in record.allocations
        ),
    )