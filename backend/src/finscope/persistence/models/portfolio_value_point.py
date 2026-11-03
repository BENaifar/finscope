from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from finscope.persistence.models.base import Base


class PortfolioValuePointRecord(Base):
    __tablename__ = "portfolio_value_points"
    __table_args__ = (
        CheckConstraint("currency = 'USD'", name="currency_usd_only"),
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    valuation_date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )