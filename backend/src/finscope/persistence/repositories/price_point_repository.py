from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from finscope.domain.instrument import Instrument
from finscope.market_data.models.price_series import PriceSeries
from finscope.persistence.mappings.price_point_mapper import (
    to_domain_price_series,
    to_record_values,
)
from finscope.persistence.models.price_point import PricePointRecord


class PricePointRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_series(
        self, series: PriceSeries, provider: str, fetched_at: datetime
    ) -> None:
        rows = to_record_values(series, provider, fetched_at)

        if not rows:
            return

        statement = insert(PricePointRecord).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=["instrument_id", "price_date"],
            set_={
                "adjusted_close": statement.excluded.adjusted_close,
                "provider": statement.excluded.provider,
                "fetched_at": statement.excluded.fetched_at,
            },
        )

        self._session.execute(statement)

    def get_series(
        self, instrument: Instrument, start_date: date, end_date: date
    ) -> PriceSeries | None:
        records = self._session.scalars(
            select(PricePointRecord)
            .where(
                PricePointRecord.instrument_id == instrument.id,
                PricePointRecord.price_date >= start_date,
                PricePointRecord.price_date <= end_date,
            )
            .order_by(PricePointRecord.price_date)
        ).all()

        if not records:
            return None

        return to_domain_price_series(records, instrument)