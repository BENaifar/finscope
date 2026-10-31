from datetime import datetime
from typing import Sequence

from finscope.domain.instrument import Instrument
from finscope.market_data.models.price_point import PricePoint
from finscope.market_data.models.price_series import PriceSeries
from finscope.persistence.models.price_point import PricePointRecord


def to_record_values(
    series: PriceSeries,
    provider: str,
    fetched_at: datetime,
) -> list[dict]:
    """Convert a domain price series into values for ORM bulk insertion."""
    return [
        {
            "instrument_id": series.instrument.id,
            "price_date": point.date,
            "adjusted_close": point.adjusted_close,
            "provider": provider,
            "fetched_at": fetched_at,
        }
        for point in series.points
    ]


def to_domain_price_point(record: PricePointRecord) -> PricePoint:
    """Convert one ORM price-point record into a domain price point."""
    return PricePoint(
        date=record.price_date,
        adjusted_close=record.adjusted_close,
    )


def to_domain_price_series(
    records: Sequence[PricePointRecord],
    instrument: Instrument,
) -> PriceSeries:
    """Convert ordered ORM records into a domain price series."""
    return PriceSeries(
        instrument=instrument,
        points=tuple(to_domain_price_point(record) for record in records),
    )

