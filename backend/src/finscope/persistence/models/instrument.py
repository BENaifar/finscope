from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from finscope.persistence.models.base import Base


class InstrumentRecord(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        CheckConstraint("length(trim(symbol)) > 0", name="symbol_not_blank"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("currency = 'USD'", name="currency_usd_only"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )