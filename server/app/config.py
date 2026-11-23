import os
from pathlib import Path


DEFAULT_DATABASE_URL = "sqlite:///./runtime/ogk.db"


def get_database_url() -> str:
    return os.getenv("OGK_DATABASE_URL", DEFAULT_DATABASE_URL)


def ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:"):
        return

    raw_path = database_url.split(":///", 1)[-1]
    if raw_path in ("", ":memory:"):
        return

    if raw_path.startswith("/"):
        database_path = Path(raw_path)
    else:
        database_path = Path.cwd() / raw_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
