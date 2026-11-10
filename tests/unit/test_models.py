from dataclasses import FrozenInstanceError
from datetime import datetime, time, timezone

import pytest

from agent.core.models import (
    AppRule,
    CategoryQuota,
    Decision,
    Grant,
    PolicySnapshot,
    ReasonCode,
    ScheduleWindow,
)


def test_reason_codes_match_shared_contract() -> None:
    assert [item.value for item in ReasonCode] == [
        "ALLOWED",
        "ALLOWED_BY_GRANT",
        "MANUAL_LOCK",
        "APP_BLOCKED",
        "DOMAIN_BLOCKED",
        "OUTSIDE_SCHEDULE",
        "DAILY_QUOTA_EXCEEDED",
        "CATEGORY_QUOTA_EXCEEDED",
        "UNMANAGED",
    ]


def test_decision_can_be_created_with_contract_fields() -> None:
    transition = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    decision = Decision(
        allowed=False,
        reason_code=ReasonCode.DAILY_QUOTA_EXCEEDED,
        rule_id="daily-quota",
        remaining_seconds=0,
        next_transition_at=transition,
    )

    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.DAILY_QUOTA_EXCEEDED
    assert decision.rule_id == "daily-quota"
    assert decision.remaining_seconds == 0
    assert decision.next_transition_at == transition


def test_decision_is_immutable() -> None:
    decision = Decision(True, ReasonCode.ALLOWED)

    with pytest.raises(FrozenInstanceError):
        decision.allowed = False  # type: ignore[misc]


def test_decision_rejects_naive_transition_and_negative_remaining() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Decision(True, ReasonCode.ALLOWED, next_transition_at=datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="non-negative"):
        Decision(False, ReasonCode.DAILY_QUOTA_EXCEEDED, remaining_seconds=-1)


def test_policy_snapshot_freezes_nested_collections() -> None:
    schedules = [
        ScheduleWindow(
            rule_id="school-night",
            weekdays=frozenset({1, 2, 3, 4, 5}),
            start=time(7, 0),
            end=time(21, 0),
        )
    ]
    quota = CategoryQuota("games-quota", "games", 3600)
    app_rule = AppRule("block-game", "game.exe", "game.exe")
    grant = Grant(
        grant_id="grant-1",
        scope="EXTRA_TIME",
        valid_from=datetime(2026, 11, 1, 10, tzinfo=timezone.utc),
        expires_at=datetime(2026, 11, 1, 11, tzinfo=timezone.utc),
        amount_seconds=900,
    )

    snapshot = PolicySnapshot(
        version=1,
        timezone_name="Asia/Ho_Chi_Minh",
        schedules=schedules,  # type: ignore[arg-type]
        daily_quota_seconds=7200,
        category_quotas=[quota],  # type: ignore[arg-type]
        app_rules=[app_rule],  # type: ignore[arg-type]
        grants=[grant],  # type: ignore[arg-type]
    )
    schedules.append(
        ScheduleWindow("weekend", frozenset({6, 7}), time(8), time(22))
    )

    assert isinstance(snapshot.schedules, tuple)
    assert len(snapshot.schedules) == 1
    assert snapshot.category_quotas == (quota,)
    assert snapshot.app_rules == (app_rule,)
    assert snapshot.grants == (grant,)
    with pytest.raises(FrozenInstanceError):
        snapshot.version = 2  # type: ignore[misc]


def test_schedule_window_rejects_cross_midnight_for_mvp() -> None:
    with pytest.raises(ValueError, match="cross midnight"):
        ScheduleWindow("overnight", frozenset({1}), time(22), time(7))


def test_policy_snapshot_requires_timezone_name() -> None:
    with pytest.raises(ValueError, match="timezone_name is required"):
        PolicySnapshot(version=1, timezone_name="  ")
