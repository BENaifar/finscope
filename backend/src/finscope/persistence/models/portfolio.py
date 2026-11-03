from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finscope.persistence.models.base import Base


class PortfolioRecord(Base):
    __tablename__ = "portfolios"

    __table_args__ = (
        CheckConstraint("initial_capital > 0", name="initial_capital_positive"),
        CheckConstraint("base_currency = 'USD'", name="currency_usd_only"),
        CheckConstraint("strategy = 'buy_and_hold'", name="strategy_buy_and_hold"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    base_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="USD",
    )

    strategy: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="buy_and_hold",
    )

    allocations: Mapped[list["PortfolioAllocationRecord"]] = relationship(
        "PortfolioAllocationRecord",
        back_populates="portfolio",
        cascade="all, delete-orphan",
        order_by="PortfolioAllocationRecord.instrument_id",
    )