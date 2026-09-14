from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.dashboard_activity import DashboardActivityService

pytestmark = pytest.mark.api


async def test_runs_land_on_the_rail_newest_first(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.scan(
        "example.com", "broken", at=now - timedelta(hours=1), status="failed"
    )
    await estate.scan("example.com", "fresh", at=now)
    await estate.hosts("fresh", ["a.example.com"], at=now)

    out = await DashboardActivityService(estate.session).activity(
        estate.project_id, "7d", programs=False
    )

    runs = [e for e in out.events if e.kind == "run"]
    assert [e.title for e in runs] == [
        "example.com run completed",
        "example.com run failed",
        "example.com run completed",
    ]
    assert runs[1].tone == "hot"
    assert runs[0].scan_id == estate.scans["fresh"]


async def test_the_window_cuts_the_rail(estate, now):
    await estate.scan("example.com", "old", at=now - timedelta(days=10))

    out = await DashboardActivityService(estate.session).activity(
        estate.project_id, "7d", programs=False
    )

    assert out.events == []
