import json
import re
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from contracts.policy_signing import PolicyContractError
from server.app.auth.agent import get_current_device
from server.app.auth.dependencies import get_current_user, require_csrf
from server.app.db.session import get_db_session
from server.app.models.entities import Device, Policy, User
from server.app.services.policy import (
    PolicyVersionConflict,
    create_policy_snapshot,
    get_current_policy,
    get_owned_device,
    load_signing_material,
    parse_policy_document,
)


router = APIRouter()
_ETAG_PATTERN = re.compile(r'^"(0|[1-9][0-9]*)"$')


class PolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy: dict[str, Any]
    expected_version: int | None = Field(default=None, ge=0)


class PolicySignature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    algorithm: str
    key_id: str
    value: str


class PolicySnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int
    device_id: str
    policy_version: int
    issued_at: str
    policy: dict[str, Any]
    signature: PolicySignature


def _read_snapshot(policy: Policy) -> dict[str, Any]:
    try:
        return parse_policy_document(policy.document_json)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="POLICY_STORAGE_INVALID",
        ) from exc


def _parse_expected_version(if_match: str | None, body_version: int | None) -> int:
    header_version: int | None = None
    if if_match is not None:
        match = _ETAG_PATTERN.fullmatch(if_match.strip())
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IF_MATCH_INVALID",
            )
        header_version = int(match.group(1))

    if header_version is not None and body_version is not None and header_version != body_version:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="VERSION_PRECONDITION_MISMATCH")
    expected_version = header_version if header_version is not None else body_version
    if expected_version is None:
        raise HTTPException(status_code=428, detail="VERSION_REQUIRED")
    return expected_version


@router.get(
    "/devices/{device_id}/policy",
    response_model=PolicySnapshotResponse,
)
def get_parent_policy(
    device_id: str,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    if user.role != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROLE_FORBIDDEN")
    device = get_owned_device(db, device_id=device_id, owner_id=user.id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DEVICE_NOT_FOUND")
    current = get_current_policy(db, device_id=device.id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POLICY_NOT_FOUND")
    snapshot = _read_snapshot(current)
    response.headers["ETag"] = f'"{current.version}"'
    return snapshot


@router.put(
    "/devices/{device_id}/policy",
    response_model=PolicySnapshotResponse,
    status_code=status.HTTP_200_OK,
)
def update_parent_policy(
    device_id: str,
    payload: PolicyUpdateRequest,
    response: Response,
    if_match: str | None = Header(default=None, alias="If-Match"),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    if user.role != "parent":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ROLE_FORBIDDEN")
    device = get_owned_device(db, device_id=device_id, owner_id=user.id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DEVICE_NOT_FOUND")

    expected_version = _parse_expected_version(if_match, payload.expected_version)
    try:
        key_id, private_key = load_signing_material()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="POLICY_SIGNING_UNAVAILABLE",
        ) from exc

    try:
        snapshot = create_policy_snapshot(
            db,
            device=device,
            created_by=user.id,
            expected_version=expected_version,
            policy=payload.policy,
            key_id=key_id,
            private_key=private_key,
        )
    except PolicyContractError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="POLICY_SCHEMA_INVALID",
        ) from exc
    except PolicyVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VERSION_CONFLICT",
                "current_version": exc.current_version,
            },
        ) from exc

    db.commit()
    response.headers["ETag"] = f'"{snapshot["policy_version"]}"'
    return snapshot


@router.get("/agent/policy", response_model=PolicySnapshotResponse)
def get_agent_policy(
    response: Response,
    version: int | None = Query(default=None, ge=0),
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db_session),
) -> dict[str, Any] | Response:
    current = get_current_policy(db, device_id=device.id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POLICY_NOT_FOUND")
    response.headers["ETag"] = f'"{current.version}"'
    if version == current.version:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": f'"{current.version}"'})
    return _read_snapshot(current)
