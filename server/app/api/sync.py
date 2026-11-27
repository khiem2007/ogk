import json
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from server.app.auth.agent import get_current_device
from server.app.auth.security import utc_now
from server.app.db.session import get_db_session
from server.app.models.entities import AppCatalog, Child, Device, DeviceEvent, UsageInterval
from server.app.services.ingest import begin_write_transaction, connection_state
from server.app.services.policy import get_current_policy


router = APIRouter()
MAX_EVENT_BATCH = 100


class HeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    applied_policy_version: int = Field(default=0, ge=0)
    agent_version: str = Field(default="unknown", min_length=1, max_length=64)
    health: dict[str, Any] = Field(default_factory=dict, max_length=8)


class HeartbeatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    server_time: str
    desired_policy_version: int
    connection_state: Literal["online"]


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    event_id: str = Field(min_length=36, max_length=36)
    boot_id: str = Field(min_length=36, max_length=36)
    sequence: int = Field(ge=0)
    observed_at: datetime
    event_type: Literal["usage.interval", "app.blocked", "domain.blocked", "telemetry.gap"]
    payload: dict[str, Any]


class EventBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[EventEnvelope] = Field(min_length=1, max_length=MAX_EVENT_BATCH)


class EventBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acknowledged_event_ids: list[str]
    accepted_count: int
    replayed_count: int
    server_time: str


def _parse_uuid(value: str, field: str) -> str:
    try:
        parsed = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"INVALID_{field.upper()}") from exc
    return parsed


def _validate_payload(event: EventEnvelope) -> dict[str, Any]:
    payload = event.payload
    try:
        if event.event_type == "usage.interval":
            required = {"started_at", "ended_at", "active_seconds", "telemetry_quality"}
            if set(payload) - {"started_at", "ended_at", "active_seconds", "app_id", "category", "telemetry_quality"}:
                raise ValueError
            if not required.issubset(payload):
                raise ValueError
            start = datetime.fromisoformat(str(payload["started_at"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(payload["ended_at"]).replace("Z", "+00:00"))
            active = payload["active_seconds"]
            if not isinstance(active, int) or isinstance(active, bool) or not 1 <= active <= 86400:
                raise ValueError
            if end <= start:
                raise ValueError
            if payload["telemetry_quality"] not in {"measured", "estimated"}:
                raise ValueError
            if payload.get("category") not in {None, "education", "entertainment", "games", "other"}:
                raise ValueError
            if payload.get("app_id") is not None:
                payload["app_id"] = _parse_uuid(str(payload["app_id"]), "app_id")
            return payload

        if event.event_type in {"app.blocked", "domain.blocked"}:
            required = {"rule_id", "reason_code", "subject_type"}
            if set(payload) - {"rule_id", "reason_code", "subject_type", "category"}:
                raise ValueError
            if not required.issubset(payload):
                raise ValueError
            payload["rule_id"] = _parse_uuid(str(payload["rule_id"]), "rule_id")
            if payload["subject_type"] not in {"app", "domain"}:
                raise ValueError
            expected_reason = "APP_BLOCKED" if event.event_type == "app.blocked" else "DOMAIN_BLOCKED"
            if payload["reason_code"] != expected_reason:
                raise ValueError
            if payload.get("category") not in {None, "education", "entertainment", "games", "other"}:
                raise ValueError
            return payload

        if event.event_type == "telemetry.gap":
            if set(payload) - {"started_at", "ended_at", "reason_code"}:
                raise ValueError
            if not {"started_at", "ended_at", "reason_code"}.issubset(payload):
                raise ValueError
            start = datetime.fromisoformat(str(payload["started_at"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(payload["ended_at"]).replace("Z", "+00:00"))
            if end <= start:
                raise ValueError
            if payload["reason_code"] not in {"HELPER_UNAVAILABLE", "SESSION_UNKNOWN", "CLOCK_SUSPECT", "SLEEP_GAP"}:
                raise ValueError
            return payload
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="EVENT_PAYLOAD_INVALID") from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="EVENT_PAYLOAD_INVALID")



def _utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        return value.isoformat().replace("+00:00", "Z")
    return value.isoformat() + "Z"


def _db_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


@router.post("/agent/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    payload: HeartbeatRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    begin_write_transaction(db)
    now = utc_now()
    device.last_seen_at = now
    device.applied_policy_version = payload.applied_policy_version
    current = get_current_policy(db, device_id=device.id)
    desired = current.version if current else 0
    db.add(device)
    db.commit()
    return {
        "server_time": _utc_iso(now),
        "desired_policy_version": desired,
        "connection_state": connection_state(now, now),
    }


@router.post("/agent/events/batch", response_model=EventBatchResponse)
def ingest_event_batch(
    payload: EventBatchRequest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db_session),
) -> dict[str, object]:
    begin_write_transaction(db)
    now = utc_now()
    acknowledged: list[str] = []
    accepted = 0
    replayed = 0
    seen: set[str] = set()

    for event in payload.events:
        event.event_id = _parse_uuid(event.event_id, "event_id")
        event.boot_id = _parse_uuid(event.boot_id, "boot_id")
        normalized = _validate_payload(event)

        if event.event_id in seen:
            replayed += 1
            acknowledged.append(event.event_id)
            continue

        existing_usage = db.query(UsageInterval).filter_by(device_id=device.id, event_id=event.event_id).first()
        existing_event = db.query(DeviceEvent).filter_by(device_id=device.id, event_id=event.event_id).first()
        if existing_usage is not None or existing_event is not None:
            replayed += 1
            acknowledged.append(event.event_id)
            seen.add(event.event_id)
            continue

        if event.event_type == "usage.interval":
            app_id = normalized.get("app_id")
            if app_id is not None:
                app = (
                    db.query(AppCatalog)
                    .join(Child, Child.owner_id == AppCatalog.owner_id)
                    .filter(AppCatalog.id == app_id, Child.id == device.child_id)
                    .first()
                )
                if app is None:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="APP_ID_INVALID")
            started = datetime.fromisoformat(str(normalized["started_at"]).replace("Z", "+00:00"))
            ended = datetime.fromisoformat(str(normalized["ended_at"]).replace("Z", "+00:00"))
            db.add(UsageInterval(
                id=str(uuid.uuid4()),
                event_id=event.event_id,
                device_id=device.id,
                start_utc=_db_datetime(started),
                end_utc=_db_datetime(ended),
                active_seconds=int(normalized["active_seconds"]),
                app_id=normalized.get("app_id"),
                sequence=event.sequence,
                boot_id=event.boot_id,
            ))
        else:
            reason_code = normalized.get("reason_code")
            if event.event_type == "telemetry.gap":
                reason_code = str(normalized["reason_code"])
            db.add(DeviceEvent(
                id=str(uuid.uuid4()),
                event_id=event.event_id,
                device_id=device.id,
                event_type=event.event_type,
                observed_at=_db_datetime(event.observed_at),
                reason_code=reason_code,
                payload_json=json.dumps(normalized, separators=(",", ":"), ensure_ascii=False),
            ))

        seen.add(event.event_id)
        accepted += 1
        acknowledged.append(event.event_id)

    db.commit()
    return {
        "acknowledged_event_ids": acknowledged,
        "accepted_count": accepted,
        "replayed_count": replayed,
        "server_time": _utc_iso(now),
    }
