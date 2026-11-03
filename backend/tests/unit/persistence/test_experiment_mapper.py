from tests.fixtures.factories import jan, make_config

from finscope.persistence.mappings.experiment_mapper import to_domain, to_record


def test_to_record_copies_all_fields() -> None:
    record = to_record(make_config(jan(1), jan(31), config_id="exp-9"))

    assert record.id == "exp-9"
    assert record.portfolio_id == "test-portfolio"
    assert record.start_date == jan(1)
    assert record.end_date == jan(31)
    assert record.price_convention == "adjusted_close"


def test_round_trip_returns_equal_config() -> None:
    config = make_config(jan(1), jan(31))

    assert to_domain(to_record(config)) == config