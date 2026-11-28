import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from server.app.auth.agent import get_current_device
from server.app.auth.dependencies import get_current_user, require_csrf
from server.app.auth.security import hash_device_token, utc_now
from server.app.db.session import get_db_session
from server.app.models.entities import AuditLog, Child, Command, Device, DeviceAuthCredential, User
from server.app.services.policy import get_owned_device

router = APIRouter()

ALLOWLIST = {"LOCK_SESSION", "CLEAR_MANUAL_LOCK", "TEMPORARY_TIME_EXEMPTION", "EXEMPT_UNTIL_LOCAL_DAY_END"}
_PENDING_NOTIFICATIONS: dict[str, set[str]] = {}


class CreateCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: str | None = Field(default=None, min_length=36, max_length=36)
    command_type: Literal["LOCK_SESSION", "CLEAR_MANUAL_LOCK", "TEMPORARY_TIME_EXEMPTION", "EXEMPT_UNTIL_LOCAL_DAY_END"]
    expires_at: datetime
    payload: dict = Field(default_factory=dict)
    dedup_key: str | None = Field(default=None, min_length=36, max_length=36)


class AckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    command_id: str = Field(min_length=36, max_length=36)
    status: Literal["executed", "failed", "expired"]
    observed_at: datetime
    result_code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]{1,64}$")
    details: dict | None = Field(default=None, max_length=8)


def _uuid(value: str, field: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"INVALID_{field.upper()}") from exc


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.replace(tzinfo=None)
    return value.isoformat(timespec="seconds") + "Z"


def _db_now(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def _normalize_expires(value: datetime) -> datetime:
    return _db_now(value)


def _begin_write(db: Session) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _audit(db: Session, *, actor: str | None, device_id: str, action: str, command_id: str, before: dict | None, after: dict | None, now: datetime) -> None:
    db.add(AuditLog(
        id=str(uuid.uuid4()), actor_user_id=actor, device_id=device_id,
        action=action, resource_type="command", resource_id=command_id,
        before_json=json.dumps(before, sort_keys=True, separators=(",", ":")) if before is not None else None,
        after_json=json.dumps(after, sort_keys=True, separators=(",", ":")) if after is not None else None,
        created_at=_db_now(now),
    ))


def _validate_payload(command_type: str, payload: dict) -> dict:
    if command_type in {"LOCK_SESSION", "CLEAR_MANUAL_LOCK"}:
        if payload:
            raise HTTPException(status_code=422, detail="COMMAND_PAYLOAD_INVALID")
        return {}
    if command_type == "TEMPORARY_TIME_EXEMPTION":
        if set(payload) != {"grant_id", "duration_seconds", "scope"}:
            raise HTTPException(status_code=422, detail="COMMAND_PAYLOAD_INVALID")
        grant_id = _uuid(str(payload["grant_id"]), "grant_id")
        if payload["duration_seconds"] != 900 or payload["scope"] != "time_limits":
            raise HTTPException(status_code=422, detail="COMMAND_PAYLOAD_INVALID")
        return {"grant_id": grant_id, "duration_seconds": 900, "scope": "time_limits"}
    if command_type == "EXEMPT_UNTIL_LOCAL_DAY_END":
        if set(payload) != {"grant_id", "scope"}:
            raise HTTPException(status_code=422, detail="COMMAND_PAYLOAD_INVALID")
        grant_id = _uuid(str(payload["grant_id"]), "grant_id")
        if payload["scope"] != "time_limits":
            raise HTTPException(status_code=422, detail="COMMAND_PAYLOAD_INVALID")
        return {"grant_id": grant_id, "scope": "time_limits"}
    raise HTTPException(status_code=422, detail="COMMAND_TYPE_NOT_ALLOWLISTED")


def _command_json(command: Command) -> dict:
    return {
        "schema_version": 1,
        "command_id": command.id,
        "command_type": command.type,
        "issued_at": _utc_iso(command.issued_at),
        "expires_at": _utc_iso(command.expires_at),
        "payload": json.loads(command.payload_json),
        "status": command.status,
    }


@router.post("/devices/{device_id}/commands", status_code=status.HTTP_201_CREATED)
def create_command(
    device_id: str,
    payload: CreateCommandRequest,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db_session),
) -> dict:
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    device_id = _uuid(device_id, "device_id")
    device = get_owned_device(db, device_id=device_id, owner_id=user.id)
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    if payload.command_type not in ALLOWLIST:
        raise HTTPException(status_code=422, detail="COMMAND_TYPE_NOT_ALLOWLISTED")

    normalized_payload = _validate_payload(payload.command_type, payload.payload)
    now = utc_now()
    expires_at = _normalize_expires(payload.expires_at)
    if expires_at <= now:
        raise HTTPException(status_code=422, detail="COMMAND_ALREADY_EXPIRED")
    if expires_at - now > timedelta(minutes=24 * 60):
        raise HTTPException(status_code=422, detail="COMMAND_TTL_TOO_LONG")

    command_id = _uuid(payload.command_id, "command_id") if payload.command_id else str(uuid.uuid4())
    dedup_key = _uuid(payload.dedup_key, "dedup_key") if payload.dedup_key else command_id

    _begin_write(db)
    existing = db.query(Command).filter_by(device_id=device.id, dedup_key=dedup_key).first()
    if existing is not None:
        db.commit()
        return _command_json(existing)

    command = Command(
        id=command_id,
        device_id=device.id,
        type=payload.command_type,
        payload_json=json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")),
        issued_at=_db_now(now),
        expires_at=expires_at,
        delivered_at=None,
        resolved_at=None,
        status="queued",
        dedup_key=dedup_key,
        result_json=None,
    )
    db.add(command)
    _audit(db, actor=user.id, device_id=device.id, action="command.created", command_id=command.id,
           before=None, after={"status": "queued", "type": command.type, "expires_at": _utc_iso(expires_at)}, now=now)
    db.commit()

    _PENDING_NOTIFICATIONS.setdefault(device.id, set()).add(command.id)
    return _command_json(command)


@router.get("/devices/{device_id}/commands")
def list_commands(
    device_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    device_id = _uuid(device_id, "device_id")
    device = get_owned_device(db, device_id=device_id, owner_id=user.id)
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    now = utc_now()
    commands = db.query(Command).filter_by(device_id=device.id).order_by(Command.issued_at.desc()).all()
    for command in commands:
        if command.status in {"queued", "delivered"} and command.expires_at <= now:
            before = {"status": command.status}
            command.status = "expired"
            command.resolved_at = _db_now(now)
            command.result_json = json.dumps({"status": "expired", "result_code": "COMMAND_EXPIRED", "observed_at": _utc_iso(now)}, sort_keys=True)
            _audit(db, actor=None, device_id=device.id, action="command.expired", command_id=command.id,
                   before=before, after={"status": "expired", "result_code": "COMMAND_EXPIRED"}, now=now)
    db.commit()
    return [_command_json(command) for command in commands]


@router.get("/agent/commands")
def poll_commands(
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db_session),
) -> dict:
    _begin_write(db)
    now = utc_now()
    commands = db.query(Command).filter_by(device_id=device.id).all()
    pending = []
    for command in commands:
        if command.status in {"queued", "delivered"}:
            if command.expires_at <= now:
                before = {"status": command.status}
                command.status = "expired"
                command.resolved_at = _db_now(now)
                command.result_json = json.dumps({"status": "expired", "result_code": "COMMAND_EXPIRED", "observed_at": _utc_iso(now)}, sort_keys=True)
                _audit(db, actor=None, device_id=device.id, action="command.expired", command_id=command.id,
                       before=before, after={"status": "expired", "result_code": "COMMAND_EXPIRED"}, now=now)
                continue
            if command.status == "queued":
                before = {"status": "queued"}
                command.status = "delivered"
                command.delivered_at = _db_now(now)
                _audit(db, actor=None, device_id=device.id, action="command.delivered", command_id=command.id,
                       before=before, after={"status": "delivered"}, now=now)
            pending.append(_command_json(command))
    db.commit()
    return {"commands": pending, "server_time": _utc_iso(now)}


@router.post("/agent/commands/{command_id}/ack")
def acknowledge_command(
    command_id: str,
    payload: AckRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db_session),
) -> dict:
    command_id = _uuid(command_id, "command_id")
    ack_id = _uuid(payload.command_id, "command_id")
    if command_id != ack_id:
        raise HTTPException(status_code=409, detail="COMMAND_ID_MISMATCH")

    _begin_write(db)
    command = db.get(Command, command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="COMMAND_NOT_FOUND")
    if command.device_id != device.id:
        raise HTTPException(status_code=404, detail="COMMAND_NOT_FOUND")

    if command.status in {"executed", "failed", "expired"}:
        existing = json.loads(command.result_json) if command.result_json else None
        if existing is not None:
            replay_matches = existing.get("status") == payload.status and existing.get("result_code") == payload.result_code
            if replay_matches:
                db.commit()
                return {"command_id": command.id, "status": command.status, "replayed": True}
        raise HTTPException(status_code=409, detail="COMMAND_RESULT_ALREADY_RESOLVED")

    now = utc_now()
    if command.status not in {"delivered", "queued"}:
        raise HTTPException(status_code=409, detail="COMMAND_STATE_INVALID")
    if command.expires_at <= now and payload.status != "expired":
        before = {"status": command.status}
        command.status = "expired"
        command.resolved_at = _db_now(now)
        command.result_json = json.dumps({"status": "expired", "result_code": "COMMAND_EXPIRED", "observed_at": _utc_iso(now)}, sort_keys=True)
        _audit(db, actor=None, device_id=device.id, action="command.expired", command_id=command.id,
               before=before, after={"status": "expired", "result_code": "COMMAND_EXPIRED"}, now=now)
        db.commit()
        return {"command_id": command.id, "status": "expired", "replayed": False}

    before = {"status": command.status}
    command.status = payload.status
    command.resolved_at = _db_now(payload.observed_at)
    result = {
        "status": payload.status,
        "observed_at": _utc_iso(payload.observed_at),
        "result_code": payload.result_code,
        "details": payload.details or {},
    }
    command.result_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
    action = "command.executed" if payload.status == "executed" else "command.failed" if payload.status == "failed" else "command.expired"
    _audit(db, actor=None, device_id=device.id, action=action, command_id=command.id,
           before=before, after=result, now=_db_now(payload.observed_at))
    db.commit()
    return {"command_id": command.id, "status": command.status, "replayed": False}


@router.websocket("/agent/commands/notify")
async def command_notify(websocket: WebSocket, access_token: str, db: Session = Depends(get_db_session)) -> None:
    device = (
        db.query(Device)
        .join(DeviceAuthCredential, DeviceAuthCredential.device_id == Device.id)
        .filter(
            Device.token_hash == hash_device_token(access_token),
            Device.revoked_at.is_(None),
            DeviceAuthCredential.revoked_at.is_(None),
            DeviceAuthCredential.access_expires_at > utc_now(),
        )
        .first()
    )
    if device is None:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    while True:
        pending = _PENDING_NOTIFICATIONS.setdefault(device.id, set())
        if pending:
            for command_id in sorted(pending):
                await websocket.send_json({"type": "command.created", "command_id": command_id})
                pending.remove(command_id)
        try:
            await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        except WebSocketDisconnect:
            break
