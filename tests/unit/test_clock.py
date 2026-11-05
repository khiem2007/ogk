from datetime import datetime, timedelta, timezone

import pytest

from agent.core.clock import FakeClock, SystemClock


def test_fake_clock_starts_at_supplied_values() -> None:
    start = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    clock = FakeClock(start, monotonic_start=12.5)

    assert clock.now_utc() == start
    assert clock.monotonic() == 12.5


def test_advance_moves_wall_and_monotonic_clocks() -> None:
    start = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    clock = FakeClock(start)

    clock.advance(90.25)

    assert clock.now_utc() == start + timedelta(seconds=90.25)
    assert clock.monotonic() == pytest.approx(90.25)


def test_wall_clock_shift_does_not_change_monotonic_time() -> None:
    start = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    clock = FakeClock(start, monotonic_start=40)

    clock.shift_wall_clock(-600)

    assert clock.now_utc() == start - timedelta(minutes=10)
    assert clock.monotonic() == 40


@pytest.mark.parametrize("seconds", [-0.001, -1, -60])
def test_advance_rejects_negative_durations(seconds: float) -> None:
    clock = FakeClock(datetime(2026, 10, 30, tzinfo=timezone.utc))

    with pytest.raises(ValueError, match="non-negative"):
        clock.advance(seconds)


def test_fake_clock_requires_timezone_aware_start() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FakeClock(datetime(2026, 10, 30, 8, 0))


def test_system_clock_returns_aware_utc_and_non_decreasing_monotonic() -> None:
    clock = SystemClock()
    first = clock.monotonic()
    now = clock.now_utc()
    second = clock.monotonic()

    assert now.tzinfo is timezone.utc
    assert second >= first
