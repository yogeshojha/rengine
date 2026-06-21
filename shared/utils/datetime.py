from datetime import UTC, datetime


def normalize_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
