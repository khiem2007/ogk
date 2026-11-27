from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from server.app.auth.security import hash_csrf_token, utc_now
from server.app.db.session import get_db_session
from server.app.models.entities import AuthSession, User


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db_session),
) -> User:
    session_id = request.cookies.get("ogk_session")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTH_REQUIRED")

    now = utc_now()
    auth_session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= now
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SESSION_INVALID")

    user = db.query(User).filter(User.id == auth_session.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="USER_NOT_FOUND")
    return user


def require_role(*roles: str) -> Callable:
    async def guard(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db_session)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROLE_FORBIDDEN")
        return user

    return guard


def require_csrf(
    request: Request,
    db: Session = Depends(get_db_session),
) -> None:
    session_id = request.cookies.get("ogk_session")
    supplied = request.headers.get("X-CSRF-Token")
    if not session_id or not supplied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF_REQUIRED")

    auth_session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= utc_now()
        or auth_session.csrf_token_hash != hash_csrf_token(supplied)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF_INVALID")
