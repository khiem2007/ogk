from datetime import datetime, timezone

from agent.core.clock import FakeClock
from agent.core.counter import Sample, UsageCounter


ACTIVE = Sample(True, True, True, 0, True, "game")
LOCKED = Sample(True, False, True, 0, True, "game")


def test_counter_persists_only_measured_usage(tmp_path):
    clock = FakeClock(datetime(2026, 11, 2, 10, tzinfo=timezone.utc))
    path = tmp_path / "usage.db"
    counter = UsageCounter(path, clock, "UTC", max_sample_gap=100)
    counter.observe(ACTIVE)
    clock.advance(90)
    assert counter.observe(ACTIVE) == 90
    counter.observe(LOCKED)
    clock.advance(30)
    assert counter.observe(LOCKED) == 0
    assert counter.seconds("2026-11-02") == 90
    assert counter.seconds("2026-11-02", "game") == 90
    counter.close()
    restarted = UsageCounter(path, clock, "UTC")
    assert restarted.seconds("2026-11-02") == 90
    restarted.observe(ACTIVE)
    assert restarted.seconds("2026-11-02") == 90
    restarted.close()


def test_rollback_and_sleep_gap_are_not_credited(tmp_path):
    clock = FakeClock(datetime(2026, 11, 2, 10, tzinfo=timezone.utc))
    counter = UsageCounter(tmp_path / "usage.db", clock, "UTC")
    counter.observe(ACTIVE)
    clock.advance(10)
    counter.observe(ACTIVE)
    clock.shift_wall_clock(-3 * 3600)
    clock.advance(1)
    assert counter.observe(ACTIVE) == 0
    assert counter.clock_rollback_detected
    clock.advance(3600)
    assert counter.observe(ACTIVE) == 0
    assert counter.degraded
    assert counter.seconds("2026-11-02") == 10
    counter.close()
