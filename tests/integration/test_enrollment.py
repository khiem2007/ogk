from concurrent.futures import ThreadPoolExecutor
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.auth.security import hash_password, utc_now
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.models.entities import (
    Child,
    Device,
    DeviceAuthCredential,
    DeviceRefreshToken,
    EnrollmentAttempt,
    EnrollmentCode,
    User,
)


@pytest.fixture
def enrolled_api(
    migrated_sqlite: tuple[Engine, sessionmaker[Session]],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker[Session], str, str]]:
    _, TestSession = migrated_sqlite
    monkeypatch.setenv("OGK_ENROLLMENT_PEPPER", "test-enrollment-pepper-value-32-bytes-minimum")
    parent_id = "11111111-1111-1111-1111-111111111111"
    child_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    db = TestSession()
    db.add(User(
        id=parent_id,
        email="parent@example.test",
        password_hash=hash_password("correct horse battery"),
        role="parent",
        created_at=utc_now(),
    ))
    db.flush()
    db.add(Child(
        id=child_id,
        owner_id=parent_id,
        display_name="Test child",
        timezone="Asia/Ho_Chi_Minh",
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
            json={"email": "parent@example.test", "password": "correct horse battery"},
        )
        assert login.status_code == 200
        client.headers.update({"X-CSRF-Token": login.headers["X-CSRF-Token"]})
        yield client, TestSession, parent_id, child_id
    app.dependency_overrides.clear()


def create_code(client: TestClient, child_id: str) -> str:
    response = client.post("/api/v1/enrollment-codes", json={"child_id": child_id})
    assert response.status_code == 201
    return response.json()["code"]


def enroll(client: TestClient, code: str, name: str = "Child PC") -> dict[str, str]:
    response = client.post(
        "/api/v1/agent/enroll",
        json={"code": code, "name": name},
    )
    assert response.status_code == 201
    return response.json()


def test_enrollment_is_one_time_and_secrets_are_hashed(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
) -> None:
    client, TestSession, _, child_id = enrolled_api
    requested_at = utc_now()
    code = create_code(client, child_id)
    assert len(code) == 8
    assert all(character in "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" for character in code)

    db = TestSession()
    stored_code = db.query(EnrollmentCode).one()
    assert stored_code.child_id == child_id
    assert stored_code.code_hash != code
    assert stored_code.code_prefix == code[:4]
    assert abs(stored_code.expires_at - requested_at - timedelta(minutes=10)) < timedelta(seconds=2)
    db.close()

    tokens = enroll(client, code)
    assert len(tokens["access_token"]) >= 40
    assert len(tokens["refresh_token"]) >= 40

    db = TestSession()
    device = db.get(Device, tokens["device_id"])
    credential = db.query(DeviceAuthCredential).filter_by(device_id=device.id).one()
    refresh = db.query(DeviceRefreshToken).one()
    stored_code = db.query(EnrollmentCode).one()
    assert device.child_id == child_id
    assert device.token_hash != tokens["access_token"]
    assert credential.access_expires_at - credential.created_at == timedelta(minutes=15)
    assert credential.refresh_expires_at - credential.created_at == timedelta(days=30)
    assert refresh.token_hash != tokens["refresh_token"]
    assert stored_code.consumed_at is not None
    db.close()

    repeated = client.post("/api/v1/agent/enroll", json={"code": code, "name": "Second PC"})
    assert repeated.status_code == 401
    assert client.get(
        "/api/v1/agent/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ).json() == {"device_id": tokens["device_id"]}


def test_simultaneous_enrollment_consumes_code_once(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
) -> None:
    _, _, _, child_id = enrolled_api
    code = create_code(enrolled_api[0], child_id)

    def submit_enrollment() -> int:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/agent/enroll",
                json={"code": code, "name": "Child PC"},
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(lambda _: submit_enrollment(), range(2)))
    assert statuses == [201, 401]


def test_wrong_code_attempts_are_limited(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
) -> None:
    client, TestSession, _, child_id = enrolled_api
    code = create_code(client, child_id)
    replacement = "A" if code[-1] != "A" else "B"
    invalid = code[:-1] + replacement
    statuses = [
        client.post("/api/v1/agent/enroll", json={"code": invalid, "name": "Child PC"}).status_code
        for _ in range(5)
    ]
    assert statuses == [401, 401, 401, 401, 429]

    db = TestSession()
    attempt = db.query(EnrollmentAttempt).one()
    assert attempt.failed_count == 5
    assert attempt.locked_until is not None
    code_record = db.query(EnrollmentCode).one()
    assert code_record.attempt_count == 5
    db.close()


def test_code_expiry_ownership_and_csrf(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
) -> None:
    client, TestSession, _, child_id = enrolled_api
    forbidden_child = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    response = client.post("/api/v1/enrollment-codes", json={"child_id": forbidden_child})
    assert response.status_code == 404

    with TestClient(app) as no_csrf:
        login = no_csrf.post(
            "/api/v1/auth/login",
            json={"email": "parent@example.test", "password": "correct horse battery"},
        )
        assert login.status_code == 200
        assert no_csrf.post(
            "/api/v1/enrollment-codes",
            json={"child_id": child_id},
        ).status_code == 403

    code = create_code(client, child_id)
    db = TestSession()
    code_record = db.query(EnrollmentCode).one()
    code_record.expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    db.close()
    expired = client.post("/api/v1/agent/enroll", json={"code": code, "name": "Child PC"})
    assert expired.status_code == 401
    assert client.get("/api/v1/devices").json() == []


def test_enrollment_requires_server_pepper(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, TestSession, _, child_id = enrolled_api
    monkeypatch.delenv("OGK_ENROLLMENT_PEPPER")
    response = client.post("/api/v1/enrollment-codes", json={"child_id": child_id})
    assert response.status_code == 503

    db = TestSession()
    assert db.query(EnrollmentCode).count() == 0
    db.close()


def test_refresh_rotates_tokens_and_replay_revokes_credential(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
) -> None:
    client, _, _, child_id = enrolled_api
    original = enroll(client, create_code(client, child_id))
    old_access = {"Authorization": f"Bearer {original['access_token']}"}

    refresh = client.post(
        "/api/v1/agent/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert refresh.status_code == 200
    rotated = refresh.json()
    assert rotated["access_token"] != original["access_token"]
    assert rotated["refresh_token"] != original["refresh_token"]
    assert client.get("/api/v1/agent/me", headers=old_access).status_code == 401
    assert client.get(
        "/api/v1/agent/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    ).status_code == 200

    replay = client.post(
        "/api/v1/agent/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert replay.status_code == 401
    assert replay.json()["detail"] == "REFRESH_TOKEN_REUSED"
    assert client.get(
        "/api/v1/agent/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    ).status_code == 401


def test_access_expiry_and_device_revoke(
    enrolled_api: tuple[TestClient, sessionmaker[Session], str, str],
) -> None:
    client, TestSession, _, child_id = enrolled_api
    tokens = enroll(client, create_code(client, child_id))
    db = TestSession()
    credential = db.query(DeviceAuthCredential).one()
    credential.access_expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    db.close()
    auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/api/v1/agent/me", headers=auth_header).status_code == 401

    refreshed = client.post(
        "/api/v1/agent/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).json()
    assert client.get(
        "/api/v1/agent/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    ).status_code == 200

    db = TestSession()
    other_parent_id = "22222222-2222-2222-2222-222222222222"
    db.add(User(
        id=other_parent_id,
        email="other@example.test",
        password_hash=hash_password("correct horse battery"),
        role="parent",
        created_at=utc_now(),
    ))
    db.commit()
    db.close()
    with TestClient(app) as other_client:
        login = other_client.post(
            "/api/v1/auth/login",
            json={"email": "other@example.test", "password": "correct horse battery"},
        )
        assert login.status_code == 200
        other_client.headers.update({"X-CSRF-Token": login.headers["X-CSRF-Token"]})
        assert other_client.post(
            f"/api/v1/devices/{tokens['device_id']}/revoke"
        ).status_code == 404

    revoke = client.post(f"/api/v1/devices/{tokens['device_id']}/revoke")
    assert revoke.status_code == 204
    assert client.get(
        "/api/v1/agent/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    ).status_code == 401
    assert client.get("/api/v1/devices").json()[0]["revoked"] is True
