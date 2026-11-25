import sqlite3
import threading
from pathlib import Path


def test_wal_reader_and_writer_with_barriers(tmp_path: Path) -> None:
    database_path = tmp_path / "wal.db"
    writer_ready = threading.Event()
    reader_done = threading.Event()
    errors: list[BaseException] = []

    setup = sqlite3.connect(database_path, timeout=5)
    setup.execute("PRAGMA journal_mode=WAL")
    setup.execute("PRAGMA busy_timeout=5000")
    setup.execute("PRAGMA foreign_keys=ON")
    setup.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
    setup.commit()
    setup.close()

    def writer() -> None:
        try:
            connection = sqlite3.connect(database_path, timeout=5)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT INTO sample(value) VALUES ('committed')")
            writer_ready.set()
            assert reader_done.wait(timeout=5)
            connection.commit()
            connection.close()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=writer)
    thread.start()
    assert writer_ready.wait(timeout=5)

    reader = sqlite3.connect(database_path, timeout=5)
    reader.execute("PRAGMA busy_timeout=5000")
    before = reader.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    reader_done.set()
    thread.join(timeout=5)
    after = reader.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    reader.close()

    assert not thread.is_alive()
    assert errors == []
    assert before == 0
    assert after == 1


def test_writer_busy_timeout_returns_bounded_error(tmp_path: Path) -> None:
    database_path = tmp_path / "lock.db"
    first = sqlite3.connect(database_path, timeout=5)
    second = sqlite3.connect(database_path, timeout=5)
    first.execute("PRAGMA busy_timeout=5000")
    second.execute("PRAGMA busy_timeout=5000")
    first.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    first.commit()

    first.execute("BEGIN IMMEDIATE")
    first.execute("INSERT INTO sample(value) VALUES ('locked')")

    try:
        second.execute("INSERT INTO sample(value) VALUES ('blocked')")
        second.commit()
    except sqlite3.OperationalError as exc:
        assert "locked" in str(exc).lower() or "busy" in str(exc).lower()
    else:
        raise AssertionError("second writer unexpectedly bypassed the lock")
    finally:
        first.rollback()
        first.close()
        second.close()
