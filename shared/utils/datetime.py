from datetime import UTC, datetime

_SIXTY = 60


def normalize_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)


def duration_text(seconds: float) -> str:
    """`45s`, `2m 5s` or `1h 5m`, as the frontend's formatSeconds spells it."""
    total = round(seconds)
    if total < _SIXTY:
        return f"{total}s"
    minutes, secs = divmod(total, _SIXTY)
    if minutes < _SIXTY:
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    hours, rest = divmod(minutes, _SIXTY)
    return f"{hours}h {rest}m" if rest else f"{hours}h"
