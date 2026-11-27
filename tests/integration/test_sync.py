import json
from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.auth.security import hash_device_token, utc_now
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.services.ingest import connection_state
from server.app.models.entities import (
    Child,
    Device,
    DeviceAuthCredential,
    DeviceEvent,
    UsageInterval,
    User,
)


PARENT_ID = "11111111-1111-1111-1111-111111111111"
CHILD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DEVICE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
CREDENTIAL_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
ACCESS_TOKEN = "test-device-access-token"


@pytest.fixture
def sync_api(
    migrated_sqlite: tuple[Engine, sessionmaker[Session]],
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    _, TestSession = migrated_sqlite
    now = utc_now()
    db = TestSession()
    db.add(User(id=PARENT_ID, email="sync-parent@example.test", password_hash="hash", role="parent", created_at=now))
    db.flush()
    db.add(Child(id=CHILD_ID, owner_id=PARENT_ID, display_name="Test child", timezone="Asia/Ho_Chi_Minh"))
    db.add(Device(
        id=DEVICE_ID,
        child_id=CHILD_ID,
        name="Test device",
        token_hash=hash_device_token(ACCESS_TOKEN),
        last_seen_at=None,
        applied_policy_version=0,
        revoked_at=None,
    ))
    db.flush()
    db.add(DeviceAuthCredential(
        id=CREDENTIAL_ID,
        device_id=DEVICE_ID,
        access_expires_at=now + timedelta(minutes=15),
        refresh_expires_at=now + timedelta(days=30),
        revoked_at=None,
        created_at=now,
    ))
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
        yield client, TestSession
    app.dependency_overrides.clear()


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def usage_event(event_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "boot_id": str(uuid4()),
        "sequence": 7,
        "observed_at": "2026-11-27T10:00:00Z",
        "event_type": "usage.interval",
        "payload": {
            "started_at": "2026-11-27T09:59:00Z",
            "ended_at": "2026-11-27T10:00:00Z",
            "active_seconds": 60,
            "telemetry_quality": "measured",
        },
    }


def test_heartbeat_updates_last_seen_and_requires_valid_device(
    sync_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, TestSession = sync_api

    unauthorized = client.post("/api/v1/agent/heartbeat", json={"applied_policy_version": 1})
    assert unauthorized.status_code == 401

    response = client.post(
        "/api/v1/agent/heartbeat",
        headers=auth_headers(),
        json={"applied_policy_version": 1, "agent_version": "1.0.0", "health": {"offline": False}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["desired_policy_version"] == 0
    assert body["connection_state"] == "online"
    assert body["server_time"].endswith("Z")

    db = TestSession()
    device = db.get(Device, DEVICE_ID)
    assert device is not None
    assert device.last_seen_at is not None
    assert device.applied_policy_version == 1
    db.close()


def test_event_batch_lost_ack_retry_is_idempotent(
    sync_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, TestSession = sync_api
    event_id = str(uuid4())

    first = client.post(
        "/api/v1/agent/events/batch",
        headers=auth_headers(),
        json={"events": [usage_event(event_id)]},
    )
    assert first.status_code == 200
    assert first.json()["accepted_count"] == 1
    assert first.json()["replayed_count"] == 0
    assert first.json()["acknowledged_event_ids"] == [event_id]

    replay = client.post(
        "/api/v1/agent/events/batch",
        headers=auth_headers(),
        json={"events": [usage_event(event_id)]},
    )
    assert replay.status_code == 200
    assert replay.json()["accepted_count"] == 0
    assert replay.json()["replayed_count"] == 1

    db = TestSession()
    assert db.query(UsageInterval).filter_by(device_id=DEVICE_ID, event_id=event_id).count() == 1
    db.close()


def test_event_batch_rejects_invalid_payload_without_commit(
    sync_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, TestSession = sync_api
    invalid = usage_event(str(uuid4()))
    invalid["payload"] = {"started_at": "2026-11-27T10:00:00Z", "ended_at": "2026-11-27T09:59:00Z", "active_seconds": 60, "telemetry_quality": "measured"}

    response = client.post(
        "/api/v1/agent/events/batch",
        headers=auth_headers(),
        json={"events": [invalid]},
    )
    assert response.status_code == 422

    db = TestSession()
    assert db.query(UsageInterval).count() == 0
    assert db.query(DeviceEvent).count() == 0
    db.close()


def test_event_batch_duplicate_in_same_request_is_acknowledged_once(
    sync_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, TestSession = sync_api
    event_id = str(uuid4())

    response = client.post(
        "/api/v1/agent/events/batch",
        headers=auth_headers(),
        json={"events": [usage_event(event_id), usage_event(event_id)]},
    )
    assert response.status_code == 200
    assert response.json()["accepted_count"] == 1
    assert response.json()["replayed_count"] == 1

    db = TestSession()
    assert db.query(UsageInterval).filter_by(device_id=DEVICE_ID, event_id=event_id).count() == 1
    db.close()


def test_connection_state_uses_180_second_threshold() -> None:
    now = utc_now()
    assert connection_state(now - timedelta(seconds=180), now) == "online"
    assert connection_state(now - timedelta(seconds=181), now) == "lost"
    assert connection_state(None, now) == "unknown"


def test_event_batch_has_fixed_upper_bound(
    sync_api: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = sync_api
    events = [usage_event(str(uuid4())) for _ in range(101)]
    response = client.post("/api/v1/agent/events/batch", headers=auth_headers(), json={"events": events})
    assert response.status_code == 422
