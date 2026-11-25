from datetime import datetime, timezone

from sqlalchemy import text

from server.app.models.entities import Child, Device, DeviceEvent, User


def test_insert_child_with_missing_owner_is_rejected(migrated_sqlite) -> None:
    engine, Session = migrated_sqlite

    with Session() as session:
        try:
            session.add(Child(id="child-1", owner_id="missing-owner", display_name="Child", timezone="Asia/Ho_Chi_Minh"))
            session.commit()
            raise AssertionError("foreign key violation was not enforced")
        except Exception:
            session.rollback()

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM children")).scalar_one() == 0


def test_unique_event_id_per_device_is_enforced(migrated_sqlite) -> None:
    engine, Session = migrated_sqlite

    with Session() as session:
        now = datetime.now(timezone.utc)
        session.add(User(id="owner-1", email="parent@example.test", password_hash="hash", created_at=now))
        session.flush()
        session.add(Child(id="child-1", owner_id="owner-1", display_name="Child", timezone="Asia/Ho_Chi_Minh"))
        session.flush()
        session.add(Device(id="device-1", child_id="child-1", name="Lab PC"))
        session.flush()
        session.add_all([
            DeviceEvent(id="event-row-1", event_id="event-1", device_id="device-1", event_type="heartbeat", observed_at=now, payload_json="{}"),
            DeviceEvent(id="event-row-2", event_id="event-1", device_id="device-1", event_type="heartbeat", observed_at=now, payload_json="{}"),
        ])
        try:
            session.commit()
            raise AssertionError("duplicate device/event pair was not rejected")
        except Exception:
            session.rollback()
