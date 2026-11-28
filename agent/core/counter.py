"""Measured usage counter with bounded monotonic deltas and SQLite checkpoints."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from agent.core.clock import Clock


@dataclass(frozen=True)
class Sample:
    child_session_active: bool
    unlocked: bool
    awake: bool
    idle_seconds: float
    telemetry_fresh: bool
    app_id: str | None = None

    @property
    def measured(self) -> bool:
        return self.child_session_active and self.unlocked and self.awake and self.telemetry_fresh and self.idle_seconds < 300


class UsageCounter:
    """Persist whole measured seconds; never infer usage across restart or sleep."""

    def __init__(self, database: Path, clock: Clock, timezone_name: str, *, max_sample_gap: float = 30) -> None:
        if max_sample_gap <= 0:
            raise ValueError("max_sample_gap must be positive")
        self.clock = clock
        self.zone = ZoneInfo(timezone_name)
        self.max_sample_gap = max_sample_gap
        self.connection = sqlite3.connect(database)
        self.connection.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT NOT NULL, app_id TEXT NOT NULL, seconds INTEGER NOT NULL, PRIMARY KEY(day, app_id))")
        self.connection.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.commit()
        stored = self.connection.execute("SELECT value FROM state WHERE key='wall_high_water'").fetchone()
        self._wall_high_water = datetime.fromisoformat(stored[0]) if stored else None
        self._previous_monotonic: float | None = None
        self._previous_wall: datetime | None = None
        self._previous_sample: Sample | None = None
        self._fraction = 0.0
        self.clock_rollback_detected = False
        self.degraded = False

    def observe(self, sample: Sample) -> int:
        mono = self.clock.monotonic()
        wall = self.clock.now_utc().astimezone(timezone.utc)
        behind_high_water = self._wall_high_water is not None and wall < self._wall_high_water
        if self._wall_high_water is None or wall > self._wall_high_water:
            self._wall_high_water = wall
            self.connection.execute("INSERT INTO state(key, value) VALUES ('wall_high_water', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (wall.isoformat(),))
            self.connection.commit()
        credited = 0
        if self._previous_monotonic is not None and self._previous_wall is not None:
            delta = mono - self._previous_monotonic
            wall_delta = (wall - self._previous_wall).total_seconds()
            self.clock_rollback_detected = behind_high_water or wall_delta < -1
            self.degraded = delta < 0 or delta > self.max_sample_gap or not sample.telemetry_fresh or behind_high_water
            if not behind_high_water and 0 <= delta <= self.max_sample_gap and self._previous_sample and self._previous_sample.measured and sample.measured:
                # Do not assign a crossing-midnight interval to either day.
                if wall_delta >= 0 and self._previous_wall.astimezone(self.zone).date() == wall.astimezone(self.zone).date():
                    seconds = delta + self._fraction
                    credited = int(seconds)
                    self._fraction = seconds - credited
                    if credited:
                        day = wall.astimezone(self.zone).date().isoformat()
                        apps = ("", sample.app_id) if sample.app_id else ("",)
                        for app in apps:
                            self.connection.execute("INSERT INTO usage(day, app_id, seconds) VALUES (?, ?, ?) ON CONFLICT(day, app_id) DO UPDATE SET seconds=seconds+excluded.seconds", (day, app, credited))
                        self.connection.commit()
                else:
                    self._fraction = 0.0
            else:
                self._fraction = 0.0
        self._previous_monotonic, self._previous_wall, self._previous_sample = mono, wall, sample
        return credited

    def seconds(self, day: str, app_id: str | None = None) -> int:
        row = self.connection.execute("SELECT seconds FROM usage WHERE day=? AND app_id=?", (day, app_id or "")).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self.connection.close()
