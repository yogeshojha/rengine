from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.services import software
from app.services.software import SoftwareService
from shared.definitions.threat_intel import STALE_AFTER_HOURS, FeedKind
from shared.models.software import SoftwareCoverage
from shared.models.threat_intel import ThreatFeed

pytestmark = pytest.mark.api


async def test_feed_age_is_read_when_coverage_is_served_from_the_cache(
    session, monkeypatch, now
):
    hours = STALE_AFTER_HOURS + 6
    await session.merge(
        ThreatFeed(
            kind=FeedKind.NVD.value,
            rows=10,
            last_synced_at=now - timedelta(hours=hours),
        )
    )
    await session.flush()
    stored = SoftwareCoverage(
        components=4, mapped=3, unmapped=1, feed_ready=False, feed_age_hours=1.0
    )

    async def cached(*_args, **_kwargs):
        return stored

    monkeypatch.setattr(software.lead_cache, "cached", cached)
    result = await SoftwareService(session).coverage((uuid.uuid4(),))

    assert result.components == 4
    assert result.feed_ready is True
    assert result.feed_age_hours == pytest.approx(hours, abs=0.1)
    assert result.stale is True
    assert stored.feed_age_hours == 1.0
