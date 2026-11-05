"""Pure, platform-independent agent domain model."""

from .clock import Clock, FakeClock, SystemClock
from .models import (
    AppRule,
    CategoryQuota,
    Decision,
    Grant,
    PolicySnapshot,
    ReasonCode,
    ScheduleWindow,
)

__all__ = [
    "AppRule",
    "CategoryQuota",
    "Clock",
    "Decision",
    "FakeClock",
    "Grant",
    "PolicySnapshot",
    "ReasonCode",
    "ScheduleWindow",
    "SystemClock",
]
