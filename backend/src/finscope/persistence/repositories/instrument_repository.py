from sqlalchemy import select
from sqlalchemy.orm import Session

from finscope.domain.instrument import Instrument
from finscope.persistence.mappings.instrument_mapper import to_domain, to_record
from finscope.persistence.models.instrument import InstrumentRecord


class InstrumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, instrument: Instrument) -> None:
        self._session.add(to_record(instrument))
        self._session.flush()

    def get_by_id(self, instrument_id: str) -> Instrument | None:
        record = self._session.get(InstrumentRecord, instrument_id)
        return to_domain(record) if record is not None else None

    def get_by_symbol(self, symbol: str) -> Instrument | None:
        record = self._session.scalar(
            select(InstrumentRecord).where(InstrumentRecord.symbol == symbol)
        )
        return to_domain(record) if record is not None else None