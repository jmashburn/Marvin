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
from marvin.db.db_setup import generate_session


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
