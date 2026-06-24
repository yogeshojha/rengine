from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from shared.enums.scan_schedule import IntervalUnit, ScheduleStatus, ScheduleType
from shared.utils.datetime import utc_now

_INTERVAL = {
    IntervalUnit.MINUTES.value: lambda n: timedelta(minutes=n),
    IntervalUnit.HOURS.value: lambda n: timedelta(hours=n),
    IntervalUnit.DAYS.value: lambda n: timedelta(days=n),
    IntervalUnit.WEEKS.value: lambda n: timedelta(weeks=n),
}


def _zone(tz: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(tz or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _next_daily(daily_at_time: str, tz: ZoneInfo, now: datetime) -> datetime:
    hh, mm = (int(p) for p in daily_at_time.split(":", 1))
    local = now.astimezone(tz)
    candidate = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if candidate <= local:
        candidate = (local + timedelta(days=1)).replace(
            hour=hh, minute=mm, second=0, microsecond=0
        )
    return candidate.astimezone(UTC)


def _next_cron(expr: str, tz: ZoneInfo, now: datetime) -> datetime | None:
    from croniter import croniter  # noqa: PLC0415

    if not croniter.is_valid(expr):
        return None
    try:
        local = now.astimezone(tz)
        return croniter(expr, local).get_next(datetime).astimezone(UTC)
    except (ValueError, OverflowError, KeyError):
        return None


def compute_next_run_at(  # noqa: PLR0911
    sched, *, after: datetime | None = None
) -> datetime | None:
    now = after or utc_now()
    tz = _zone(getattr(sched, "timezone", "UTC"))

    if sched.schedule_type == ScheduleType.ONE_OFF.value:
        run_at = sched.run_at
        return run_at if run_at is not None and run_at > now else None

    if sched.schedule_type == ScheduleType.INTERVAL.value:
        delta = _INTERVAL.get(sched.interval_unit)
        if delta is None or not sched.interval_every:
            return None
        return now + delta(sched.interval_every)

    if sched.schedule_type == ScheduleType.DAILY_AT.value:
        if not sched.daily_at_time:
            return None
        return _next_daily(sched.daily_at_time, tz, now)

    if sched.schedule_type == ScheduleType.CRON.value:
        if not sched.cron_expression:
            return None
        return _next_cron(sched.cron_expression, tz, now)

    return None


def advance_schedule(sched, *, fired_at: datetime) -> None:
    """Mark a fired schedule: bump run count, then complete (one-off) or set next fire."""
    sched.last_run_at = fired_at
    sched.total_run_count += 1
    if sched.schedule_type == ScheduleType.ONE_OFF.value:
        sched.status = ScheduleStatus.COMPLETED.value
        sched.next_run_at = None
    else:
        sched.next_run_at = compute_next_run_at(sched, after=fired_at)


def describe_schedule(sched) -> str:
    t = sched.schedule_type
    if t == ScheduleType.ONE_OFF.value:
        return "Once"
    if t == ScheduleType.INTERVAL.value:
        n = sched.interval_every or 0
        unit = (sched.interval_unit or "").rstrip("s")
        return f"Every {n} {unit}{'s' if n != 1 else ''}".strip()
    if t == ScheduleType.DAILY_AT.value:
        return f"Daily at {sched.daily_at_time}"
    if t == ScheduleType.CRON.value:
        return f"Cron: {sched.cron_expression}"
    return t
