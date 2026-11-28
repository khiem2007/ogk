import json
import uuid
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.orm import Session

from server.app.auth.agent import get_current_device
from server.app.auth.dependencies import get_current_user, require_csrf
from server.app.auth.security import utc_now
from server.app.db.session import get_db_session
from server.app.models.entities import AuditLog, Child, Device, Grant, Policy, Request, UsageInterval, User
from server.app.services.policy import get_current_policy, get_owned_device, parse_policy_document


router = APIRouter()


class AgentRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    request_id: str = Field(min_length=36, max_length=36)
    request_type: Literal["time_extension", "app_exception", "false_positive"]
    created_at: datetime
    reason: str = Field(min_length=1, max_length=2000)
    payload: dict


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected"]


def _uuid(value: str, field: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"INVALID_{field.upper()}") from exc


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return value.isoformat(timespec="seconds") + "Z"


def _db_now(value: datetime) -> datetime:
    return value.replace(tzinfo=None)


def _begin_write(db: Session) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _audit(db: Session, *, actor: str | None, device_id: str, action: str, request_id: str, before: dict | None, after: dict | None, now: datetime) -> None:
    db.add(AuditLog(
        id=str(uuid.uuid4()), actor_user_id=actor, device_id=device_id,
        action=action, resource_type="request", resource_id=request_id,
        before_json=json.dumps(before, sort_keys=True, separators=(",", ":")) if before is not None else None,
        after_json=json.dumps(after, sort_keys=True, separators=(",", ":")) if after is not None else None,
        created_at=now,
    ))


def _device_owner(db: Session, device_id: str, user: User) -> Device:
    device = get_owned_device(db, device_id=device_id, owner_id=user.id)
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    return device


def _validate_request_payload(payload: AgentRequestCreate, child: Child) -> dict:
    data = payload.payload
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="REQUEST_PAYLOAD_INVALID")

    if payload.request_type == "time_extension":
        if set(data) != {"amount_seconds", "local_date"}:
            raise HTTPException(status_code=422, detail="REQUEST_PAYLOAD_INVALID")
        amount = data["amount_seconds"]
        local_date = data["local_date"]
        if isinstance(amount, bool) or not isinstance(amount, int) or not 60 <= amount <= 14400:
            raise HTTPException(status_code=422, detail="REQUEST_PAYLOAD_INVALID")
        try:
            now_local = utc_now().astimezone(ZoneInfo(child.timezone)).date().isoformat()
        except ZoneInfoNotFoundError:
            raise HTTPException(status_code=422, detail="CHILD_TIMEZONE_INVALID")
        if not isinstance(local_date, str) or local_date != now_local:
            raise HTTPException(status_code=422, detail="LOCAL_DATE_MISMATCH")
        return {"amount_seconds": amount, "local_date": local_date}

    if payload.request_type == "app_exception":
        if set(data) != {"app_id", "duration_seconds"}:
            raise HTTPException(status_code=422, detail="REQUEST_PAYLOAD_INVALID")
        duration = data["duration_seconds"]
        if isinstance(duration, bool) or not isinstance(duration, int) or not 60 <= duration <= 14400:
            raise HTTPException(status_code=422, detail="REQUEST_PAYLOAD_INVALID")
        app_id = _uuid(str(data["app_id"]), "app_id")
        return {"app_id": app_id, "duration_seconds": duration}

    if set(data) - {"domain"} or not isinstance(data.get("domain"), str) or not data["domain"]:
        raise HTTPException(status_code=422, detail="REQUEST_PAYLOAD_INVALID")
    return {"domain": data["domain"][:255]}


def _policy_for_device(db: Session, device_id: str) -> dict | None:
    policy = get_current_policy(db, device_id=device_id)
    if policy is None:
        return None
    try:
        return parse_policy_document(policy.document_json)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="POLICY_STORAGE_INVALID") from exc


def _quota_remaining(db: Session, device: Device, child: Child, duration_seconds: int, local_date: str) -> int:
    policy = _policy_for_device(db, device.id)
    if policy is None:
        return duration_seconds
    policy_doc = policy["policy"] if "policy" in policy else policy
    quota = policy_doc.get("quotas", {}).get("total_daily_seconds")
    if not isinstance(quota, int):
        return duration_seconds

    tz = ZoneInfo(child.timezone)
    day = datetime.strptime(local_date, "%Y-%m-%d").date()
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    end = (datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(days=1)).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    used = sum(row.active_seconds for row in db.query(UsageInterval).filter(
        UsageInterval.device_id == device.id,
        UsageInterval.start_utc >= start,
        UsageInterval.end_utc <= end,
    ).all())
    for grant in db.query(Grant).filter(Grant.device_id == device.id, Grant.local_date == local_date).all():
        used += grant.amount_seconds
    return max(0, quota - used)


@router.post("/agent/requests", status_code=status.HTTP_200_OK)
def create_agent_request(payload: AgentRequestCreate, device: Device = Depends(get_current_device), db: Session = Depends(get_db_session)) -> dict:
    request_id = _uuid(payload.request_id, "request_id")
    child = db.get(Child, device.child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="CHILD_NOT_FOUND")
    normalized = _validate_request_payload(payload, child)

    _begin_write(db)
    existing = db.get(Request, request_id)
    if existing is not None:
        if existing.device_id != device.id:
            raise HTTPException(status_code=409, detail="REQUEST_ID_CONFLICT")
        db.commit()
        return {
            "request_id": existing.id, "device_id": existing.device_id, "request_type": existing.request_type,
            "status": existing.status, "payload": json.loads(existing.payload_json), "reason": existing.reason,
            "created_at": _utc_iso(existing.created_at), "decided_at": _utc_iso(existing.decided_at) if existing.decided_at else None,
        }

    now = utc_now()
    request = Request(
        id=request_id, device_id=device.id, request_type=payload.request_type,
        payload_json=json.dumps(normalized, sort_keys=True, separators=(",", ":")),
        reason=payload.reason.strip(), status="pending", decided_by=None,
        created_at=_db_now(now), decided_at=None,
    )
    db.add(request)
    db.commit()
    return {
        "request_id": request.id, "device_id": request.device_id, "request_type": request.request_type,
        "status": request.status, "payload": normalized, "reason": request.reason,
        "created_at": _utc_iso(request.created_at), "decided_at": None,
    }


@router.get("/requests")
def list_requests(status_filter: str | None = Query(default=None, alias="status"), user: User = Depends(get_current_user), db: Session = Depends(get_db_session)) -> list[dict]:
    if user.role not in {"parent", "admin", "child-view"}:
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    if status_filter not in {None, "pending", "approved", "rejected", "expired"}:
        raise HTTPException(status_code=422, detail="REQUEST_STATUS_INVALID")
    query = db.query(Request).join(Device, Device.id == Request.device_id).join(Child, Child.id == Device.child_id)
    if user.role != "admin":
        query = query.filter(Child.owner_id == user.id)
    if status_filter:
        query = query.filter(Request.status == status_filter)
    rows = query.order_by(Request.created_at.desc()).all()
    result = []
    for request in rows:
        child = db.query(Child).join(Device, Device.child_id == Child.id).filter(Device.id == request.device_id).first()
        result.append({
            "request_id": request.id, "device_id": request.device_id,
            "child_name": child.display_name if child else "Unknown",
            "request_type": request.request_type, "payload": json.loads(request.payload_json),
            "reason": request.reason, "status": request.status,
            "decided_by": request.decided_by, "created_at": _utc_iso(request.created_at),
            "decided_at": _utc_iso(request.decided_at) if request.decided_at else None,
        })
    return result


@router.post("/requests/{request_id}/decision")
def decide_request(request_id: str, payload: DecisionRequest, user: User = Depends(get_current_user), _: None = Depends(require_csrf), db: Session = Depends(get_db_session)) -> dict:
    if user.role not in {"parent", "admin"}:
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    request_id = _uuid(request_id, "request_id")
    _begin_write(db)
    request = db.get(Request, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="REQUEST_NOT_FOUND")
    device = db.get(Device, request.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    child = db.get(Child, device.child_id)
    if child is None or (user.role != "admin" and child.owner_id != user.id):
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    if request.status != "pending":
        raise HTTPException(status_code=409, detail="REQUEST_ALREADY_DECIDED")

    now = utc_now()
    before = {"status": request.status}
    request.status = payload.decision
    request.decided_by = user.id
    request.decided_at = _db_now(now)

    grant = None
    if payload.decision == "approved" and request.request_type in {"time_extension", "app_exception"}:
        data = json.loads(request.payload_json)
        policy = _policy_for_device(db, device.id)
        policy_doc = policy["policy"] if policy and "policy" in policy else (policy or {})

        if request.request_type == "app_exception" and policy_doc.get("manual_lock") is True:
            raise HTTPException(status_code=409, detail="MANUAL_LOCK_ACTIVE")

        if request.request_type == "time_extension":
            duration = data["amount_seconds"]
            local_date = data["local_date"]
        else:
            duration = data["duration_seconds"]
            try:
                local_date = now.astimezone(ZoneInfo(child.timezone)).date().isoformat()
            except ZoneInfoNotFoundError:
                raise HTTPException(status_code=422, detail="CHILD_TIMEZONE_INVALID")

        remaining = _quota_remaining(db, device, child, duration, local_date)
        if remaining < duration:
            raise HTTPException(status_code=409, detail={"code": "QUOTA_EXCEEDED", "remaining_seconds": remaining})

        grant_id = str(uuid.uuid4())
        valid_from = _db_now(now)
        valid_until = _db_now(now + timedelta(seconds=duration))
        scope = {"local_date": local_date, "amount_seconds": duration} if request.request_type == "time_extension" else {"app_id": data["app_id"]}
        grant = Grant(
            id=grant_id, request_id=request.id, device_id=device.id,
            scope_json=json.dumps(scope, sort_keys=True, separators=(",", ":")),
            valid_from=valid_from, valid_until=valid_until,
            amount_seconds=duration, local_date=local_date,
        )
        db.add(grant)

    after = {"status": request.status, "grant_id": grant.id if grant else None}
    db.flush()
    _audit(db, actor=user.id, device_id=device.id, action="request.decided", request_id=request.id,
           before=before, after=after, now=_db_now(now))
    db.commit()
    return {
        "request_id": request.id, "device_id": request.device_id, "request_type": request.request_type,
        "status": request.status, "payload": json.loads(request.payload_json), "reason": request.reason,
        "decided_by": request.decided_by, "created_at": _utc_iso(request.created_at),
        "decided_at": _utc_iso(request.decided_at) if request.decided_at else None,
        "grant": {
            "grant_id": grant.id, "device_id": grant.device_id, "valid_from": _utc_iso(grant.valid_from),
            "valid_until": _utc_iso(grant.valid_until), "scope": json.loads(grant.scope_json),
        } if grant else None,
    }


@router.get("/agent/grants")
def list_agent_grants(device: Device = Depends(get_current_device), db: Session = Depends(get_db_session)) -> list[dict]:
    now = utc_now().replace(tzinfo=None)
    grants = db.query(Grant).filter(Grant.device_id == device.id, Grant.valid_until > now).order_by(Grant.valid_from.desc()).all()
    return [{
        "grant_id": grant.id, "source_request_id": grant.request_id, "device_id": grant.device_id,
        "valid_from": _utc_iso(grant.valid_from), "valid_until": _utc_iso(grant.valid_until),
        "scope": json.loads(grant.scope_json),
    } for grant in grants]
