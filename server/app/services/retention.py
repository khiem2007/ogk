from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from server.app.auth.security import utc_now
from server.app.models.entities import AuditLog, Command, DeviceEvent, Grant, Request, UsageInterval

RETENTION_DAYS = 90


def run_retention(db: Session, cutoff: datetime | None = None, batch_size: int = 1000) -> dict[str, int]:
    """Delete child-data older than the 90-day retention boundary."""
    if cutoff is None:
        cutoff = utc_now() - timedelta(days=RETENTION_DAYS)
    cutoff = cutoff.replace(tzinfo=None) if cutoff.tzinfo is not None else cutoff

    counts = {
        "usage_intervals": 0,
        "device_events": 0,
        "audit_logs": 0,
        "grants": 0,
        "requests": 0,
        "commands": 0,
    }

    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    def delete_many(model, timestamp_column, key: str) -> None:
        while True:
            ids = [row.id for row in db.query(model.id).filter(timestamp_column < cutoff).limit(batch_size).all()]
            if not ids:
                break
            db.query(model).filter(model.id.in_(ids)).delete(synchronize_session=False)
            counts[key] += len(ids)

    # Delete child-bearing usage and events before request/grant cascades.
    delete_many(UsageInterval, UsageInterval.start_utc, "usage_intervals")
    delete_many(DeviceEvent, DeviceEvent.observed_at, "device_events")
    delete_many(AuditLog, AuditLog.created_at, "audit_logs")
    delete_many(Grant, Grant.valid_until, "grants")
    delete_many(Request, Request.created_at, "requests")
    delete_many(Command, Command.issued_at, "commands")

    db.commit()
    return counts
