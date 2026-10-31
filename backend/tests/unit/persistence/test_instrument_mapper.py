from tests.fixtures.factories import make_instrument

from finscope.persistence.mappings.instrument_mapper import to_domain, to_record


def test_round_trip_preserves_all_fields() -> None:
    instrument = make_instrument("inst-a", symbol="AAA")

    assert to_domain(to_record(instrument)) == instrument


def test_to_record_copies_every_field() -> None:
    record = to_record(make_instrument("inst-a", symbol="AAA"))

    assert (record.id, record.symbol, record.name, record.currency) == (
        "inst-a",
        "AAA",
        "inst-a",
        "USD",
    )