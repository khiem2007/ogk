"""Deterministic local policy decisions; no host or Windows dependencies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from agent.core.models import Decision, PolicySnapshot, ReasonCode


def _active_grants(policy: PolicySnapshot, now: datetime):
    # Convert the current time to the policy's local date.
    local_date = now.astimezone(ZoneInfo(policy.timezone_name)).date().isoformat()
    return tuple(
        grant for grant in policy.grants
        if grant.valid_from <= now < grant.expires_at
        and (grant.local_date is None or grant.local_date == local_date)
    )


def _schedule(policy: PolicySnapshot, now: datetime) -> tuple[bool, datetime | None]:
    zone = ZoneInfo(policy.timezone_name)
    local = now.astimezone(zone)
    current = local.time().replace(tzinfo=None)
    active = any(
        local.isoweekday() in window.weekdays and window.start <= current < window.end
        for window in policy.schedules
    )
    transitions: list[datetime] = []
    for offset in range(8):
        day = local.date() + timedelta(days=offset)
        for window in policy.schedules:
            if day.isoweekday() not in window.weekdays:
                continue
            for edge in (window.start, window.end):
                instant = datetime.combine(day, edge, zone).astimezone(timezone.utc)
                if instant > now:
                    transitions.append(instant)
    return active, min(transitions, default=None)


def evaluate(
    policy: PolicySnapshot,
    *,
    now: datetime,
    daily_used_seconds: int,
    category_used_seconds: int = 0,
    app_id: str | None = None,
    category_id: str | None = None,
) -> Decision:
    """Apply lock, app, schedule, daily and category gates in that order."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if min(daily_used_seconds, category_used_seconds) < 0:
        raise ValueError("usage must be non-negative")

    now = now.astimezone(timezone.utc)
    grants = _active_grants(policy, now)
    scheduled, schedule_transition = _schedule(policy, now)
    local = now.astimezone(ZoneInfo(policy.timezone_name))
    midnight = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), local.tzinfo).astimezone(timezone.utc)
    time_exemption = any(g.scope in {"TIME_EXEMPTION", "EXEMPT_15_MINUTES", "EXEMPT_TODAY"} for g in grants)

    # The parent manually locks the device.
    if policy.manual_lock:
        return Decision(False, ReasonCode.MANUAL_LOCK, rule_id="manual-lock")

    # Block specific applications.
    for rule in policy.app_rules:
        if rule.blocked and app_id in {rule.app_id, rule.executable}:
            exception = any(g.scope == "APP_EXCEPTION" and g.app_id == rule.app_id for g in grants)
            if not exception:
                return Decision(False, ReasonCode.APP_BLOCKED, rule_id=rule.rule_id)

    # Block usage outside the allowed schedule.
    if policy.schedules and not scheduled and not time_exemption:
        return Decision(False, ReasonCode.OUTSIDE_SCHEDULE, next_transition_at=schedule_transition)

    # Enforce the daily usage limit.
    extra = sum(g.amount_seconds or 0 for g in grants if g.scope == "EXTRA_TIME")
    remaining = None if policy.daily_quota_seconds is None else max(0, policy.daily_quota_seconds + extra - daily_used_seconds)
    if remaining == 0 and not time_exemption:
        return Decision(False, ReasonCode.DAILY_QUOTA_EXCEEDED, rule_id="daily-quota", remaining_seconds=0, next_transition_at=midnight)

    # Enforce category limits, such as separate study and entertainment time.
    if category_id is not None:
        for quota in policy.category_quotas:
            if quota.category_id == category_id and category_used_seconds >= quota.limit_seconds and not time_exemption:
                return Decision(False, ReasonCode.CATEGORY_QUOTA_EXCEEDED, rule_id=quota.rule_id, remaining_seconds=0, next_transition_at=midnight)

    expiries = [g.expires_at for g in grants]
    next_transition = min((t for t in (schedule_transition, midnight, *expiries) if t and t > now), default=None)
    return Decision(True, ReasonCode.ALLOWED_BY_GRANT if grants else ReasonCode.ALLOWED, remaining_seconds=remaining, next_transition_at=next_transition)


def warning_level(remaining_seconds: int | None) -> int | None:
    """Return the active 10/5/1 minute warning threshold."""
    if remaining_seconds is None or remaining_seconds <= 0:
        return None
    return next((level for level in (60, 300, 600) if remaining_seconds <= level), None)
