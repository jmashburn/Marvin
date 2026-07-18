import contextlib
from collections.abc import Generator

from pytest import MonkeyPatch, fixture

mp = MonkeyPatch()
mp.setenv("PRODUCTION", "False")  # Set to False for testing (enables debug handlers)
mp.setenv("TESTING", "True")
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from marvin.app import app
from marvin.core import config
from marvin.db.db_setup import engine, generate_session
from marvin.db.models import SqlAlchemyBase


@fixture(scope="session", autouse=True)
def _create_test_schema() -> Generator[None, None, None]:
    """Build the schema on the empty test database once per session, via migrations.

    The test config points at a separate, unmigrated test data dir. We can't use
    create_all — the models declare JSONB (postgres) which SQLite can't compile — so
    we run the Alembic migrations, which use sqlite-compatible sa.JSON(). Any partial
    tables from an earlier run are dropped first for a clean slate.
    """
    from alembic import command
    from alembic.config import Config

    with contextlib.suppress(Exception):
        SqlAlchemyBase.metadata.drop_all(bind=engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")

    cfg = Config(str(Path(__file__).resolve().parents[1] / "src" / "marvin" / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@fixture
def client() -> TestClient:
    """FastAPI test client for making API requests."""
    return TestClient(app)


@fixture
def db_session() -> Generator[Session, None, None]:
    """
    Database session fixture for tests.

    Yields a SQLAlchemy session for database operations in tests.
    Session is automatically closed after the test completes.
    """
    session = next(generate_session())
    try:
        yield session
    finally:
        session.close()
