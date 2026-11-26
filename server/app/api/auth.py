import os
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from server.app.auth.dependencies import get_current_user, require_csrf
from server.app.auth.security import (
    hash_csrf_token,
    new_csrf_token,
    new_session_id,
    session_expiry,
    utc_now,
    validate_password_length,
    verify_password,
)
from server.app.db.session import get_db_session
from server.app.models.entities import AuthSession, Child, LoginAttempt, User


router = APIRouter()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=4096)


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    child_id: str | None = None


class ChildResponse(BaseModel):
    id: str
    display_name: str
    age_band: str | None = None
    timezone: str


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:45]
    return (request.client.host if request.client else "unknown")[:45]


@router.post("/login", status_code=status.HTTP_200_OK)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db_session)) -> MeResponse:
    email = payload.email.strip().lower()
    ip_address = _client_ip(request)

    if not validate_password_length(payload.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PASSWORD_TOO_SHORT")

    attempt = db.query(LoginAttempt).filter(
        LoginAttempt.email == email,
        LoginAttempt.ip_address == ip_address,
    ).first()
    now = utc_now()
    if attempt and attempt.locked_until and attempt.locked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="LOGIN_LOCKED")

    user = db.query(User).filter(User.email == email).first()
    valid = bool(user and verify_password(user.password_hash, payload.password))

    if not valid:
        if attempt is None:
            attempt = LoginAttempt(
                id=str(uuid.uuid4()),
                email=email,
                ip_address=ip_address,
                failed_count=0,
                locked_until=None,
                updated_at=now,
            )
            db.add(attempt)
        attempt.failed_count += 1
        attempt.updated_at = now
        if attempt.failed_count >= 5:
            attempt.locked_until = now + timedelta(minutes=15)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")

    if attempt:
        db.delete(attempt)

    session_id = new_session_id()
    csrf_token = new_csrf_token()
    auth_session = AuthSession(
        id=session_id,
        user_id=user.id,
        csrf_token_hash=hash_csrf_token(csrf_token),
        expires_at=session_expiry(now),
        revoked_at=None,
        created_at=now,
    )
    db.add(auth_session)

    secure_cookie = os.getenv("OGK_ENV", "development").lower() in {"production", "prod"}
    response.set_cookie(
        key="ogk_session",
        value=session_id,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=12 * 60 * 60,
        path="/",
    )
    response.set_cookie(
        key="ogk_csrf",
        value=csrf_token,
        httponly=False,
        secure=secure_cookie,
        samesite="lax",
        max_age=12 * 60 * 60,
        path="/",
    )
    response.headers["X-CSRF-Token"] = csrf_token
    return MeResponse(id=user.id, email=user.email, role=user.role, child_id=user.child_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    _: None = Depends(require_csrf),
) -> Response:
    session_id = request.cookies.get("ogk_session")
    auth_session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    if auth_session:
        auth_session.revoked_at = utc_now()
    response.delete_cookie("ogk_session", path="/")
    response.delete_cookie("ogk_csrf", path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, role=user.role, child_id=user.child_id)


@router.get("/children", response_model=list[ChildResponse])
def list_children(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ChildResponse]:
    if user.role == "child-view":
        if user.child_id is None:
            return []
        children = db.query(Child).filter(Child.id == user.child_id).all()
    elif user.role == "admin":
        children = db.query(Child).all()
    else:
        children = db.query(Child).filter(Child.owner_id == user.id).all()
    return [
        ChildResponse(id=item.id, display_name=item.display_name, age_band=item.age_band, timezone=item.timezone)
        for item in children
    ]
