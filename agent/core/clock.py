"""Clock abstractions for deterministic policy and counter tests.

This module is deliberately free of Windows imports.  Wall-clock time is used
for schedules and expiry, while monotonic time is used only for elapsed-time
measurement within a running process.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from threading import RLock
import time


class Clock(ABC):
    """Source of UTC wall-clock time and monotonic elapsed time."""

    @abstractmethod
    def now_utc(self) -> datetime:
        """Return a timezone-aware current time in UTC."""

    @abstractmethod
    def monotonic(self) -> float:
        """Return a non-decreasing process-local time in seconds."""


class SystemClock(Clock):
    """Production clock backed by Python's system clocks."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock(Clock):
    """Deterministic clock whose two time sources advance together by default."""

    def __init__(
        self,
        start_utc: datetime,
        *,
        monotonic_start: float = 0.0,
    ) -> None:
        if start_utc.tzinfo is None or start_utc.utcoffset() is None:
            raise ValueError("start_utc must be timezone-aware")
        if monotonic_start < 0:
            raise ValueError("monotonic_start must be non-negative")

        self._now_utc = start_utc.astimezone(timezone.utc)
        self._monotonic = float(monotonic_start)
        self._lock = RLock()

    def now_utc(self) -> datetime:
        # Serialize access so readers cannot observe a partially updated clock.
        with self._lock:
            return self._now_utc

    def monotonic(self) -> float:
        with self._lock:
            return self._monotonic

    def advance(self, seconds: float) -> None:
        """Advance wall-clock and monotonic time by a non-negative duration."""

        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        with self._lock:
            self._now_utc += timedelta(seconds=seconds)
            self._monotonic += float(seconds)

    def shift_wall_clock(self, seconds: float) -> None:
        """Move only wall-clock time to simulate a system clock correction."""

        with self._lock:
            self._now_utc += timedelta(seconds=seconds)
