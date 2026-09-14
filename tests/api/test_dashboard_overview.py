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


def _step(overview, key: str):
    return next(s for s in overview.funnel.steps if s.key == key)


async def test_funnel_counts_names_resolved_live_and_faulted(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["dead.example.com"], at=now)
    await estate.hosts("run", ["idle.example.com"], at=now, ips=["10.0.0.1"])
    await estate.hosts("run", ["www.example.com"], at=now, ips=["10.0.0.2"], status=200)
    await estate.vulns("run", [("xss", "high")], at=now, host="www.example.com")

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    assert _step(out, "names").count == 3
    assert _step(out, "resolved").count == 2
    assert _step(out, "live").count == 1
    assert _step(out, "findings").count == 1
    assert _step(out, "names").new_in_window == 0


async def test_retired_counts_what_the_previous_run_held(estate, now):
    old = now - timedelta(days=2)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", ["a.example.com", "b.example.com"], at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", ["a.example.com"], at=now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    today = next(d for d in out.daily if d.date == now.date().isoformat())
    assert today.retired[WEB] == 1, "b.example.com left between the runs"
    earlier = next(d for d in out.daily if d.date == old.date().isoformat())
    assert earlier.retired[WEB] == 0


async def test_a_cancelled_run_retires_nothing(estate, now):
    old = now - timedelta(days=2)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", ["a.example.com", "b.example.com"], at=old)
    await estate.scan("example.com", "second", at=now, status="cancelled")
    await estate.hosts("second", ["a.example.com"], at=now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    today = next(d for d in out.daily if d.date == now.date().isoformat())
    assert today.retired[WEB] == 0
    assert today.outcomes == {"cancelled": 1}


async def test_queue_tiers_follow_exploitation_then_severity(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.vulns("run", [("kev-low", "low")], at=now, kev=True)
    await estate.vulns("run", [("plain-high", "high"), ("plain-low", "low")], at=now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    assert out.risk.tiers == {"act": 1, "attend": 1, "track": 1}
    tiers = {f.template_id: f.tier for f in out.risk.queue}
    assert tiers == {"kev-low": "act", "plain-high": "attend", "plain-low": "track"}
    cells = {(c.severity, c.evidence): c.count for c in out.risk.evidence}
    assert cells == {("high", "observed"): 1, ("low", "observed"): 2}


async def test_findings_per_day_split_by_severity_need_a_baseline(estate, now):
    old = now - timedelta(days=3)
    await estate.scan("example.com", "first", at=old)
    await estate.vulns("first", [("a", "high")], at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.vulns("second", [("a", "high"), ("b", "critical")], at=now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    today = next(d for d in out.daily if d.date == now.date().isoformat())
    assert today.findings["critical"] == 1
    assert today.findings["high"] == 0, "a was reported by the first run"
    earlier = next(d for d in out.daily if d.date == old.date().isoformat())
    assert sum(earlier.findings.values()) == 0, "a first run has no baseline"
