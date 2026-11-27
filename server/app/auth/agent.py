from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from server.app.auth.security import hash_device_token, utc_now
from server.app.db.session import get_db_session
from server.app.models.entities import Device, DeviceAuthCredential


def get_current_device(
    request: Request,
    db: Session = Depends(get_db_session),
) -> Device:
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="DEVICE_AUTH_REQUIRED")

    device = (
        db.query(Device)
        .join(DeviceAuthCredential, DeviceAuthCredential.device_id == Device.id)
        .filter(
            Device.token_hash == hash_device_token(token),
            Device.revoked_at.is_(None),
            DeviceAuthCredential.revoked_at.is_(None),
            DeviceAuthCredential.access_expires_at > utc_now(),
        )
        .first()
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="DEVICE_TOKEN_INVALID")
    return device
