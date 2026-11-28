"""Policy snapshot persistence and signing helpers."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from contracts.policy_signing import (
    decode_private_key,
    sign_policy_snapshot,
    validate_policy_key_id,
    validate_policy_snapshot,
)
from server.app.auth.security import utc_now
from server.app.models.entities import AuditLog, Child, Device, Policy


class PolicyVersionConflict(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version
        super().__init__("policy version does not match expected version")


def load_signing_material() -> tuple[str, bytes]:
    key_id = os.getenv("OGK_POLICY_SIGNING_KEY_ID", "").strip()
    encoded_key = os.getenv("OGK_POLICY_SIGNING_PRIVATE_KEY", "")
    if not key_id or not encoded_key:
        raise ValueError("policy signing key ID and private key must be configured")
    validate_policy_key_id(key_id)
    return key_id, decode_private_key(encoded_key)


def get_owned_device(db: Session, *, device_id: str, owner_id: str) -> Device | None:
    return (
        db.query(Device)
        .join(Child, Child.id == Device.child_id)
        .filter(Device.id == device_id, Child.owner_id == owner_id)
        .first()
    )


def get_current_policy(db: Session, *, device_id: str) -> Policy | None:
    return db.execute(
        select(Policy)
        .where(Policy.device_id == device_id)
        .order_by(Policy.version.desc())
        .limit(1)
    ).scalar_one_or_none()


def create_policy_snapshot(
    db: Session,
    *,
    device: Device,
    created_by: str,
    expected_version: int,
    policy: dict[str, Any],
    key_id: str,
    private_key: bytes,
) -> dict[str, Any]:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    locked_device = db.execute(
        select(Device).where(Device.id == device.id).with_for_update()
    ).scalar_one_or_none()
    if locked_device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DEVICE_NOT_FOUND")

    current = get_current_policy(db, device_id=device.id)
    current_version = current.version if current else 0
    if current_version != expected_version:
        raise PolicyVersionConflict(current_version)

    now = utc_now()
    snapshot = {
        "schema_version": 1,
        "device_id": device.id,
        "policy_version": current_version + 1,
        "issued_at": _rfc3339(now),
        "policy": policy,
    }
    validate_policy_snapshot({
        **snapshot,
        "signature": {
            "algorithm": "Ed25519",
            "key_id": key_id,
            "value": "A" * 86 + "==",
        },
    })
    signed_snapshot = sign_policy_snapshot(
        snapshot,
        key_id=key_id,
        private_key=private_key,
    )
    db.add(Policy(
        id=str(uuid.uuid4()),
        device_id=device.id,
        version=current_version + 1,
        document_json=json.dumps(
            signed_snapshot,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ),
        created_by=created_by,
        created_at=now,
    ))
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        actor_user_id=created_by,
        device_id=device.id,
        action="policy.updated",
        resource_type="policy",
        resource_id=f"{device.id}:{current_version + 1}",
        before_json=None,
        after_json=json.dumps(
            {"policy_version": current_version + 1},
            separators=(",", ":"),
        ),
        created_at=now,
    ))
    db.flush()
    return signed_snapshot


def parse_policy_document(document_json: str) -> dict[str, Any]:
    value = json.loads(document_json)
    if not isinstance(value, dict):
        raise ValueError("stored policy snapshot must be an object")
    return value


def _rfc3339(value: datetime) -> str:
    return value.isoformat(timespec="seconds") + "Z"
