from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from finscope.persistence.models.base import Base


class PricePointRecord(Base):
    __tablename__ = "price_points"
    __table_args__ = (
        CheckConstraint("adjusted_close > 0", name="adjusted_close_positive"),
    )

    instrument_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    price_date: Mapped[date] = mapped_column(Date, primary_key=True)
    adjusted_close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )