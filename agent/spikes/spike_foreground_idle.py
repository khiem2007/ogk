"""Observe foreground process and session-local idle time on Windows.

This spike is read-only.  Its default mode takes one safe observation; use
``--samples`` to repeat.  No system setting is changed.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import os
import platform
import sys
import time
from typing import Any


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def load_dependencies() -> tuple[Any, Any, Any, Any]:
    if platform.system() != "Windows":
        raise RuntimeError("This spike must be run in the child's Windows session")
    try:
        import psutil
        import win32api
        import win32gui
        import win32process
        import win32ts
    except ImportError as exc:
        raise RuntimeError(
            "Install requirements-windows-spikes.txt with CPython on Windows"
        ) from exc
    return psutil, win32api, win32gui, win32process, win32ts


def idle_seconds(win32api: Any) -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        raise ctypes.WinError()
    # Both values are 32-bit tick counters; masking handles wraparound.
    elapsed_ms = (win32api.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return elapsed_ms / 1000.0


def observe() -> dict[str, object]:
    psutil, win32api, win32gui, win32process, win32ts = load_dependencies()
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("No foreground window is currently available")
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        process = psutil.Process(pid)
        process_name = process.name()
        executable = process.exe()
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        process_name = "UNAVAILABLE"
        executable = "UNAVAILABLE"
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "helper_pid": os.getpid(),
        "helper_session_id": win32ts.ProcessIdToSessionId(os.getpid()),
        "window_handle": int(hwnd),
        "foreground_pid": pid,
        "foreground_session_id": win32ts.ProcessIdToSessionId(pid),
        "process_name": process_name,
        "executable": executable,
        "idle_seconds": round(idle_seconds(win32api), 3),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=1, help="Number of observations")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Read-only observation (the default)",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Compatibility flag; this read-only spike never changes the system",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.samples < 1 or args.interval < 0:
        print("ERROR: samples must be >= 1 and interval must be >= 0", file=sys.stderr)
        return 2
    try:
        for index in range(args.samples):
            print(observe())
            if index + 1 < args.samples:
                time.sleep(args.interval)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
