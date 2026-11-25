from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text


def test_upgrade_empty_database_creates_erd_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "empty.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    assert not database_path.exists()

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    from server.app.db.session import create_app_engine
    engine = create_app_engine(database_url)
    try:
        inspector = inspect(engine)
        expected = {
            "users", "children", "devices", "enrollment_codes", "policies",
            "app_catalog", "usage_intervals", "device_events", "requests",
            "grants", "commands", "audit_logs", "transparency_records",
        }
        assert expected.issubset(set(inspector.get_table_names()))

        foreign_keys = inspector.get_foreign_keys("children")
        assert any(fk["constrained_columns"] == ["owner_id"] for fk in foreign_keys)

        event_constraints = inspector.get_unique_constraints("device_events")
        assert any(set(item["column_names"]) == {"device_id", "event_id"} for item in event_constraints)

        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000
            assert str(connection.execute(text("PRAGMA journal_mode")).scalar_one()).lower() == "wal"
    finally:
        engine.dispose()


def test_upgrade_is_repeatable(tmp_path: Path) -> None:
    database_path = tmp_path / "repeat.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")
