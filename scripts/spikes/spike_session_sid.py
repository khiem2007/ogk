"""Inspect Windows sessions/SIDs and safely exercise WTS disconnect fallback.

Read-only inspection runs by default.  Disconnecting a session requires all of
``--execute``, ``--session-id`` and ``--confirm-disconnect DISCONNECT-<id>``.
The destructive path also refuses to run unless this process is in Session 0.
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
from typing import Any


def require_windows_modules() -> tuple[Any, Any, Any, Any]:
    if platform.system() != "Windows":
        raise RuntimeError("This spike must be run on a Windows VM")
    try:
        import win32net
        import win32security
        import win32ts
        import pywintypes
    except ImportError as exc:
        raise RuntimeError(
            "Install requirements-windows-spikes.txt with CPython on Windows"
        ) from exc
    return win32ts, win32security, win32net, pywintypes


def query_text(win32ts: Any, session_id: int, info_class: int) -> str:
    try:
        value = win32ts.WTSQuerySessionInformation(
            win32ts.WTS_CURRENT_SERVER_HANDLE, session_id, info_class
        )
        return str(value or "").strip("\x00 ")
    except Exception:
        return ""


def account_sid(win32security: Any, domain: str, username: str) -> str | None:
    if not username:
        return None
    account = f"{domain}\\{username}" if domain else username
    try:
        sid, _, _ = win32security.LookupAccountName(None, account)
        return win32security.ConvertSidToStringSid(sid)
    except Exception:
        return None


def administrator_sids(win32security: Any, win32net: Any) -> set[str]:
    """Return direct members of the localized built-in Administrators group."""

    try:
        group_sid = win32security.ConvertStringSidToSid("S-1-5-32-544")
        group_name, _, _ = win32security.LookupAccountSid(None, group_sid)
        members, _, _ = win32net.NetLocalGroupGetMembers(None, group_name, 0)
        return {
            win32security.ConvertSidToStringSid(member["sid"])
            for member in members
        }
    except Exception:
        return set()


def state_names(win32ts: Any) -> dict[int, str]:
    names = (
        "WTSActive",
        "WTSConnected",
        "WTSConnectQuery",
        "WTSShadow",
        "WTSDisconnected",
        "WTSIdle",
        "WTSListen",
        "WTSReset",
        "WTSDown",
        "WTSInit",
    )
    return {
        getattr(win32ts, name): name.removeprefix("WTS").upper()
        for name in names
        if hasattr(win32ts, name)
    }


def label_session(
    session_id: int,
    username: str,
    is_admin: bool,
    parent_user: str | None,
    child_user: str | None,
) -> str:
    if session_id == 0:
        return "SESSION_0_SERVICE"
    normalized = username.casefold()
    if parent_user and normalized == parent_user.casefold():
        return "PARENT_ADMIN" if is_admin else "PARENT_NON_ADMIN"
    if child_user and normalized == child_user.casefold():
        return "CHILD_ADMIN_UNSAFE" if is_admin else "CHILD_STANDARD"
    return "ADMIN_USER" if is_admin else "STANDARD_USER"


def enumerate_sessions(
    win32ts: Any,
    win32security: Any,
    win32net: Any,
    parent_user: str | None,
    child_user: str | None,
) -> list[dict[str, object]]:
    admin_sids = administrator_sids(win32security, win32net)
    state_by_value = state_names(win32ts)
    active_console = win32ts.WTSGetActiveConsoleSessionId()
    rows: list[dict[str, object]] = []
    for raw_session in win32ts.WTSEnumerateSessions(
        win32ts.WTS_CURRENT_SERVER_HANDLE
    ):
        # pywin32 312 returns dictionaries.  Retain tuple support for older
        # builds used by some Windows lab images.
        if isinstance(raw_session, dict):
            session_id = int(raw_session["SessionId"])
            station = str(raw_session.get("WinStationName") or "")
            state = int(raw_session["State"])
        else:
            session_id, station, state = raw_session
        username = query_text(win32ts, session_id, win32ts.WTSUserName)
        domain = query_text(win32ts, session_id, win32ts.WTSDomainName)
        sid = account_sid(win32security, domain, username)
        is_admin = bool(sid and sid in admin_sids)
        rows.append(
            {
                "session_id": session_id,
                "station": station or "",
                "state": state_by_value.get(state, f"UNKNOWN({state})"),
                "domain": domain,
                "username": username,
                "sid": sid or "UNAVAILABLE",
                "account_type": "ADMIN" if is_admin else "STANDARD/UNKNOWN",
                "role": label_session(
                    session_id, username, is_admin, parent_user, child_user
                ),
                "active_console": session_id == active_console,
            }
        )
    return rows


def print_sessions(rows: list[dict[str, object]]) -> None:
    headers = (
        "ID",
        "Station",
        "State",
        "Account",
        "SID",
        "Type",
        "Role",
        "Console",
    )
    print(" | ".join(headers))
    print("-" * 150)
    for row in rows:
        account = "\\".join(
            item for item in (str(row["domain"]), str(row["username"])) if item
        )
        print(
            f"{row['session_id']} | {row['station']} | {row['state']} | "
            f"{account or '-'} | {row['sid']} | {row['account_type']} | "
            f"{row['role']} | {row['active_console']}"
        )


def disconnect_if_authorized(
    win32ts: Any,
    rows: list[dict[str, object]],
    session_id: int | None,
    execute: bool,
    confirmation: str | None,
) -> None:
    current_session = win32ts.ProcessIdToSessionId(os.getpid())
    print(f"\nCurrent process SessionId: {current_session}")
    if session_id is None:
        print("Dry-run: no disconnect target selected.")
        return

    target = next((row for row in rows if row["session_id"] == session_id), None)
    if target is None:
        raise RuntimeError(f"Session {session_id} was not found")
    if session_id == 0:
        raise RuntimeError("Session 0 must never be used as a disconnect target")
    print(
        "Disconnect plan: "
        f"SessionId={session_id}, user={target['username'] or '-'}, "
        f"state={target['state']}. Disconnect is not the same as lock."
    )
    if not execute:
        print("Dry-run only. Add --execute and the confirmation token to run it.")
        return
    if current_session != 0:
        raise RuntimeError(
            "Fallback test must run from Session 0 (for example a temporary VM service)"
        )
    expected = f"DISCONNECT-{session_id}"
    if confirmation != expected:
        raise RuntimeError(f"Refusing disconnect: pass --confirm-disconnect {expected}")
    win32ts.WTSDisconnectSession(
        win32ts.WTS_CURRENT_SERVER_HANDLE, session_id, False
    )
    print("Disconnect request submitted; enumerate sessions again to verify state.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-user", help="Expected parent/admin username")
    parser.add_argument("--child-user", help="Expected child/standard username")
    parser.add_argument("--session-id", type=int, help="Disconnect target for fallback test")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="List/evaluate only (the default); never disconnect",
    )
    mode.add_argument("--execute", action="store_true", help="Permit WTS disconnect")
    parser.add_argument("--confirm-disconnect", help="Required token: DISCONNECT-<id>")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        win32ts, win32security, win32net, _ = require_windows_modules()
        rows = enumerate_sessions(
            win32ts, win32security, win32net, args.parent_user, args.child_user
        )
        print_sessions(rows)
        disconnect_if_authorized(
            win32ts,
            rows,
            args.session_id,
            args.execute,
            args.confirm_disconnect,
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
