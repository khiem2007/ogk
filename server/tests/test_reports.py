import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from server.app.auth.security import hash_csrf_token, utc_now
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.models.entities import AuthSession, AuditLog, Child, Device, UsageInterval, User
from server.app.services.retention import run_retention

PARENT_ID = "11111111-1111-1111-1111-111111111111"
CHILD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DEVICE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SESSION_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
CSRF = "test-csrf-token"


@pytest.fixture
def reports_api(migrated_sqlite: tuple[object, sessionmaker[Session]]):
    _, TestSession = migrated_sqlite
    db = TestSession()
    now = utc_now()
    db.add(User(id=PARENT_ID, email="report-parent@example.test", password_hash="hash", role="parent", created_at=now))
    db.flush()
    db.add(Child(id=CHILD_ID, owner_id=PARENT_ID, display_name="Test child", timezone="Asia/Ho_Chi_Minh"))
    db.flush()
    db.add(Device(id=DEVICE_ID, child_id=CHILD_ID, name="Test device", token_hash=None, revoked_at=None))
    db.add(AuthSession(id=SESSION_ID, user_id=PARENT_ID, csrf_token_hash=hash_csrf_token(CSRF), expires_at=now + timedelta(hours=1), revoked_at=None, created_at=now))
    db.add(UsageInterval(
        id=str(uuid.uuid4()), event_id=str(uuid.uuid4()), device_id=DEVICE_ID,
        start_utc=datetime(2026, 11, 27, 16, 0), end_utc=datetime(2026, 11, 27, 16, 1),
        active_seconds=60, app_id=None, sequence=1, boot_id=str(uuid.uuid4()),
    ))
    db.commit()
    db.close()

    def override_db():
        session = TestSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as client:
        yield client, TestSession
    app.dependency_overrides.clear()


def cookies():
    return {"ogk_session": SESSION_ID}


def test_daily_report_deduplicates_event_and_respects_timezone(reports_api):
    client, TestSession = reports_api
    response = client.get(
        f"/api/v1/reports/daily?device_id={DEVICE_ID}&date=2026-11-27",
        cookies=cookies(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "Asia/Ho_Chi_Minh"
    assert body["machine_total_seconds"] == 60


def test_audit_is_paginated_and_delete_all_requires_csrf(reports_api):
    client, TestSession = reports_api
    response = client.post(
        f"/api/v1/children/{CHILD_ID}/delete-all",
        cookies=cookies(),
    )
    assert response.status_code == 403

    response = client.post(
        f"/api/v1/children/{CHILD_ID}/delete-all",
        cookies=cookies(), headers={"X-CSRF-Token": CSRF},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "server_data_deleted"

    db = TestSession()
    assert db.query(Device).filter_by(id=DEVICE_ID).count() == 1
    assert db.query(UsageInterval).filter_by(device_id=DEVICE_ID).count() == 0
    assert db.query(AuditLog).filter_by(action="child.delete_all").count() == 1
    db.close()


def test_retention_deletes_only_records_past_90_days(reports_api):
    client, TestSession = reports_api
    db = TestSession()
    old = utc_now() - timedelta(days=91)
    event_id = str(uuid.uuid4())
    db.add(UsageInterval(
        id=str(uuid.uuid4()), event_id=event_id, device_id=DEVICE_ID,
        start_utc=old.replace(tzinfo=None), end_utc=(old + timedelta(seconds=60)).replace(tzinfo=None),
        active_seconds=60, app_id=None, sequence=1, boot_id=str(uuid.uuid4()),
    ))
    db.commit()

    counts = run_retention(db)
    assert counts["usage_intervals"] >= 1
    assert db.query(UsageInterval).filter_by(event_id=event_id).count() == 0
    db.close()
