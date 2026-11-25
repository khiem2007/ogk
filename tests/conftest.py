from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.db.session import create_app_engine


@pytest.fixture
def migrated_sqlite(tmp_path: Path) -> Iterator[tuple[Engine, sessionmaker[Session]]]:
    database_path = tmp_path / "ogk-test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")

    test_engine = create_app_engine(database_url)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield test_engine, TestSession
    finally:
        test_engine.dispose()
