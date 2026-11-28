import json
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from server.app.auth.dependencies import get_current_user, require_csrf
from server.app.auth.security import utc_now
from server.app.db.session import get_db_session
from server.app.models.entities import (
    AppCatalog,
    AuditLog,
    Child,
    Command,
    Device,
    DeviceEvent,
    Grant,
    Policy,
    Request,
    TransparencyRecord,
    UsageInterval,
    User,
)

router = APIRouter()


def _uuid(value: str, field: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"INVALID_{field.upper()}") from exc


def _db_now(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.replace(tzinfo=None)
    return value.isoformat(timespec="seconds") + "Z"


def _parse_local_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="LOCAL_DATE_INVALID") from exc


def _timezone(child: Child) -> ZoneInfo:
    try:
        return ZoneInfo(child.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail="CHILD_TIMEZONE_INVALID") from exc


def _utc_boundary(local: datetime, tz: ZoneInfo) -> datetime:
    return datetime(local.year, local.month, local.day, tzinfo=tz).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def _authorized_child(db: Session, user: User, child_id: str) -> Child:
    child_id = _uuid(child_id, "child_id")
    child = db.get(Child, child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="CHILD_NOT_FOUND")
    if user.role == "admin":
        return child
    if user.role == "child-view" and user.child_id == child.id:
        return child
    if user.role == "parent" and child.owner_id == user.id:
        return child
    raise HTTPException(status_code=404, detail="CHILD_NOT_FOUND")


def _authorized_device(db: Session, user: User, child: Child, device_id: str) -> Device:
    device_id = _uuid(device_id, "device_id")
    device = db.query(Device).filter(Device.id == device_id, Device.child_id == child.id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    if user.role == "parent" and child.owner_id != user.id:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    return device


def _merge_seconds(intervals: list[tuple[datetime, datetime]]) -> int:
    """Union overlapping intervals once, in UTC."""
    if not intervals:
        return 0
    merged: list[list[datetime]] = []
    for start, end in sorted(intervals, key=lambda item: item[0]):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        elif end > merged[-1][1]:
            merged[-1][1] = end
    return int(sum((end - start).total_seconds() for start, end in merged))


def _usage_rows(db: Session, device_id: str, start_utc: datetime, end_utc: datetime) -> list[UsageInterval]:
    return db.query(UsageInterval).filter(
        UsageInterval.device_id == device_id,
        UsageInterval.start_utc < end_utc,
        UsageInterval.end_utc > start_utc,
    ).all()


def _build_report(db: Session, device: Device, child: Child, start_date: datetime, end_date: datetime) -> dict:
    tz = _timezone(child)
    start_utc = _utc_boundary(start_date, tz)
    end_utc = _utc_boundary(end_date, tz)

    # event_id deduplication is the ingestion authority; repeated DB rows cannot exist,
    # but this guard also makes reporting stable against legacy/fixture duplicates.
    seen: set[str] = set()
    all_intervals: list[tuple[datetime, datetime]] = []
    app_intervals: dict[str, list[tuple[datetime, datetime]]] = {}
    category_intervals: dict[str, list[tuple[datetime, datetime]]] = {}

    for row in _usage_rows(db, device.id, start_utc, end_utc):
        if row.event_id in seen:
            continue
        seen.add(row.event_id)
        overlap_start = max(row.start_utc, start_utc)
        overlap_end = min(row.end_utc, end_utc)
        if overlap_end <= overlap_start:
            continue
        interval = (overlap_start, overlap_end)
        all_intervals.append(interval)
        app_label = "Unattributed"
        if row.app_id:
            app = db.get(AppCatalog, row.app_id)
            if app:
                app_label = app.display_name
                category = app.category or "other"
            else:
                category = "other"
        else:
            category = "other"
        app_intervals.setdefault(app_label, []).append(interval)
        category_intervals.setdefault(category, []).append(interval)

    total = _merge_seconds(all_intervals)
    top_apps = sorted(
        ({"app": name, "seconds": _merge_seconds(intervals)} for name, intervals in app_intervals.items()),
        key=lambda item: (-item["seconds"], item["app"]),
    )[:10]
    category_breakdown = sorted(
        ({"category": name, "seconds": _merge_seconds(intervals)} for name, intervals in category_intervals.items()),
        key=lambda item: (-item["seconds"], item["category"]),
    )

    gaps = db.query(DeviceEvent).filter(
        DeviceEvent.device_id == device.id,
        DeviceEvent.event_type == "telemetry.gap",
        DeviceEvent.observed_at >= start_utc,
        DeviceEvent.observed_at < end_utc,
    ).order_by(DeviceEvent.observed_at.desc()).all()
    blocks = db.query(DeviceEvent).filter(
        DeviceEvent.device_id == device.id,
        DeviceEvent.event_type.in_(["app.blocked", "domain.blocked"]),
        DeviceEvent.observed_at >= start_utc,
        DeviceEvent.observed_at < end_utc,
    ).all()

    domain_counts: dict[str, int] = {}
    app_block_counts: dict[str, int] = {}
    for block in blocks:
        try:
            payload = json.loads(block.payload_json)
        except json.JSONDecodeError:
            payload = {}
        if block.event_type == "domain.blocked":
            key = str(payload.get("domain", payload.get("rule_id", "redacted")))
            domain_counts[key] = domain_counts.get(key, 0) + 1
        else:
            key = str(payload.get("app_id", payload.get("rule_id", "redacted")))
            app_block_counts[key] = app_block_counts.get(key, 0) + 1

    top_domains = sorted(
        ({"domain": name, "count": count} for name, count in domain_counts.items()),
        key=lambda item: (-item["count"], item["domain"]),
    )[:10]
    top_apps_with_blocks = sorted(
        ({"app_id": name, "count": count} for name, count in app_block_counts.items()),
        key=lambda item: (-item["count"], item["app_id"]),
    )[:10]

    requests = db.query(Request).filter(Request.device_id == device.id, Request.created_at >= start_utc, Request.created_at < end_utc).all()
    request_summary = {
        "total": len(requests),
        "pending": sum(row.status == "pending" for row in requests),
        "approved": sum(row.status == "approved" for row in requests),
        "rejected": sum(row.status == "rejected" for row in requests),
    }

    missing = bool(gaps)
    result = {
        "child_id": child.id,
        "device_id": device.id,
        "timezone": child.timezone,
        "machine_total_seconds": total,
        "usage_seconds": total,
        "top_apps": top_apps,
        "top_10_apps": top_apps,
        "top_domains": top_domains,
        "top_10_domains": top_domains,
        "category_breakdown": category_breakdown,
        "block_counts": {
            "total": len(blocks),
            "app": sum(row.event_type == "app.blocked" for row in blocks),
            "domain": sum(row.event_type == "domain.blocked" for row in blocks),
            "top_apps": top_apps_with_blocks,
        },
        "request_summary": request_summary,
        "missing_telemetry": missing,
        "telemetry_status": "missing" if missing else "measured",
        "gaps": [{"observed_at": _utc_iso(row.observed_at), "reason_code": row.reason_code} for row in gaps[:20]],
    }
    return result


@router.get("/reports/daily")
def daily_report(
    device_id: str = Query(...),
    date: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict:
    if user.role not in {"parent", "admin", "child-view"}:
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    if date is None:
        date = utc_now().astimezone(ZoneInfo("UTC")).date().isoformat()
    local_day = _parse_local_date(date)
    device_id = _uuid(device_id, "device_id")
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    child = db.get(Child, device.child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="CHILD_NOT_FOUND")
    if user.role == "child-view":
        if user.child_id != child.id:
            raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    elif user.role == "parent" and child.owner_id != user.id:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")

    report = _build_report(db, device, child, local_day, local_day + timedelta(days=1))
    report.update({"date": date, "period": "daily", "start_date": date, "end_date": date})
    return report


@router.get("/reports/weekly")
def weekly_report(
    device_id: str = Query(...),
    week_start: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict:
    if user.role not in {"parent", "admin", "child-view"}:
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    if week_start is None:
        week_start = utc_now().date().isoformat()
    start = _parse_local_date(week_start)
    if start.weekday() != 0:
        raise HTTPException(status_code=422, detail="WEEK_START_MUST_BE_MONDAY")
    device_id = _uuid(device_id, "device_id")
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    child = db.get(Child, device.child_id)
    if child is None:
        raise HTTPException(status_code=404, detail="CHILD_NOT_FOUND")
    if user.role == "child-view":
        if user.child_id != child.id:
            raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")
    elif user.role == "parent" and child.owner_id != user.id:
        raise HTTPException(status_code=404, detail="DEVICE_NOT_FOUND")

    report = _build_report(db, device, child, start, start + timedelta(days=7))
    report.update({"week_start": week_start, "period": "weekly", "start_date": week_start, "end_date": (start + timedelta(days=6)).strftime("%Y-%m-%d")})
    return report


def _audit_cursor(row: AuditLog) -> str:
    return f"{row.created_at.isoformat(timespec='microseconds')}:{row.id}"


def _parse_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if cursor is None:
        return None
    try:
        timestamp, row_id = cursor.rsplit(":", 1)
        return datetime.fromisoformat(timestamp), str(uuid.UUID(row_id))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail="AUDIT_CURSOR_INVALID") from exc


@router.get("/audit")
def audit_report(
    device_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict:
    if user.role not in {"parent", "admin", "child-view"}:
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")

    query = db.query(AuditLog)
    if user.role != "admin":
        owned_device_ids = db.query(Device.id).join(Child, Child.id == Device.child_id)
        if user.role == "child-view":
            if user.child_id is None:
                owned_device_ids = owned_device_ids.filter(False)
            else:
                owned_device_ids = owned_device_ids.filter(Child.id == user.child_id)
        else:
            owned_device_ids = owned_device_ids.filter(Child.owner_id == user.id)
        owned_child_ids = db.query(Child.id)
        if user.role == "child-view":
            owned_child_ids = owned_child_ids.filter(Child.id == user.child_id) if user.child_id else owned_child_ids.filter(False)
        else:
            owned_child_ids = owned_child_ids.filter(Child.owner_id == user.id)
        query = query.filter(or_(
            AuditLog.actor_user_id == user.id,
            AuditLog.device_id.in_(owned_device_ids),
            AuditLog.resource_id.in_(owned_child_ids),
        ))

    if device_id:
        device_id = _uuid(device_id, "device_id")
        query = query.filter(AuditLog.device_id == device_id)
    if action:
        query = query.filter(AuditLog.action == action)

    parsed = _parse_cursor(cursor)
    if parsed:
        cursor_time, cursor_id = parsed
        query = query.filter(or_(AuditLog.created_at < cursor_time, (AuditLog.created_at == cursor_time) & (AuditLog.id < cursor_id)))

    rows = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1).all()
    has_next = len(rows) > limit
    rows = rows[:limit]

    items = []
    sensitive_keys = {"password", "token", "access_token", "refresh_token", "csrf", "windows_sid", "url", "title", "window_title"}

    def redact(value):
        if isinstance(value, dict):
            return {key: ("[REDACTED]" if key.lower() in sensitive_keys else redact(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    for row in rows:
        before = json.loads(row.before_json) if row.before_json else None
        after = json.loads(row.after_json) if row.after_json else None
        items.append({
            "id": row.id,
            "actor_user_id": row.actor_user_id,
            "device_id": row.device_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "before": redact(before),
            "after": redact(after),
            "created_at": _utc_iso(row.created_at),
        })

    return {
        "items": items,
        "next_cursor": _audit_cursor(rows[-1]) if has_next and rows else None,
        "has_next": has_next,
    }


@router.post("/children/{child_id}/delete-all")
def delete_all_child_data(
    child_id: str,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db_session),
) -> dict:
    if user.role != "parent":
        raise HTTPException(status_code=403, detail="ROLE_FORBIDDEN")
    child = _authorized_child(db, user, child_id)

    devices = db.query(Device).filter(Device.child_id == child.id).all()
    now = utc_now()
    expires_at = now + timedelta(hours=24)

    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")

    command_ids: list[str] = []
    delete_dedup_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f"openguard-delete-all:{child.id}"))
    for device in devices:
        existing = db.query(Command).filter_by(device_id=device.id, dedup_key=delete_dedup_key).first()
        if existing:
            command_ids.append(existing.id)
            continue
        command_id = str(uuid.uuid4())
        command = Command(
            id=command_id,
            device_id=device.id,
            type="DELETE_ALL_DATA",
            payload_json="{}",
            issued_at=_db_now(now),
            expires_at=_db_now(expires_at),
            delivered_at=None,
            resolved_at=None,
            status="queued",
            dedup_key=delete_dedup_key,
            result_json=None,
        )
        db.add(command)
        command_ids.append(command_id)

    # Preserve only a redacted tombstone. Child/device identifiers are deleted after
    # commands and the tombstone have been written in the same transaction.
    tombstone_exists = db.query(AuditLog).filter_by(
        actor_user_id=user.id, action="child.delete_all", resource_type="child", resource_id=child.id
    ).first()
    if tombstone_exists is None:
        db.add(AuditLog(
            id=str(uuid.uuid4()), actor_user_id=user.id, device_id=None,
            action="child.delete_all", resource_type="child", resource_id=child.id,
            before_json=None,
            after_json=json.dumps({"status": "server_data_deleted", "child_id": "[REDACTED]"}, sort_keys=True),
            created_at=_db_now(now),
        ))

    for device in devices:
        db.query(UsageInterval).filter(UsageInterval.device_id == device.id).delete(synchronize_session=False)
        db.query(DeviceEvent).filter(DeviceEvent.device_id == device.id).delete(synchronize_session=False)
        db.query(Grant).filter(Grant.device_id == device.id).delete(synchronize_session=False)
        db.query(Request).filter(Request.device_id == device.id).delete(synchronize_session=False)
        db.query(Policy).filter(Policy.device_id == device.id).delete(synchronize_session=False)
        db.query(Command).filter(Command.device_id == device.id, Command.type != "DELETE_ALL_DATA").delete(synchronize_session=False)
    db.query(TransparencyRecord).filter(TransparencyRecord.child_id == child.id).delete(synchronize_session=False)
    db.commit()

    return {
        "child_id": child_id,
        "status": "server_data_deleted",
        "agent_cache_status": "pending" if command_ids else "no_devices",
        "command_ids": command_ids,
        "deleted_at": _utc_iso(now),
    }
