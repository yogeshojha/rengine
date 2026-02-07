"""Datetime utilities for consistent timezone handling across the application."""

from datetime import UTC, datetime


def normalize_datetime(dt: datetime | None) -> datetime | None:
    """
    Normalize datetime for database storage.

    Converts timezone-aware datetimes to UTC and strips timezone info.
    PostgreSQL TIMESTAMP WITHOUT TIME ZONE requires timezone-naive datetimes.

    Args:
        dt: DateTime to normalize (can be None)

    Returns:
        Timezone-naive datetime in UTC, or None if input is None

    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convert to UTC and remove tzinfo
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
