from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_valid_timezone(tz: str) -> bool:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def normalize_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)
