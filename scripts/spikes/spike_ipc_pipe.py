"""Exercise a bounded, replay-resistant Windows named-pipe exchange.

Dry-run is the default: it builds the intended DACL and validates sample data
without opening a pipe.  Use ``--execute --role server`` in an elevated/System
terminal and ``--execute --role client`` in the child's session for the live VM
test.  The DACL grants access only to LocalSystem and the selected child SID.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import json
import platform
import sys
import time
from typing import Any
from uuid import UUID, uuid4


DEFAULT_PIPE_NAME = r"\\.\pipe\OpenGuardKidsSpike"
MAX_PAYLOAD_BYTES = 4096
MAX_CLOCK_SKEW_SECONDS = 30.0


def load_dependencies() -> tuple[Any, Any, Any, Any, Any, Any]:
    if platform.system() != "Windows":
        raise RuntimeError("This spike must be run on a Windows VM")
    try:
        import ntsecuritycon
        import pywintypes
        import win32file
        import win32pipe
        import win32security
        import winerror
    except ImportError as exc:
        raise RuntimeError(
            "Install requirements-windows-spikes.txt with CPython on Windows"
        ) from exc
    return (
        ntsecuritycon,
        pywintypes,
        win32file,
        win32pipe,
        win32security,
        winerror,
    )


def lookup_sid(win32security: Any, account: str) -> tuple[Any, str]:
    sid, domain, _ = win32security.LookupAccountName(None, account)
    return sid, f"{domain}\\{account}" if domain and "\\" not in account else account


def build_security_attributes(
    ntsecuritycon: Any,
    pywintypes: Any,
    win32security: Any,
    child_account: str,
) -> tuple[Any, list[str]]:
    system_sid = win32security.ConvertStringSidToSid("S-1-5-18")
    child_sid, resolved_account = lookup_sid(win32security, child_account)
    dacl = win32security.ACL()
    access = ntsecuritycon.GENERIC_READ | ntsecuritycon.GENERIC_WRITE
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, access, system_sid)
    dacl.AddAccessAllowedAce(win32security.ACL_REVISION, access, child_sid)
    descriptor = win32security.SECURITY_DESCRIPTOR()
    descriptor.SetSecurityDescriptorDacl(True, dacl, False)
    attributes = pywintypes.SECURITY_ATTRIBUTES()
    attributes.SECURITY_DESCRIPTOR = descriptor
    summary = [
        "LocalSystem:S-1-5-18:READ_WRITE",
        f"{resolved_account}:{win32security.ConvertSidToStringSid(child_sid)}:READ_WRITE",
    ]
    return attributes, summary


def encode_message(message: dict[str, object]) -> bytes:
    payload = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"payload is {len(payload)} bytes; limit is {MAX_PAYLOAD_BYTES} bytes"
        )
    return payload


def validate_message(
    payload: bytes,
    seen_message_ids: set[str],
    *,
    now: float | None = None,
) -> dict[str, object]:
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload exceeds maximum size")
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("payload must be valid UTF-8 JSON") from exc
    if not isinstance(message, dict):
        raise ValueError("payload root must be a JSON object")
    if set(message) != {"message_id", "timestamp", "type", "payload"}:
        raise ValueError("payload fields must be message_id, timestamp, type and payload")
    try:
        message_id = str(UUID(str(message["message_id"])))
    except (ValueError, AttributeError) as exc:
        raise ValueError("message_id must be a UUID") from exc
    if message_id in seen_message_ids:
        raise ValueError("replayed message_id")
    if not isinstance(message["timestamp"], (int, float)):
        raise ValueError("timestamp must be Unix seconds")
    current = time.time() if now is None else now
    skew = abs(current - float(message["timestamp"]))
    if skew > MAX_CLOCK_SKEW_SECONDS:
        raise ValueError(
            f"timestamp skew is {skew:.3f}s; limit is {MAX_CLOCK_SKEW_SECONDS:.0f}s"
        )
    if message["type"] not in {"session_signal", "status_request", "notification_ack"}:
        raise ValueError("message type is not allowlisted")
    if not isinstance(message["payload"], dict):
        raise ValueError("payload field must be an object")
    seen_message_ids.add(message_id)
    return message


def sample_message() -> dict[str, object]:
    return {
        "message_id": str(uuid4()),
        "timestamp": time.time(),
        "type": "session_signal",
        "payload": {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "session_state": "ACTIVE",
            "idle_seconds": 0,
        },
    }


def dry_run(child_account: str) -> int:
    ntsecuritycon, pywintypes, _, _, win32security, _ = load_dependencies()
    _, summary = build_security_attributes(
        ntsecuritycon, pywintypes, win32security, child_account
    )
    print("Dry-run DACL:")
    for entry in summary:
        print(f"  {entry}")
    payload = encode_message(sample_message())
    seen: set[str] = set()
    validate_message(payload, seen)
    print(f"Sample accepted ({len(payload)} bytes).")
    try:
        validate_message(payload, seen)
    except ValueError as exc:
        print(f"Replay correctly rejected: {exc}")
    else:
        raise AssertionError("replayed message was unexpectedly accepted")
    oversized = sample_message()
    oversized["payload"] = {"data": "x" * MAX_PAYLOAD_BYTES}
    try:
        encode_message(oversized)
    except ValueError as exc:
        print(f"Oversized payload correctly rejected: {exc}")
    else:
        raise AssertionError("oversized payload was unexpectedly accepted")
    stale = sample_message()
    stale["timestamp"] = time.time() - MAX_CLOCK_SKEW_SECONDS - 1
    try:
        validate_message(encode_message(stale), seen)
    except ValueError as exc:
        print(f"Stale timestamp correctly rejected: {exc}")
    else:
        raise AssertionError("stale timestamp was unexpectedly accepted")
    return 0


def run_server(pipe_name: str, child_account: str) -> int:
    (
        ntsecuritycon,
        pywintypes,
        win32file,
        win32pipe,
        win32security,
        winerror,
    ) = load_dependencies()
    attributes, summary = build_security_attributes(
        ntsecuritycon, pywintypes, win32security, child_account
    )
    print("Opening one-client named pipe with DACL:")
    for entry in summary:
        print(f"  {entry}")
    pipe = win32pipe.CreateNamedPipe(
        pipe_name,
        win32pipe.PIPE_ACCESS_DUPLEX,
        win32pipe.PIPE_TYPE_MESSAGE
        | win32pipe.PIPE_READMODE_MESSAGE
        | win32pipe.PIPE_WAIT
        | getattr(win32pipe, "PIPE_REJECT_REMOTE_CLIENTS", 0),
        1,
        MAX_PAYLOAD_BYTES,
        MAX_PAYLOAD_BYTES,
        5000,
        attributes,
    )
    seen: set[str] = set()
    try:
        print(f"Waiting for child client on {pipe_name} ...")
        try:
            win32pipe.ConnectNamedPipe(pipe, None)
        except pywintypes.error as exc:
            if exc.winerror != winerror.ERROR_PIPE_CONNECTED:
                raise
        _, payload = win32file.ReadFile(pipe, MAX_PAYLOAD_BYTES + 1)
        try:
            message = validate_message(payload, seen)
            response = {"ok": True, "message_id": message["message_id"]}
        except ValueError as exc:
            response = {"ok": False, "error": str(exc)}
        win32file.WriteFile(pipe, encode_message(response))
        print(response)
        return 0 if response["ok"] else 1
    finally:
        try:
            win32pipe.DisconnectNamedPipe(pipe)
        except Exception:
            pass
        win32file.CloseHandle(pipe)


def run_client(pipe_name: str) -> int:
    ntsecuritycon, _, win32file, win32pipe, _, _ = load_dependencies()
    win32pipe.WaitNamedPipe(pipe_name, 5000)
    handle = win32file.CreateFile(
        pipe_name,
        ntsecuritycon.GENERIC_READ | ntsecuritycon.GENERIC_WRITE,
        0,
        None,
        win32file.OPEN_EXISTING,
        0,
        None,
    )
    try:
        win32pipe.SetNamedPipeHandleState(
            handle, win32pipe.PIPE_READMODE_MESSAGE, None, None
        )
        win32file.WriteFile(handle, encode_message(sample_message()))
        _, response = win32file.ReadFile(handle, MAX_PAYLOAD_BYTES)
        print(json.loads(response.decode("utf-8")))
        return 0
    finally:
        win32file.CloseHandle(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child-account", default=getpass.getuser())
    parser.add_argument("--pipe-name", default=DEFAULT_PIPE_NAME)
    parser.add_argument("--role", choices=("server", "client"), default="server")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate DACL/payload/replay logic only (the default)",
    )
    mode.add_argument("--execute", action="store_true", help="Open/connect to the pipe")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not args.execute:
            return dry_run(args.child_account)
        if args.role == "server":
            return run_server(args.pipe_name, args.child_account)
        return run_client(args.pipe_name)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
