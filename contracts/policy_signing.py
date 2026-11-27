"""Shared canonicalization, schema validation, and Ed25519 policy signing."""

from __future__ import annotations

import base64
import binascii
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


_SCHEMA_DIRECTORY = Path(__file__).parent / "schemas"
_COMMON_SCHEMA_ID = "https://ogk.example/contracts/v1/common.schema.json"
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class PolicyContractError(ValueError):
    """A policy snapshot does not match the shared contract."""


class PolicyIntegrityError(ValueError):
    """A policy snapshot cannot be trusted or its signature is invalid."""


@lru_cache(maxsize=1)
def _policy_validator() -> Draft202012Validator:
    policy_schema = json.loads((_SCHEMA_DIRECTORY / "policy.schema.json").read_text(encoding="utf-8"))
    common_schema = json.loads((_SCHEMA_DIRECTORY / "common.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(
        _COMMON_SCHEMA_ID,
        Resource.from_contents(common_schema),
    )
    return Draft202012Validator(
        policy_schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def validate_policy_snapshot(snapshot: Mapping[str, Any]) -> None:
    errors = sorted(
        _policy_validator().iter_errors(snapshot),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        raise PolicyContractError(errors[0].message)


def _validate_key_id(key_id: str) -> None:
    if not _KEY_ID_PATTERN.fullmatch(key_id):
        raise ValueError("policy signing key ID must use 1-64 letters, digits, '.', '_' or '-'")


def validate_policy_key_id(key_id: str) -> None:
    _validate_key_id(key_id)


def canonical_policy_message(snapshot: Mapping[str, Any], key_id: str) -> bytes:
    _validate_key_id(key_id)
    if "signature" in snapshot:
        raise ValueError("canonical snapshot must not include a signature")
    signed_value = {
        "algorithm": "Ed25519",
        "key_id": key_id,
        "snapshot": snapshot,
    }
    return json.dumps(
        signed_value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sign_policy_snapshot(
    snapshot: Mapping[str, Any],
    *,
    key_id: str,
    private_key: bytes,
) -> dict[str, Any]:
    try:
        signer = Ed25519PrivateKey.from_private_bytes(private_key)
    except ValueError as exc:
        raise ValueError("policy signing private key must be a 32-byte Ed25519 key") from exc

    signature = signer.sign(canonical_policy_message(snapshot, key_id))
    signed_snapshot = dict(snapshot)
    signed_snapshot["signature"] = {
        "algorithm": "Ed25519",
        "key_id": key_id,
        "value": base64.b64encode(signature).decode("ascii"),
    }
    validate_policy_snapshot(signed_snapshot)
    return signed_snapshot


def decode_private_key(encoded_key: str) -> bytes:
    try:
        private_key = base64.b64decode(encoded_key, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("policy signing private key must be base64-encoded") from exc
    if len(private_key) != 32:
        raise ValueError("policy signing private key must decode to 32 bytes")
    return private_key


def decode_public_keys(encoded_keys: str) -> dict[str, bytes]:
    try:
        values = json.loads(encoded_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("policy verification keys must be a JSON object") from exc
    if not isinstance(values, dict) or not values:
        raise ValueError("policy verification keys must be a non-empty JSON object")

    keys: dict[str, bytes] = {}
    for key_id, encoded_key in values.items():
        if not isinstance(key_id, str):
            raise ValueError("policy verification key IDs must be strings")
        _validate_key_id(key_id)
        if not isinstance(encoded_key, str):
            raise ValueError(f"policy verification key {key_id!r} must be a base64 string")
        try:
            public_key = base64.b64decode(encoded_key, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"policy verification key {key_id!r} must be base64-encoded") from exc
        if len(public_key) != 32:
            raise ValueError(f"policy verification key {key_id!r} must decode to 32 bytes")
        keys[key_id] = public_key
    return keys


def verify_policy_snapshot(
    snapshot: Mapping[str, Any],
    *,
    trusted_public_keys: Mapping[str, bytes],
    expected_device_id: str,
    minimum_policy_version: int,
) -> dict[str, Any]:
    try:
        validate_policy_snapshot(snapshot)
    except PolicyContractError as exc:
        raise PolicyIntegrityError("POLICY_SCHEMA_INVALID") from exc

    signature = snapshot["signature"]
    if snapshot["device_id"] != expected_device_id:
        raise PolicyIntegrityError("POLICY_DEVICE_MISMATCH")
    if minimum_policy_version < 0:
        raise ValueError("minimum policy version must be non-negative")
    if snapshot["policy_version"] < minimum_policy_version:
        raise PolicyIntegrityError("POLICY_VERSION_ROLLBACK")
    key_id = signature["key_id"]
    public_key_bytes = trusted_public_keys.get(key_id)
    if public_key_bytes is None:
        raise PolicyIntegrityError("POLICY_SIGNING_KEY_UNTRUSTED")
    try:
        verifier = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        signature_bytes = base64.b64decode(signature["value"], validate=True)
        verifier.verify(
            signature_bytes,
            canonical_policy_message(
                {key: value for key, value in snapshot.items() if key != "signature"},
                key_id,
            ),
        )
    except (InvalidSignature, binascii.Error, TypeError, ValueError) as exc:
        raise PolicyIntegrityError("POLICY_SIGNATURE_INVALID") from exc
    return dict(snapshot)
