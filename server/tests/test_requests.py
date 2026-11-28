from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from server.app.auth.security import hash_device_token, hash_password, utc_now
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.models.entities import Child, Device, DeviceAuthCredential, Grant, Request, User


PARENT_ID = "11111111-1111-1111-1111-111111111111"
CHILD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DEVICE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
REQUEST_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
ACCESS_TOKEN = "request-test-access-token"


@pytest.fixture
def requests_api(migrated_sqlite) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    _, TestSession = migrated_sqlite
    now = utc_now()
    db = TestSession()
    db.add(User(id=PARENT_ID, email="request-parent@example.test", password_hash=hash_password("correct horse battery"), role="parent", created_at=now))
    db.flush()
    db.add(Child(id=CHILD_ID, owner_id=PARENT_ID, display_name="Test child", timezone="Asia/Ho_Chi_Minh", age_band="6-11"))
    db.flush()
    db.add(Device(id=DEVICE_ID, child_id=CHILD_ID, name="Test device", token_hash=hash_device_token(ACCESS_TOKEN), last_seen_at=now, revoked_at=None))
    db.flush()
    db.add(DeviceAuthCredential(id="dddddddd-dddd-dddd-dddd-dddddddddddd", device_id=DEVICE_ID, access_expires_at=now + timedelta(minutes=15), refresh_expires_at=now + timedelta(days=30), revoked_at=None, created_at=now))
    db.commit()
    db.close()

    def override_db() -> Iterator[Session]:
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
        login = client.post("/api/v1/auth/login", json={"email":"request-parent@example.test", "password":"correct horse battery"})
        assert login.status_code == 200
        client.headers.update({"X-CSRF-Token": login.headers["X-CSRF-Token"]})
        yield client, TestSession
    app.dependency_overrides.clear()


def _create_request(client: TestClient) -> dict:
    now = utc_now()
    local_date = now.isoformat()[:10]
    response = client.post("/api/v1/agent/requests", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}, json={
        "schema_version": 1,
        "request_id": REQUEST_ID,
        "request_type": "time_extension",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "reason": "Xin thêm giờ học",
        "payload": {"amount_seconds": 900, "local_date": local_date},
    })
    assert response.status_code == 200
    return response.json()


def test_request_approve_creates_one_grant_and_reject(requests_api):
    client, TestSession = requests_api
    _create_request(client)

    approved = client.post(f"/api/v1/requests/{REQUEST_ID}/decision", json={"decision":"approved"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["grant"]["scope"]["amount_seconds"] == 900

    second = client.post(f"/api/v1/requests/{REQUEST_ID}/decision", json={"decision":"approved"})
    assert second.status_code == 409

    db = TestSession()
    assert db.query(Request).filter_by(id=REQUEST_ID).one().status == "approved"
    assert db.query(Grant).filter_by(request_id=REQUEST_ID).count() == 1
    db.close()


def test_request_replay_and_reject_no_grant(requests_api):
    client, TestSession = requests_api
    first = _create_request(client)
    replay = client.post("/api/v1/agent/requests", headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}, json={
        "schema_version": 1,
        "request_id": REQUEST_ID,
        "request_type": "time_extension",
        "created_at": utc_now().isoformat().replace("+00:00", "Z"),
        "reason": "Xin thêm giờ học",
        "payload": {"amount_seconds": 900, "local_date": utc_now().isoformat()[:10]},
    })
    assert replay.status_code == 200
    assert replay.json()["request_id"] == first["request_id"]

    rejected = client.post(f"/api/v1/requests/{REQUEST_ID}/decision", json={"decision":"rejected"})
    assert rejected.status_code == 200
    assert rejected.json()["grant"] is None

    db = TestSession()
    assert db.query(Grant).filter_by(request_id=REQUEST_ID).count() == 0
    db.close()
