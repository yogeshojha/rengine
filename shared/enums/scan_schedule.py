from enum import Enum


class ScheduleType(Enum):
    ONE_OFF = "one_off"
    INTERVAL = "interval"
    DAILY_AT = "daily_at"
    CRON = "cron"


class IntervalUnit(Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class ScheduleStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


SCHEDULE_TYPES = tuple(t.value for t in ScheduleType)
INTERVAL_UNITS = tuple(u.value for u in IntervalUnit)
SCHEDULE_STATUSES = tuple(s.value for s in ScheduleStatus)
