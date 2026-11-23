from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.config import ensure_sqlite_parent, get_database_url


database_url = get_database_url()


def create_app_engine(database_url: str) -> Engine:
    ensure_sqlite_parent(database_url)
    new_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    if new_engine.dialect.name == "sqlite":
        @event.listens_for(new_engine, "connect")
        def configure_sqlite_connection(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    return new_engine


engine = create_app_engine(database_url)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine() -> Engine:
    return engine


def verify_database_pragmas() -> dict[str, str | int]:
    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
    return {
        "foreign_keys": int(foreign_keys),
        "busy_timeout": int(busy_timeout),
        "journal_mode": str(journal_mode),
    }
