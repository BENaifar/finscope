from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finscope.persistence.models.base import Base

if TYPE_CHECKING:
    from finscope.persistence.models.experiment import ExperimentRecord
    from finscope.persistence.models.performance_metrics import (
        PerformanceMetricsRecord,
    )
    from finscope.persistence.models.portfolio_value_point import (
        PortfolioValuePointRecord,
    )


class ExperimentRunRecord(Base):
    __tablename__ = "experiment_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="status_valid",
        ),
        CheckConstraint(
            "(status = 'pending' AND started_at IS NULL AND finished_at IS NULL)"
            " OR (status = 'running' AND started_at IS NOT NULL"
            " AND finished_at IS NULL)"
            " OR (status IN ('completed', 'failed') AND started_at IS NOT NULL"
            " AND finished_at IS NOT NULL)",
            name="status_matches_timestamps",
        ),
        CheckConstraint(
            "started_at IS NULL OR created_at <= started_at",
            name="created_before_started",
        ),
        CheckConstraint(
            "finished_at IS NULL OR started_at <= finished_at",
            name="started_before_finished",
        ),
        CheckConstraint(
            "(status = 'failed') = (error_message IS NOT NULL)",
            name="error_only_when_failed",
        ),
        CheckConstraint(
            "error_message IS NULL OR length(trim(error_message)) > 0",
            name="error_not_blank",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("experiments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped["ExperimentRecord"] = relationship()
    value_points: Mapped[list["PortfolioValuePointRecord"]] = relationship(
        cascade="all, delete-orphan",
        order_by="PortfolioValuePointRecord.valuation_date",
    )
    metrics: Mapped["PerformanceMetricsRecord | None"] = relationship(
        cascade="all, delete-orphan",
        uselist=False,
    )