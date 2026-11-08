from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.api.v1.whats_new import _check_range, _utc
from app.services.whats_new import WhatsNewService

pytestmark = pytest.mark.api

LAST = date.max - timedelta(days=1)


@pytest.mark.parametrize(
    ("day", "day_to"), [(date.max, None), (date(2026, 1, 1), date.max)]
)
def test_last_calendar_day_is_refused(day, day_to):
    with pytest.raises(HTTPException) as caught:
        _check_range(None, day, day_to)
    assert caught.value.status_code == 422


def test_day_before_the_last_passes():
    _check_range(None, LAST, LAST)


def test_naive_since_is_read_as_utc():
    since = _utc(datetime.fromisoformat("2026-11-01T00:00:00"))
    assert since == datetime(2026, 11, 1, tzinfo=UTC)
    _, cutoff, _, _ = WhatsNewService._period(
        datetime.now(UTC), None, since, None, None, None, UTC
    )
    assert min(cutoff, datetime.now(UTC)) == cutoff


def test_aware_since_is_kept():
    aware = datetime(2026, 11, 1, 5, tzinfo=UTC)
    assert _utc(aware) is aware
    assert _utc(None) is None
