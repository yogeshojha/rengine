"""A scan is credited with a row only if it was the first to see it."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.dashboard_overview import DashboardOverviewService
from shared.definitions.surface import SurfaceDimension

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value


def _metric(overview, key: str):
    return next(m for m in overview.surface if m.key == key)


async def test_a_first_scan_contributes_nothing_new(estate, now):
    await estate.scan("example.com", "only", at=now)
    await estate.hosts("only", ["a.example.com", "b.example.com"], at=now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    web = _metric(out, WEB)
    assert web.value == 2
    assert web.new_in_window == 0, "no baseline, so nothing counts as new"


async def test_only_the_scan_that_first_saw_a_host_is_credited(estate, now):
    old = now - timedelta(days=3)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", ["a.example.com", "b.example.com"], at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts(
        "second", ["a.example.com", "b.example.com", "c.example.com"], at=now
    )

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    web = _metric(out, WEB)
    assert web.value == 3, "the newest covering scan holds three hosts"
    assert web.new_in_window == 1, "only c.example.com is new"


async def test_a_repeat_finding_is_never_counted_twice(estate, now):
    """Three scans, one unchanged host: the first sighting is credited once."""
    for days, name in ((10, "one"), (5, "two"), (0, "three")):
        await estate.scan("example.com", name, at=now - timedelta(days=days))
        await estate.hosts(name, ["a.example.com"], at=now - timedelta(days=days))

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "30d"
    )

    assert _metric(out, WEB).new_in_window == 0, (
        "the only scan that first saw it has no baseline of its own"
    )


async def test_newness_is_judged_per_target(estate, now):
    old = now - timedelta(days=3)
    await estate.scan("one.com", "one-first", at=old)
    await estate.hosts("one-first", ["a.one.com"], at=old)
    await estate.scan("one.com", "one-second", at=now)
    await estate.hosts("one-second", ["a.one.com", "b.one.com"], at=now)
    await estate.scan("two.com", "two-only", at=now)
    await estate.hosts("two-only", ["a.two.com", "b.two.com"], at=now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    web = _metric(out, WEB)
    assert web.value == 4
    assert web.targets_covered == 2
    assert web.new_in_window == 1, "two.com has no baseline and contributes nothing"
