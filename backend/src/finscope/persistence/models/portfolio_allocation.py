from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finscope.persistence.models.base import Base
from finscope.persistence.models.instrument import InstrumentRecord


class PortfolioAllocationRecord(Base):
    __tablename__ = "portfolio_allocations"

    __table_args__ = (
        CheckConstraint("weight > 0 AND weight <= 1", name="weight_in_range"),
    )

    portfolio_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
    )

    instrument_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        primary_key=True,
    )

    weight: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )

    portfolio: Mapped["PortfolioRecord"] = relationship(
        "PortfolioRecord",
        back_populates="allocations",
    )

    instrument: Mapped["InstrumentRecord"] = relationship(
        "InstrumentRecord",
    )