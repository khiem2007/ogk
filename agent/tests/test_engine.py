from datetime import datetime, time, timedelta, timezone

from agent.core.engine import evaluate, warning_level
from agent.core.models import AppRule, CategoryQuota, Grant, PolicySnapshot, ReasonCode, ScheduleWindow


NOW = datetime(2026, 11, 2, 10, tzinfo=timezone.utc)  # Monday


def policy(**changes):
    fields = dict(version=1, timezone_name="UTC", schedules=(ScheduleWindow("day", frozenset({1}), time(9), time(11)),), daily_quota_seconds=180)
    fields.update(changes)
    return PolicySnapshot(**fields)


def test_precedence_and_half_open_schedule():
    p = policy(manual_lock=True, app_rules=(AppRule("block", "game", "game.exe"),))
    assert evaluate(p, now=NOW, daily_used_seconds=180, app_id="game").reason_code is ReasonCode.MANUAL_LOCK
    p = policy(app_rules=p.app_rules)
    assert evaluate(p, now=NOW, daily_used_seconds=180, app_id="game").reason_code is ReasonCode.APP_BLOCKED
    assert evaluate(p, now=NOW.replace(hour=11), daily_used_seconds=0).reason_code is ReasonCode.OUTSIDE_SCHEDULE
    assert evaluate(p, now=NOW.replace(hour=9), daily_used_seconds=0).allowed


def test_quota_grants_and_category_gate():
    grant = Grant("extra", "EXTRA_TIME", NOW - timedelta(minutes=1), NOW + timedelta(minutes=5), 60)
    p = policy(grants=(grant,), category_quotas=(CategoryQuota("games", "games", 30),))
    assert evaluate(p, now=NOW, daily_used_seconds=180, category_id="games", category_used_seconds=30).reason_code is ReasonCode.CATEGORY_QUOTA_EXCEEDED
    allowed = evaluate(p, now=NOW, daily_used_seconds=180, category_id="games", category_used_seconds=29)
    assert allowed.allowed and allowed.remaining_seconds == 60
    assert evaluate(p, now=NOW + timedelta(minutes=5), daily_used_seconds=180).reason_code is ReasonCode.DAILY_QUOTA_EXCEEDED
    assert [warning_level(n) for n in (601, 600, 301, 300, 61, 60, 0)] == [None, 600, 600, 300, 300, 60, None]


def test_app_exception_does_not_bypass_quota():
    grant = Grant("exception", "APP_EXCEPTION", NOW - timedelta(seconds=1), NOW + timedelta(seconds=30), app_id="game")
    p = policy(app_rules=(AppRule("block", "game", "game.exe"),), grants=(grant,))
    assert evaluate(p, now=NOW, daily_used_seconds=180, app_id="game").reason_code is ReasonCode.DAILY_QUOTA_EXCEEDED
    assert evaluate(p, now=NOW, daily_used_seconds=0, app_id="game").reason_code is ReasonCode.ALLOWED_BY_GRANT
