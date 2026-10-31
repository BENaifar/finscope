import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url is None:
        pytest.skip("TEST_DATABASE_URL is not set")

    engine = create_engine(url, pool_pre_ping=True)
    if not (engine.url.database or "").endswith("_test"):
        pytest.exit("Refusing to run: test database name must end with '_test'")

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["url"] = url
    command.upgrade(config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def session(test_engine: Engine) -> Iterator[Session]:
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    factory = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    with factory() as db_session:
        yield db_session
    outer_transaction.rollback()
    connection.close()