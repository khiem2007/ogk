import base64
import json
from copy import deepcopy
from pathlib import Path

import pytest

from agent.core.policy_integrity import (
    PolicyIntegrityError,
    load_trusted_policy_keys,
    verify_policy_snapshot,
)


FIXTURE_PATH = Path("contracts/fixtures/policy.valid.json")
TEST_PUBLIC_KEY = base64.b64decode("A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=")


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fixture_signature_verifies_and_canonicalization_ignores_key_order() -> None:
    snapshot = load_fixture()
    reordered_snapshot = dict(reversed(list(snapshot.items())))

    assert verify_policy_snapshot(
        reordered_snapshot,
        {"test-fixture": TEST_PUBLIC_KEY},
        expected_device_id="a3e1f4d0-00f7-4e84-9dbe-13e9c77510a1",
        minimum_policy_version=3,
    ) == snapshot


def test_tampered_snapshot_is_rejected_without_changing_last_valid_snapshot() -> None:
    applied_snapshot = load_fixture()
    tampered_snapshot = deepcopy(applied_snapshot)
    tampered_snapshot["policy"]["manual_lock"] = True

    with pytest.raises(PolicyIntegrityError, match="POLICY_SIGNATURE_INVALID"):
        verify_policy_snapshot(
            tampered_snapshot,
            {"test-fixture": TEST_PUBLIC_KEY},
            expected_device_id="a3e1f4d0-00f7-4e84-9dbe-13e9c77510a1",
            minimum_policy_version=3,
        )

    assert applied_snapshot["policy"]["manual_lock"] is False


def test_invalid_schema_is_rejected_before_signature_verification() -> None:
    snapshot = load_fixture()
    snapshot["unexpected"] = True

    with pytest.raises(PolicyIntegrityError, match="POLICY_SCHEMA_INVALID"):
        verify_policy_snapshot(
            snapshot,
            {"test-fixture": TEST_PUBLIC_KEY},
            expected_device_id="a3e1f4d0-00f7-4e84-9dbe-13e9c77510a1",
            minimum_policy_version=3,
        )


def test_unknown_signing_key_is_rejected() -> None:
    with pytest.raises(PolicyIntegrityError, match="POLICY_SIGNING_KEY_UNTRUSTED"):
        verify_policy_snapshot(
            load_fixture(),
            {"other-key": TEST_PUBLIC_KEY},
            expected_device_id="a3e1f4d0-00f7-4e84-9dbe-13e9c77510a1",
            minimum_policy_version=3,
        )


def test_snapshot_for_another_device_is_rejected() -> None:
    with pytest.raises(PolicyIntegrityError, match="POLICY_DEVICE_MISMATCH"):
        verify_policy_snapshot(
            load_fixture(),
            {"test-fixture": TEST_PUBLIC_KEY},
            expected_device_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            minimum_policy_version=3,
        )


def test_older_snapshot_is_rejected() -> None:
    with pytest.raises(PolicyIntegrityError, match="POLICY_VERSION_ROLLBACK"):
        verify_policy_snapshot(
            load_fixture(),
            {"test-fixture": TEST_PUBLIC_KEY},
            expected_device_id="a3e1f4d0-00f7-4e84-9dbe-13e9c77510a1",
            minimum_policy_version=4,
        )


def test_trusted_key_map_is_loaded_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    encoded_public_key = base64.b64encode(TEST_PUBLIC_KEY).decode("ascii")
    monkeypatch.setenv("OGK_POLICY_VERIFY_PUBLIC_KEYS", json.dumps({"test-fixture": encoded_public_key}))

    assert load_trusted_policy_keys() == {"test-fixture": TEST_PUBLIC_KEY}


def test_trusted_key_configuration_fails_explicitly_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OGK_POLICY_VERIFY_PUBLIC_KEYS", raising=False)

    with pytest.raises(ValueError, match="OGK_POLICY_VERIFY_PUBLIC_KEYS"):
        load_trusted_policy_keys()
