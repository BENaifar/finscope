from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from finscope.persistence.models.base import Base


class PerformanceMetricsRecord(Base):
    __tablename__ = "performance_metrics"
    __table_args__ = (
        CheckConstraint("from_date <= to_date", name="from_before_to"),
    )

    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiment_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    final_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    pnl: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    maximum_drawdown: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    maximum_drawdown_peak_date: Mapped[date] = mapped_column(Date, nullable=False)
    maximum_drawdown_trough_date: Mapped[date] = mapped_column(Date, nullable=False)
    best_daily_return: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    best_daily_return_date: Mapped[date] = mapped_column(Date, nullable=False)
    highest_portfolio_value_date: Mapped[date] = mapped_column(Date, nullable=False)
    lowest_portfolio_value_date: Mapped[date] = mapped_column(Date, nullable=False)