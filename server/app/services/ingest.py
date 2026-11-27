"""Heartbeat and telemetry ingestion helpers for agent synchronization."""

from datetime import datetime

from sqlalchemy.orm import Session


LOST_CONNECTION_SECONDS = 180


def begin_write_transaction(db: Session) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def connection_state(last_seen_at: datetime | None, now: datetime) -> str:
    if last_seen_at is None:
        return "unknown"
    elapsed = (now - last_seen_at).total_seconds()
    return "lost" if elapsed > LOST_CONNECTION_SECONDS else "online"
