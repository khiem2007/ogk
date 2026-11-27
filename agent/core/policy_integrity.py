"""Agent-side policy verification boundary."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from contracts.policy_signing import (
    PolicyIntegrityError,
    decode_public_keys,
    verify_policy_snapshot as _verify_policy_snapshot,
)


def load_trusted_policy_keys() -> dict[str, bytes]:
    encoded_keys = os.getenv("OGK_POLICY_VERIFY_PUBLIC_KEYS", "")
    if not encoded_keys:
        raise ValueError("OGK_POLICY_VERIFY_PUBLIC_KEYS must be configured")
    return decode_public_keys(encoded_keys)


def verify_policy_snapshot(
    snapshot: Mapping[str, Any],
    trusted_public_keys: Mapping[str, bytes] | None = None,
    *,
    expected_device_id: str,
    minimum_policy_version: int,
) -> dict[str, Any]:
    """Validate and authenticate a snapshot before the caller applies it."""
    keys = trusted_public_keys if trusted_public_keys is not None else load_trusted_policy_keys()
    return _verify_policy_snapshot(
        snapshot,
        trusted_public_keys=keys,
        expected_device_id=expected_device_id,
        minimum_policy_version=minimum_policy_version,
    )


__all__ = ["PolicyIntegrityError", "load_trusted_policy_keys", "verify_policy_snapshot"]
