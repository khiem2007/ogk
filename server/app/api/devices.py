import hmac
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import update
from sqlalchemy.orm import Session

from server.app.auth.agent import get_current_device
from server.app.auth.dependencies import get_current_user, require_csrf
from server.app.auth.security import (
    enrollment_code_hash,
    hash_device_token,
    new_device_token,
    new_enrollment_code,
    utc_now,
)
from server.app.db.session import get_db_session
from server.app.models.entities import (
    AuditLog,
    Child,
    Device,
    DeviceAuthCredential,
    DeviceRefreshToken,
    EnrollmentAttempt,
    EnrollmentCode,
    User,
)


router = APIRouter()

CODE_TTL = timedelta(minutes=10)
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=30)
ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_FAILED_ATTEMPTS = 5


class EnrollmentCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    child_id: str = Field(min_length=1, max_length=36)


class EnrollmentCodeResponse(BaseModel):
    code: str
    expires_at: str


class DeviceEnrollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=8, max_length=8, pattern=r"^[A-HJ-NP-Z2-9]{8}$")
    name: str = Field(min_length=1, max_length=255)
    windows_sid: str | None = Field(default=None, max_length=255)


class DeviceTokenResponse(BaseModel):
    device_id: str
    access_token: str
    access_expires_at: str
    refresh_token: str
    refresh_expires_at: str


class DeviceRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=20, max_length=128)


class DeviceSummary(BaseModel):
    id: str
    child_id: str
    name: str
    last_seen_at: str | None
    revoked: bool


def _client_ip(request: Request) -> str:
    return (request.client.host if request.client else "unknown")[:45]


def _begin_write_transaction(db: Session) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")


def _peppered_code_hash(code: str) -> str:
    try:
        return enrollment_code_hash(code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ENROLLMENT_UNAVAILABLE",
        ) from exc


def _audit(
    db: Session,
    *,
    actor_user_id: str | None,
    device_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    now,
) -> None:
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        actor_user_id=actor_user_id,
        device_id=device_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_json=None,
        after_json=None,
        created_at=now,
    ))


def _check_enrollment_throttle(
    db: Session,
    ip_address: str,
    now,
) -> EnrollmentAttempt | None:
    attempt = db.get(EnrollmentAttempt, ip_address)
    if attempt and attempt.locked_until and attempt.locked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="ENROLLMENT_RATE_LIMITED")
    if attempt and attempt.window_started_at + ATTEMPT_WINDOW <= now:
        attempt.failed_count = 0
        attempt.window_started_at = now
        attempt.locked_until = None
    return attempt


def _record_enrollment_failure(
    db: Session,
    *,
    attempt: EnrollmentAttempt | None,
    ip_address: str,
    candidates: list[EnrollmentCode],
    now,
) -> None:
    if attempt is None:
        attempt = EnrollmentAttempt(
            ip_address=ip_address,
            failed_count=0,
            window_started_at=now,
            locked_until=None,
        )
        db.add(attempt)
    attempt.failed_count += 1
    if attempt.failed_count >= MAX_FAILED_ATTEMPTS:
        attempt.locked_until = now + ATTEMPT_WINDOW
    for candidate in candidates:
        if candidate.attempt_count < MAX_FAILED_ATTEMPTS:
            candidate.attempt_count += 1
    db.commit()
    if attempt.locked_until:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="ENROLLMENT_RATE_LIMITED")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ENROLLMENT_CODE_INVALID")


@router.post("/enrollment-codes", response_model=EnrollmentCodeResponse, status_code=status.HTTP_201_CREATED)
def create_enrollment_code(
    payload: EnrollmentCodeRequest,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db_session),
) -> EnrollmentCodeResponse:
    if user.role != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROLE_FORBIDDEN")
    child = db.query(Child).filter(Child.id == payload.child_id, Child.owner_id == user.id).first()
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CHILD_NOT_FOUND")

    now = utc_now()
    code = new_enrollment_code()
    code_record = EnrollmentCode(
        id=str(uuid.uuid4()),
        owner_id=user.id,
        child_id=child.id,
        code_hash=_peppered_code_hash(code),
        code_prefix=code[:4],
        expires_at=now + CODE_TTL,
        consumed_at=None,
        attempt_count=0,
    )
    db.add(code_record)
    _audit(
        db,
        actor_user_id=user.id,
        device_id=None,
        action="enrollment_code.created",
        resource_type="enrollment_code",
        resource_id=code_record.id,
        now=now,
    )
    db.commit()
    return EnrollmentCodeResponse(code=code, expires_at=code_record.expires_at.isoformat() + "Z")


@router.post("/agent/enroll", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
def enroll_device(
    payload: DeviceEnrollRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> DeviceTokenResponse:
    _begin_write_transaction(db)
    now = utc_now()
    ip_address = _client_ip(request)
    attempt = _check_enrollment_throttle(db, ip_address, now)
    prefix = payload.code[:4]
    candidates = (
        db.query(EnrollmentCode)
        .filter(
            EnrollmentCode.code_prefix == prefix,
            EnrollmentCode.consumed_at.is_(None),
            EnrollmentCode.attempt_count < MAX_FAILED_ATTEMPTS,
        )
        .all()
    )
    expected_hash = _peppered_code_hash(payload.code)
    code_record = next(
        (
            candidate for candidate in candidates
            if candidate.expires_at > now
            and candidate.child_id is not None
            and hmac.compare_digest(candidate.code_hash, expected_hash)
        ),
        None,
    )
    if code_record is None:
        _record_enrollment_failure(
            db, attempt=attempt, ip_address=ip_address, candidates=candidates, now=now
        )

    child = db.query(Child).filter(
        Child.id == code_record.child_id,
        Child.owner_id == code_record.owner_id,
    ).first()
    if child is None:
        _record_enrollment_failure(
            db, attempt=attempt, ip_address=ip_address, candidates=[code_record], now=now
        )

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="DEVICE_NAME_REQUIRED")

    consumed = db.execute(
        update(EnrollmentCode)
        .where(
            EnrollmentCode.id == code_record.id,
            EnrollmentCode.consumed_at.is_(None),
            EnrollmentCode.expires_at > now,
            EnrollmentCode.attempt_count < MAX_FAILED_ATTEMPTS,
        )
        .values(consumed_at=now)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ENROLLMENT_CODE_INVALID")
    code_record.consumed_at = now

    access_token = new_device_token()
    refresh_token = new_device_token()
    access_expires_at = now + ACCESS_TTL
    refresh_expires_at = now + REFRESH_TTL
    device = Device(
        id=str(uuid.uuid4()),
        child_id=child.id,
        windows_sid=payload.windows_sid,
        name=name,
        token_hash=hash_device_token(access_token),
        last_seen_at=now,
        applied_policy_version=None,
        revoked_at=None,
    )
    credential = DeviceAuthCredential(
        id=str(uuid.uuid4()),
        device_id=device.id,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        revoked_at=None,
        created_at=now,
    )
    if attempt:
        attempt.failed_count = 0
        attempt.locked_until = None
    db.add_all([
        device,
        credential,
        DeviceRefreshToken(
            id=str(uuid.uuid4()),
            credential_id=credential.id,
            token_hash=hash_device_token(refresh_token),
            expires_at=refresh_expires_at,
            consumed_at=None,
            created_at=now,
        ),
    ])
    db.flush()
    _audit(
        db,
        actor_user_id=code_record.owner_id,
        device_id=device.id,
        action="device.enrolled",
        resource_type="device",
        resource_id=device.id,
        now=now,
    )
    db.commit()
    return DeviceTokenResponse(
        device_id=device.id,
        access_token=access_token,
        access_expires_at=access_expires_at.isoformat() + "Z",
        refresh_token=refresh_token,
        refresh_expires_at=refresh_expires_at.isoformat() + "Z",
    )


@router.post("/agent/refresh", response_model=DeviceTokenResponse)
def refresh_device_token(
    payload: DeviceRefreshRequest,
    db: Session = Depends(get_db_session),
) -> DeviceTokenResponse:
    _begin_write_transaction(db)
    now = utc_now()
    refresh_token = db.query(DeviceRefreshToken).filter(
        DeviceRefreshToken.token_hash == hash_device_token(payload.refresh_token)
    ).first()
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_INVALID")

    credential = db.get(DeviceAuthCredential, refresh_token.credential_id)
    device = db.get(Device, credential.device_id) if credential else None
    if credential is None or device is None or device.revoked_at is not None or credential.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_INVALID")
    if refresh_token.consumed_at is not None:
        credential.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_REUSED")
    if refresh_token.expires_at <= now or credential.refresh_expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_EXPIRED")

    consumed = db.execute(
        update(DeviceRefreshToken)
        .where(
            DeviceRefreshToken.id == refresh_token.id,
            DeviceRefreshToken.consumed_at.is_(None),
            DeviceRefreshToken.expires_at > now,
        )
        .values(consumed_at=now)
    )
    if consumed.rowcount != 1:
        db.refresh(refresh_token)
        if refresh_token.consumed_at is not None:
            credential.revoked_at = now
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_REUSED")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="REFRESH_TOKEN_INVALID")

    access_token = new_device_token()
    next_refresh_token = new_device_token()
    access_expires_at = now + ACCESS_TTL
    credential.access_expires_at = access_expires_at
    device.token_hash = hash_device_token(access_token)
    db.add(DeviceRefreshToken(
        id=str(uuid.uuid4()),
        credential_id=credential.id,
        token_hash=hash_device_token(next_refresh_token),
        expires_at=credential.refresh_expires_at,
        consumed_at=None,
        created_at=now,
    ))
    db.commit()
    return DeviceTokenResponse(
        device_id=device.id,
        access_token=access_token,
        access_expires_at=access_expires_at.isoformat() + "Z",
        refresh_token=next_refresh_token,
        refresh_expires_at=credential.refresh_expires_at.isoformat() + "Z",
    )


@router.get("/devices", response_model=list[DeviceSummary])
def list_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[DeviceSummary]:
    if user.role == "child-view":
        if user.child_id is None:
            return []
        rows = db.query(Device).filter(Device.child_id == user.child_id).all()
    elif user.role == "admin":
        rows = db.query(Device).all()
    else:
        rows = db.query(Device).join(Child, Child.id == Device.child_id).filter(Child.owner_id == user.id).all()
    return [
        DeviceSummary(
            id=device.id,
            child_id=device.child_id,
            name=device.name,
            last_seen_at=device.last_seen_at.isoformat() + "Z" if device.last_seen_at else None,
            revoked=device.revoked_at is not None,
        )
        for device in rows
    ]


@router.post("/devices/{device_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device(
    device_id: str,
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db_session),
) -> Response:
    if user.role != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROLE_FORBIDDEN")
    device = (
        db.query(Device)
        .join(Child, Child.id == Device.child_id)
        .filter(Device.id == device_id, Child.owner_id == user.id)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DEVICE_NOT_FOUND")
    now = utc_now()
    device.revoked_at = now
    credential = db.query(DeviceAuthCredential).filter(DeviceAuthCredential.device_id == device.id).first()
    if credential:
        credential.revoked_at = now
    _audit(
        db,
        actor_user_id=user.id,
        device_id=device.id,
        action="device.revoked",
        resource_type="device",
        resource_id=device.id,
        now=now,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/agent/me")
def agent_me(device: Device = Depends(get_current_device)) -> dict[str, str]:
    return {"device_id": device.id}
