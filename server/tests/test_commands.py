from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.auth.security import hash_device_token, hash_password, utc_now
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.models.entities import AuditLog, Child, Command, Device, DeviceAuthCredential, User

PARENT_ID = "11111111-1111-1111-1111-111111111111"
CHILD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DEVICE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
CREDENTIAL_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
ACCESS_TOKEN = "test-device-access-token"


@pytest.fixture
def command_api(migrated_sqlite: tuple[Engine, sessionmaker[Session]]) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    _, TestSession = migrated_sqlite
    now = utc_now()
    db = TestSession()
    db.add(User(id=PARENT_ID, email="commands-parent@example.test", password_hash=hash_password("correct horse battery"), role="parent", created_at=now))
    db.flush()
    db.add(Child(id=CHILD_ID, owner_id=PARENT_ID, display_name="Test child", timezone="Asia/Ho_Chi_Minh"))
    db.add(Device(id=DEVICE_ID, child_id=CHILD_ID, name="Test device", token_hash=hash_device_token(ACCESS_TOKEN), last_seen_at=None, applied_policy_version=0, revoked_at=None))
    db.add(DeviceAuthCredential(id=CREDENTIAL_ID, device_id=DEVICE_ID, access_expires_at=now + timedelta(minutes=15), refresh_expires_at=now + timedelta(days=30), revoked_at=None, created_at=now))
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
        login = client.post("/api/v1/auth/login", json={"email": "commands-parent@example.test", "password": "correct horse battery"})
        assert login.status_code == 200
        csrf = login.headers["X-CSRF-Token"]
        yield client, TestSession, {"X-CSRF-Token": csrf}
    app.dependency_overrides.clear()


def agent_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def test_create_poll_ack_replay(command_api: tuple[TestClient, sessionmaker[Session], dict[str, str]]) -> None:
    client, TestSession, csrf = command_api
    dedup_key = str(uuid4())
    expires_at = (utc_now() + timedelta(minutes=5)).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    body = {"command_type": "LOCK_SESSION", "expires_at": expires_at, "payload": {}, "dedup_key": dedup_key}

    created = client.post(f"/api/v1/devices/{DEVICE_ID}/commands", headers=csrf, json=body)
    assert created.status_code == 201
    command_id = created.json()["command_id"]
    assert created.json()["status"] == "queued"

    replay_create = client.post(f"/api/v1/devices/{DEVICE_ID}/commands", headers=csrf, json=body)
    assert replay_create.status_code == 201
    assert replay_create.json()["command_id"] == command_id

    polled = client.get("/api/v1/agent/commands", headers=agent_headers())
    assert polled.status_code == 200
    assert [item["command_id"] for item in polled.json()["commands"]] == [command_id]

    ack = client.post(
        f"/api/v1/agent/commands/{command_id}/ack",
        headers=agent_headers(),
        json={"schema_version": 1, "command_id": command_id, "status": "executed", "observed_at": (utc_now()).isoformat() + "Z", "result_code": "SESSION_STATE_CONFIRMED"},
    )
    assert ack.status_code == 200
    assert ack.json()["status"] == "executed"

    replay_ack = client.post(
        f"/api/v1/agent/commands/{command_id}/ack",
        headers=agent_headers(),
        json={"schema_version": 1, "command_id": command_id, "status": "executed", "observed_at": (utc_now()).isoformat() + "Z", "result_code": "SESSION_STATE_CONFIRMED"},
    )
    assert replay_ack.status_code == 200
    assert replay_ack.json()["replayed"] is True

    db = TestSession()
    command = db.get(Command, command_id)
    assert command is not None
    assert command.status == "executed"
    assert db.query(AuditLog).filter_by(resource_type="command", resource_id=command_id).count() >= 3
    db.close()


def test_allowlist_payload_expiry_and_owner(command_api: tuple[TestClient, sessionmaker[Session], dict[str, str]]) -> None:
    client, _, csrf = command_api
    expires_at = (utc_now() + timedelta(minutes=5)).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    invalid_payload = client.post(
        f"/api/v1/devices/{DEVICE_ID}/commands",
        headers=csrf,
        json={"command_type": "TEMPORARY_TIME_EXEMPTION", "expires_at": expires_at, "payload": {"duration_seconds": 60}},
    )
    assert invalid_payload.status_code == 422

    expired = client.post(
        f"/api/v1/devices/{DEVICE_ID}/commands",
        headers=csrf,
        json={"command_type": "CLEAR_MANUAL_LOCK", "expires_at": (utc_now() - timedelta(seconds=1)).isoformat() + "Z", "payload": {}},
    )
    assert expired.status_code == 422

    unknown_device = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    forbidden = client.post(
        f"/api/v1/devices/{unknown_device}/commands",
        headers=csrf,
        json={"command_type": "LOCK_SESSION", "expires_at": expires_at, "payload": {}},
    )
    assert forbidden.status_code in {404, 422}


def test_ack_wrong_device_and_conflicting_result(command_api: tuple[TestClient, sessionmaker[Session], dict[str, str]]) -> None:
    client, TestSession, csrf = command_api
    expires_at = (utc_now() + timedelta(minutes=5)).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    created = client.post(
        f"/api/v1/devices/{DEVICE_ID}/commands",
        headers=csrf,
        json={"command_type": "CLEAR_MANUAL_LOCK", "expires_at": expires_at, "payload": {}},
    )
    command_id = created.json()["command_id"]
    client.get("/api/v1/agent/commands", headers=agent_headers())

    db = TestSession()
    other_device_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    db.add(Device(id=other_device_id, child_id=CHILD_ID, name="Other", token_hash=hash_device_token("other-token"), applied_policy_version=0, revoked_at=None))
    db.add(DeviceAuthCredential(id=str(uuid4()), device_id=other_device_id, access_expires_at=utc_now() + timedelta(minutes=15), refresh_expires_at=utc_now() + timedelta(days=30), revoked_at=None, created_at=utc_now()))
    db.commit()
    db.close()

    wrong = client.post(
        f"/api/v1/agent/commands/{command_id}/ack",
        headers={"Authorization": "Bearer other-token"},
        json={"schema_version": 1, "command_id": command_id, "status": "executed", "observed_at": utc_now().isoformat() + "Z", "result_code": "SESSION_STATE_CONFIRMED"},
    )
    assert wrong.status_code == 404

    ack = client.post(
        f"/api/v1/agent/commands/{command_id}/ack",
        headers=agent_headers(),
        json={"schema_version": 1, "command_id": command_id, "status": "executed", "observed_at": utc_now().isoformat() + "Z", "result_code": "SESSION_STATE_CONFIRMED"},
    )
    assert ack.status_code == 200

    conflict = client.post(
        f"/api/v1/agent/commands/{command_id}/ack",
        headers=agent_headers(),
        json={"schema_version": 1, "command_id": command_id, "status": "failed", "observed_at": utc_now().isoformat() + "Z", "result_code": "LOCK_FAILED"},
    )
    assert conflict.status_code == 409
