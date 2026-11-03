from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from finscope.persistence.models.base import Base


class ExperimentRecord(Base):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint("start_date < end_date", name="start_before_end"),
        CheckConstraint(
            "price_convention = 'adjusted_close'",
            name="price_convention_adjusted_close",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    portfolio_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("portfolios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_convention: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="adjusted_close"
    )