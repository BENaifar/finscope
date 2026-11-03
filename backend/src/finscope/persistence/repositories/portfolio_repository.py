from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from finscope.domain.portfolio import Portfolio
from finscope.persistence.mappings.portfolio_mapper import to_domain, to_record
from finscope.persistence.models.portfolio import PortfolioRecord
from finscope.persistence.models.portfolio_allocation import PortfolioAllocationRecord


class PortfolioRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, portfolio: Portfolio) -> None:
        self._session.add(to_record(portfolio))
        self._session.flush()

    def get_by_id(self, portfolio_id: str) -> Portfolio | None:
        record = self._session.scalar(
            select(PortfolioRecord)
            .where(PortfolioRecord.id == portfolio_id)
            .options(
                selectinload(PortfolioRecord.allocations).joinedload(
                    PortfolioAllocationRecord.instrument
                )
            )
        )
        return to_domain(record) if record is not None else None