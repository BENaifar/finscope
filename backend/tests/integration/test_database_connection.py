import os

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.skipif(
    "DATABASE_URL" not in os.environ,
    reason="DATABASE_URL is not set; PostgreSQL integration tests skipped",
)


def test_engine_can_run_a_query() -> None:
    from finscope.persistence.database import engine

    with engine.connect() as connection:
        assert connection.execute(text("select 1")).scalar_one() == 1