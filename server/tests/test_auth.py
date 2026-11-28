from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.auth.security import hash_password
from server.app.db.session import get_db_session
from server.app.main import app
from server.app.models.entities import Child, User


@pytest.fixture
def auth_session(migrated_sqlite: tuple[Engine, sessionmaker[Session]]) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    _, TestSession = migrated_sqlite

    def override_db() -> Iterator[Session]:
        db = TestSession()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as client:
        yield client, TestSession
    app.dependency_overrides.clear()


def seed_parent(TestSession: sessionmaker[Session], email: str = "parent@example.test", role: str = "parent", child_id: str | None = None) -> str:
    db = TestSession()
    try:
        user_id = "11111111-1111-1111-1111-111111111111"
        db.add(User(
            id=user_id,
            email=email,
            password_hash=hash_password("correct horse battery"),
            role=role,
            child_id=child_id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        db.commit()
        return user_id
    finally:
        db.close()


def test_login_me_logout_and_children_owner(auth_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, TestSession = auth_session
    parent_id = seed_parent(TestSession)
    db = TestSession()
    db.add(Child(id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", owner_id=parent_id, display_name="My child", timezone="Asia/Ho_Chi_Minh"))
    db.commit()
    db.close()

    login = client.post("/api/v1/auth/login", json={"email":"parent@example.test", "password":"correct horse battery"})
    assert login.status_code == 200
    csrf = login.headers["X-CSRF-Token"]

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "parent"

    children = client.get("/api/v1/auth/children")
    assert children.status_code == 200
    assert len(children.json()) == 1

    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_lockout_after_five_failures(auth_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, TestSession = auth_session
    seed_parent(TestSession, email="lock@example.test")

    for _ in range(5):
        response = client.post("/api/v1/auth/login", json={"email":"lock@example.test", "password":"wrongpassword"})
        assert response.status_code == 401

    locked = client.post("/api/v1/auth/login", json={"email":"lock@example.test", "password":"wrongpassword"})
    assert locked.status_code == 429


def test_missing_and_wrong_csrf_are_rejected(auth_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, TestSession = auth_session
    seed_parent(TestSession, email="csrf@example.test")
    login = client.post("/api/v1/auth/login", json={"email":"csrf@example.test", "password":"correct horse battery"})
    assert login.status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token":"wrong"}).status_code == 403


def test_child_view_cannot_read_another_child(auth_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, TestSession = auth_session
    db = TestSession()
    own_child_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    db.add(User(id="44444444-4444-4444-4444-444444444444", email="other@example.test", password_hash=hash_password("correct horse battery"), role="parent", created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    db.flush()
    db.add(Child(id=own_child_id, owner_id="44444444-4444-4444-4444-444444444444", display_name="Own", timezone="Asia/Ho_Chi_Minh"))
    db.add(Child(id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", owner_id="44444444-4444-4444-4444-444444444444", display_name="Other", timezone="Asia/Ho_Chi_Minh"))
    db.flush()
    db.add(User(id="33333333-3333-3333-3333-333333333333", email="child@example.test", password_hash=hash_password("correct horse battery"), role="child-view", child_id=own_child_id, created_at=datetime.now(timezone.utc).replace(tzinfo=None)))
    db.commit()
    db.close()

    login = client.post("/api/v1/auth/login", json={"email":"child@example.test", "password":"correct horse battery"})
    assert login.status_code == 200
    children = client.get("/api/v1/auth/children")
    assert [item["id"] for item in children.json()] == ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]
