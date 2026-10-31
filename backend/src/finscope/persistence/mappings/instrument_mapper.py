from finscope.domain.instrument import Instrument
from finscope.persistence.models.instrument import InstrumentRecord


def to_domain(record: InstrumentRecord) -> Instrument:
    return Instrument(
        id=record.id,
        symbol=record.symbol,
        name=record.name,
        currency=record.currency,
    )


def to_record(instrument: Instrument) -> InstrumentRecord:
    return InstrumentRecord(
        id=instrument.id,
        symbol=instrument.symbol,
        name=instrument.name,
        currency=instrument.currency,
    )