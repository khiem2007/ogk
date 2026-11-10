"""Immutable core data structures shared by policy evaluation and contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class ReasonCode(str, Enum):
    ALLOWED = "ALLOWED"
    ALLOWED_BY_GRANT = "ALLOWED_BY_GRANT"
    MANUAL_LOCK = "MANUAL_LOCK"
    APP_BLOCKED = "APP_BLOCKED"
    DOMAIN_BLOCKED = "DOMAIN_BLOCKED"
    OUTSIDE_SCHEDULE = "OUTSIDE_SCHEDULE"
    DAILY_QUOTA_EXCEEDED = "DAILY_QUOTA_EXCEEDED"
    CATEGORY_QUOTA_EXCEEDED = "CATEGORY_QUOTA_EXCEEDED"
    UNMANAGED = "UNMANAGED"


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    reason_code: ReasonCode
    rule_id: str | None = None
    remaining_seconds: int | None = None
    next_transition_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.remaining_seconds is not None and self.remaining_seconds < 0:
            raise ValueError("remaining_seconds must be non-negative")
        if self.next_transition_at is not None:
            _require_aware(self.next_transition_at, "next_transition_at")


@dataclass(frozen=True, slots=True)
class ScheduleWindow:
    """A local-time interval active on ISO weekdays 1 (Monday) through 7."""

    rule_id: str
    weekdays: frozenset[int]
    start: time
    end: time

    def __post_init__(self) -> None:
        object.__setattr__(self, "weekdays", frozenset(self.weekdays))
        if not self.rule_id:
            raise ValueError("rule_id is required")
        if not self.weekdays or not self.weekdays <= frozenset(range(1, 8)):
            raise ValueError("weekdays must contain ISO weekday values 1..7")
        if self.start >= self.end:
            raise ValueError("schedule windows must not be empty or cross midnight")


@dataclass(frozen=True, slots=True)
class CategoryQuota:
    rule_id: str
    category_id: str
    limit_seconds: int

    def __post_init__(self) -> None:
        if not self.rule_id or not self.category_id:
            raise ValueError("rule_id and category_id are required")
        if self.limit_seconds < 0:
            raise ValueError("limit_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class AppRule:
    rule_id: str
    app_id: str
    executable: str
    blocked: bool = True
    category_id: str | None = None

    def __post_init__(self) -> None:
        if not self.rule_id or not self.app_id or not self.executable:
            raise ValueError("rule_id, app_id and executable are required")


@dataclass(frozen=True, slots=True)
class Grant:
    grant_id: str
    scope: str
    valid_from: datetime
    expires_at: datetime
    amount_seconds: int | None = None
    app_id: str | None = None
    local_date: str | None = None

    def __post_init__(self) -> None:
        if not self.grant_id or not self.scope:
            raise ValueError("grant_id and scope are required")
        _require_aware(self.valid_from, "valid_from")
        _require_aware(self.expires_at, "expires_at")
        if self.expires_at <= self.valid_from:
            raise ValueError("expires_at must be after valid_from")
        if self.amount_seconds is not None and self.amount_seconds <= 0:
            raise ValueError("amount_seconds must be positive")


@dataclass(frozen=True, slots=True)
class PolicySnapshot:
    version: int
    timezone_name: str
    schedules: tuple[ScheduleWindow, ...] = field(default_factory=tuple)
    daily_quota_seconds: int | None = None
    category_quotas: tuple[CategoryQuota, ...] = field(default_factory=tuple)
    app_rules: tuple[AppRule, ...] = field(default_factory=tuple)
    grants: tuple[Grant, ...] = field(default_factory=tuple)
    manual_lock: bool = False

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be at least 1")
        # Resolution belongs to the policy-evaluation boundary. Keeping this
        # contract independent of an optional host tzdata package makes it
        # portable to a clean Windows VM.
        if not self.timezone_name.strip():
            raise ValueError("timezone_name is required")
        if self.daily_quota_seconds is not None and self.daily_quota_seconds < 0:
            raise ValueError("daily_quota_seconds must be non-negative")
        object.__setattr__(self, "schedules", tuple(self.schedules))
        object.__setattr__(self, "category_quotas", tuple(self.category_quotas))
        object.__setattr__(self, "app_rules", tuple(self.app_rules))
        object.__setattr__(self, "grants", tuple(self.grants))
