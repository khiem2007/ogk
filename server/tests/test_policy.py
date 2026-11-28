import base64
import json
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from agent.core.policy_integrity import verify_policy_snapshot
from server.app.auth.security import hash_device_token, hash_password, utc_now
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.models.entities import (
    AuditLog,
    Child,
    Device,
    DeviceAuthCredential,
    Policy,
    User,
)


FIXTURE_PATH = Path("contracts/fixtures/policy.valid.json")
PARENT_ID = "11111111-1111-1111-1111-111111111111"
CHILD_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DEVICE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ACCESS_TOKEN = "test-device-access-token"
SIGNING_KEY_ID = "test-policy-key"
PRIVATE_KEY = bytes(range(32))


@pytest.fixture
def policy_api(
    migrated_sqlite: tuple[Engine, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker[Session], bytes]]:
    _, TestSession = migrated_sqlite
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    public_key = Ed25519PrivateKey.from_private_bytes(PRIVATE_KEY).public_key().public_bytes(
        Encoding.Raw,
        PublicFormat.Raw,
    )
    monkeypatch.setenv("OGK_POLICY_SIGNING_KEY_ID", SIGNING_KEY_ID)
    monkeypatch.setenv(
        "OGK_POLICY_SIGNING_PRIVATE_KEY",
        base64.b64encode(PRIVATE_KEY).decode("ascii"),
    )

    now = utc_now()
    db = TestSession()
    db.add(User(
        id=PARENT_ID,
        email="policy-parent@example.test",
        password_hash=hash_password("correct horse battery"),
        role="parent",
        created_at=now,
    ))
    db.flush()
    db.add(Child(
        id=CHILD_ID,
        owner_id=PARENT_ID,
        display_name="Test child",
        timezone="Asia/Ho_Chi_Minh",
    ))
    db.add(Device(
        id=DEVICE_ID,
        child_id=CHILD_ID,
        name="Test device",
        token_hash=hash_device_token(ACCESS_TOKEN),
        last_seen_at=now,
        applied_policy_version=None,
        revoked_at=None,
    ))
    db.flush()
    db.add(DeviceAuthCredential(
        id="cccccccc-cccc-cccc-cccc-cccccccccccc",
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
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "policy-parent@example.test", "password": "correct horse battery"},
        )
        assert login.status_code == 200
        client.headers.update({"X-CSRF-Token": login.headers["X-CSRF-Token"]})
        yield client, TestSession, public_key
    app.dependency_overrides.clear()


def policy_payload() -> dict[str, object]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return fixture["policy"]


def test_policy_update_signs_snapshot_and_rejects_stale_version(
    policy_api: tuple[TestClient, sessionmaker[Session], bytes],
) -> None:
    client, TestSession, public_key = policy_api
    update = client.put(
        f"/api/v1/devices/{DEVICE_ID}/policy",
        headers={"If-Match": '"0"'},
        json={"policy": policy_payload()},
    )

    assert update.status_code == 200
    snapshot = update.json()
    assert snapshot["policy_version"] == 1
    assert update.headers["ETag"] == '"1"'
    assert verify_policy_snapshot(
        snapshot,
        {SIGNING_KEY_ID: public_key},
        expected_device_id=DEVICE_ID,
        minimum_policy_version=1,
    ) == snapshot

    stale_update = client.put(
        f"/api/v1/devices/{DEVICE_ID}/policy",
        headers={"If-Match": '"0"'},
        json={"policy": {**policy_payload(), "manual_lock": True}},
    )
    assert stale_update.status_code == 409
    assert stale_update.json()["detail"]["code"] == "VERSION_CONFLICT"
    assert stale_update.json()["detail"]["current_version"] == 1

    parent_read = client.get(f"/api/v1/devices/{DEVICE_ID}/policy")
    agent_read = client.get(
        "/api/v1/agent/policy?version=0",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
    )
    assert parent_read.json() == snapshot
    assert agent_read.status_code == 200
    assert agent_read.json() == snapshot
    assert client.get(
        "/api/v1/agent/policy?version=1",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
    ).status_code == 304

    db = TestSession()
    assert db.query(Policy).filter_by(device_id=DEVICE_ID).count() == 1
    audit = db.query(AuditLog).filter_by(action="policy.updated").one()
    assert audit.after_json == '{"policy_version":1}'
    db.close()


def test_invalid_policy_is_not_persisted(
    policy_api: tuple[TestClient, sessionmaker[Session], bytes],
) -> None:
    client, TestSession, _ = policy_api
    invalid_policy = policy_payload()
    invalid_policy["manual_lock"] = "yes"

    response = client.put(
        f"/api/v1/devices/{DEVICE_ID}/policy",
        headers={"If-Match": '"0"'},
        json={"policy": invalid_policy},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "POLICY_SCHEMA_INVALID"
    db = TestSession()
    assert db.query(Policy).filter_by(device_id=DEVICE_ID).count() == 0
    assert db.query(AuditLog).filter_by(action="policy.updated").count() == 0
    db.close()


def test_policy_update_requires_configured_signing_key(
    policy_api: tuple[TestClient, sessionmaker[Session], bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, TestSession, _ = policy_api
    monkeypatch.delenv("OGK_POLICY_SIGNING_PRIVATE_KEY")

    response = client.put(
        f"/api/v1/devices/{DEVICE_ID}/policy",
        headers={"If-Match": '"0"'},
        json={"policy": policy_payload()},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "POLICY_SIGNING_UNAVAILABLE"
    db = TestSession()
    assert db.query(Policy).filter_by(device_id=DEVICE_ID).count() == 0
    db.close()


def test_parent_cannot_read_or_update_another_family_device(
    policy_api: tuple[TestClient, sessionmaker[Session], bytes],
) -> None:
    client, TestSession, _ = policy_api
    other_parent_id = "22222222-2222-2222-2222-222222222222"
    other_child_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    other_device_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    db = TestSession()
    db.add(User(
        id=other_parent_id,
        email="other-policy-parent@example.test",
        password_hash=hash_password("correct horse battery"),
        role="parent",
        created_at=utc_now(),
    ))
    db.flush()
    db.add(Child(
        id=other_child_id,
        owner_id=other_parent_id,
        display_name="Other child",
        timezone="Asia/Ho_Chi_Minh",
    ))
    db.flush()
    db.add(Device(
        id=other_device_id,
        child_id=other_child_id,
        name="Other device",
        token_hash=hash_device_token("other-device-token"),
        last_seen_at=utc_now(),
        applied_policy_version=None,
        revoked_at=None,
    ))
    db.commit()
    db.close()

    read = client.get(f"/api/v1/devices/{other_device_id}/policy")
    update = client.put(
        f"/api/v1/devices/{other_device_id}/policy",
        headers={"If-Match": '"0"'},
        json={"policy": policy_payload()},
    )

    assert read.status_code == 404
    assert update.status_code == 404
    db = TestSession()
    assert db.query(Policy).filter_by(device_id=other_device_id).count() == 0
    db.close()


def test_simultaneous_updates_with_same_version_create_one_snapshot(
    policy_api: tuple[TestClient, sessionmaker[Session], bytes],
) -> None:
    _, TestSession, _ = policy_api

    def submit_update() -> int:
        with TestClient(app) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "policy-parent@example.test", "password": "correct horse battery"},
            )
            assert login.status_code == 200
            response = client.put(
                f"/api/v1/devices/{DEVICE_ID}/policy",
                headers={
                    "X-CSRF-Token": login.headers["X-CSRF-Token"],
                    "If-Match": '"0"',
                },
                json={"policy": policy_payload()},
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(lambda _: submit_update(), range(2)))

    assert statuses == [200, 409]
    db = TestSession()
    policies = db.query(Policy).filter_by(device_id=DEVICE_ID).all()
    assert len(policies) == 1
    assert policies[0].version == 1
    db.close()
