from pathlib import Path

from sqlalchemy import text

from server.app.db.session import create_app_engine


def test_sqlite_connection_applies_required_pragmas(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'config.db').as_posix()}"
    test_engine = create_app_engine(database_url)

    try:
        with test_engine.connect() as connection:
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
            busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()

        assert foreign_keys == 1
        assert busy_timeout == 5000
        assert journal_mode.lower() == "wal"
    finally:
        test_engine.dispose()
