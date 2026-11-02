from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1._common import get_config_store
from app.api.v1.timetable import RunManager, get_run_manager
from app.core.timetable_config import DEFAULT_CONFIG_PATH, ConfigStore
from app.data_io.importer import import_workbook
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db, get_session_factory
from app.main import app

SAMPLE_WORKBOOK = Path(__file__).resolve().parents[1] / "samples" / "sample_data.xlsx"


def _sqlite_factory(path: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@pytest.fixture(scope="session")
def seeded_session_factory(tmp_path_factory) -> sessionmaker:
    """A database loaded from ``samples/sample_data.xlsx`` (80 assignments)."""

    factory = _sqlite_factory(tmp_path_factory.mktemp("seeded") / "seeded.db")
    with factory() as db:
        result = import_workbook(db, SAMPLE_WORKBOOK.read_bytes())
    assert result.ok, result.issues
    return factory


@pytest.fixture
def config_store(tmp_path) -> ConfigStore:
    path = tmp_path / "timetable.toml"
    path.write_text(DEFAULT_CONFIG_PATH.read_text())
    return ConfigStore(path)


@pytest.fixture
def test_app(tmp_path, config_store) -> Generator[FastAPI]:
    factory = _sqlite_factory(tmp_path / "test.db")

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    manager = RunManager(factory, tmp_path / "output")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_config_store] = lambda: config_store
    app.dependency_overrides[get_run_manager] = lambda: manager
    app.state.test_run_manager = manager
    yield app
    app.dependency_overrides.clear()
    factory.kw["bind"].dispose()


@pytest.fixture
def run_manager(test_app) -> RunManager:
    return test_app.state.test_run_manager


@pytest.fixture
async def client(test_app: FastAPI):
    with TestClient(test_app) as test_client:
        yield test_client
