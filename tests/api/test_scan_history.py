from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.services.scan import ScanService
from app.services.vulnerability import VulnerabilityService
from shared.models.scan import Scan
from shared.models.vulnerability import VulnerabilityCoverage, VulnerabilityTriage

pytestmark = pytest.mark.api

RAN_VULNS = {"vulnerability_scan": "success"}


async def _ids(service: ScanService, **filters) -> list:
    query = service.build_list_query(**filters)
    return list((await service.session.execute(query)).scalars())


async def test_row_counts_match_the_vulnerability_page(estate, now):
    sid = await estate.scan("example.com", "run", at=now)
    await estate.activity("run", RAN_VULNS)
    await estate.vulns(
        "run",
        [
            ("rce", "critical"),
            ("sqli", "high"),
            ("redirect", "medium"),
            ("hsts", "low"),
            ("banner", "info"),
        ],
        at=now,
    )
    estate.session.add(
        VulnerabilityTriage(
            project_id=estate.project_id,
            target_id=estate.targets["example.com"],
            fingerprint="sqli",
            template_id="sqli",
            matched_at="https://www.example.com/",
            state="false_positive",
        )
    )
    await estate.session.flush()

    counts = (await ScanService(estate.session).finding_counts([sid]))[sid]
    page = await VulnerabilityService(estate.session).overview(sid)
    by_page = {s.severity: s.count for s in page.by_severity}

    assert (counts.critical, counts.high, counts.medium) == (1, 0, 1)
    assert counts.critical == by_page.get("critical", 0)
    assert counts.high == by_page.get("high", 0)
    assert counts.medium == by_page.get("medium", 0)
    assert counts.covered is True


async def test_overview_counts_checks_run_and_each_dropped_target_once(estate, now):
    sid = await estate.scan("example.com", "run", at=now)
    tid = estate.targets["example.com"]

    def row(tier, *, selected, loaded, dropped, status="partial"):
        return VulnerabilityCoverage(
            scan_id=sid,
            target_id=tid,
            project_id=estate.project_id,
            group="Standard rate",
            tier=tier,
            status=status,
            templates_selected=selected,
            templates_loaded=loaded,
            hosts_total=2,
            hosts_dropped=[{"host": h, "reason": "no route"} for h in dropped],
        )

    estate.session.add_all(
        [
            row("one_request", selected=20, loaded=20, dropped=["a:443", "b:80"]),
            row("blind", selected=300, loaded=298, dropped=["a:443"]),
            row(None, selected=900, loaded=None, dropped=[], status="skipped"),
        ]
    )
    await estate.session.flush()

    out = await VulnerabilityService(estate.session).overview(sid)

    assert out.templates_run == 298
    assert out.targets_dropped == 2
    assert out.headline_detail.startswith("298 checks ran against")


async def test_a_run_that_never_scanned_is_not_covered(estate, now):
    sid = await estate.scan("example.com", "recon", at=now)
    await estate.activity("recon", {"subdomain_discovery": "success"})
    counts = (await ScanService(estate.session).finding_counts([sid]))[sid]
    assert counts.covered is False


async def test_a_partial_vulnerability_stage_with_nothing_found_covered(estate, now):
    sid = await estate.scan("example.com", "cut", at=now)
    await estate.activity("cut", {"vulnerability_scan": "partial"})
    counts = (await ScanService(estate.session).finding_counts([sid]))[sid]
    assert counts.covered is True
    assert counts.critical == counts.high == counts.medium == 0


async def test_severity_filter_ignores_suppressed_findings(estate, now):
    await estate.scan("example.com", "a", at=now)
    await estate.vulns("a", [("rce", "critical")], at=now)
    await estate.scan("example.com", "b", at=now - timedelta(hours=1))
    await estate.vulns("b", [("sqli", "high")], at=now)
    estate.session.add(
        VulnerabilityTriage(
            project_id=estate.project_id,
            target_id=estate.targets["example.com"],
            fingerprint="rce",
            template_id="rce",
            matched_at="https://www.example.com/",
            state="accepted",
        )
    )
    await estate.session.flush()
    service = ScanService(estate.session)

    crit = await _ids(service, project_id=estate.project_id, severities=["critical"])
    high = await _ids(service, project_id=estate.project_id, severities=["high"])

    assert crit == []
    assert [s.id for s in high] == [estate.scans["b"]]


async def test_latest_keeps_the_newest_run_of_each_target(estate, now):
    await estate.scan("a.com", "a-old", at=now - timedelta(days=2))
    await estate.scan("a.com", "a-new", at=now)
    await estate.scan("b.com", "b-only", at=now - timedelta(days=1))
    service = ScanService(estate.session)

    rows = await _ids(service, project_id=estate.project_id, latest=True)
    assert {s.id for s in rows} == {estate.scans["a-new"], estate.scans["b-only"]}

    items = [service.to_read(s) for s in rows]
    await service.attach_target_runs(items)
    runs = {i.id: i.target_runs for i in items}
    assert runs[estate.scans["a-new"]] == 2
    assert runs[estate.scans["b-only"]] == 1


async def test_short_flags_a_partial_or_failed_stage(estate, now):
    await estate.scan("example.com", "clean", at=now)
    await estate.activity("clean", {"http_probe": "success"})
    await estate.scan("example.com", "cut", at=now - timedelta(hours=1))
    await estate.activity("cut", {"http_probe": "partial"})
    service = ScanService(estate.session)

    short = await _ids(service, project_id=estate.project_id, short=True)
    clean = await _ids(service, project_id=estate.project_id, short=False)

    assert [s.id for s in short] == [estate.scans["cut"]]
    assert [s.id for s in clean] == [estate.scans["clean"]]


async def test_added_leaves_out_a_first_run(durable_estate, now):
    estate = durable_estate
    await estate.scan("example.com", "first", at=now - timedelta(days=1))
    await estate.hosts("first", ["a.example.com"], at=now - timedelta(days=1))
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", ["a.example.com", "b.example.com"], at=now)
    await estate.scan("example.org", "only", at=now)
    await estate.hosts("only", ["a.example.org"], at=now)
    await estate.session.commit()
    service = ScanService(estate.session)
    await service.prepare_growth(estate.project_id)

    added = await _ids(service, project_id=estate.project_id, added=True)
    rest = await _ids(service, project_id=estate.project_id, added=False)

    assert [s.id for s in added] == [estate.scans["second"]]
    assert {s.id for s in rest} == {estate.scans["first"], estate.scans["only"]}


async def test_daily_counts_runs_with_each_severity(estate, now):
    today = now.replace(hour=12, minute=0, second=0, microsecond=0)
    await estate.scan("example.com", "x", at=today)
    await estate.vulns("x", [("rce", "critical"), ("sqli", "high")], at=today)
    await estate.scan(
        "example.com", "y", at=today - timedelta(minutes=5), status="failed"
    )
    service = ScanService(estate.session)

    daily = await service.daily(estate.project_id, 3)
    last = daily.days[-1]

    assert len(daily.days) == 4, "the three-day window touches four calendar days"
    assert (last.runs, last.failed, last.critical, last.high, last.medium) == (
        2,
        1,
        1,
        1,
        0,
    )
    assert (daily.window.runs, daily.window.critical) == (2, 1)
    crit = await _ids(
        service,
        project_id=estate.project_id,
        severities=["critical"],
        started_from=daily.since,
    )
    assert len(crit) == daily.window.critical


async def test_the_daily_totals_slide_with_the_clock(estate, now):
    await estate.scan("example.com", "inside", at=now - timedelta(days=2, hours=23))
    await estate.scan("example.com", "outside", at=now - timedelta(days=3, hours=1))
    service = ScanService(estate.session)

    daily = await service.daily(estate.project_id, 3)
    listed = await _ids(service, project_id=estate.project_id, started_from=daily.since)

    assert daily.window.runs == len(listed) == 1
    assert sum(d.runs for d in daily.days) >= daily.window.runs


async def test_trends_are_oldest_first_and_capped(estate, now):
    for i in range(12):
        await estate.scan("example.com", f"r{i}", at=now - timedelta(days=12 - i))
    await estate.vulns("r11", [("rce", "critical")], at=now)
    service = ScanService(estate.session)

    [trend] = await service.finding_trends(
        estate.project_id, [estate.targets["example.com"]]
    )

    assert len(trend.points) == 10
    assert trend.points[-1].scan_id == estate.scans["r11"]
    assert trend.points[-1].critical == 1
    started = [p.started_at for p in trend.points]
    assert started == sorted(started)
    assert await estate.session.scalar(
        select(Scan.id).where(Scan.id == trend.points[0].scan_id)
    )


async def test_latest_for_targets_returns_one_run_per_target(estate, now):
    await estate.scan("example.com", "old", at=now - timedelta(days=2))
    await estate.scan("example.com", "new", at=now)
    await estate.activity("new", RAN_VULNS)
    await estate.vulns("new", [("rce", "critical")], at=now)
    await estate.scan("other.com", "only", at=now - timedelta(days=1))

    service = ScanService(estate.session)
    runs = await service.latest_for_targets(
        estate.project_id,
        [estate.targets["example.com"], estate.targets["other.com"]],
    )
    by_target = {r.target_id: r for r in runs}

    assert len(runs) == 2
    assert by_target[estate.targets["example.com"]].id == estate.scans["new"]
    assert by_target[estate.targets["example.com"]].findings.critical == 1
    assert by_target[estate.targets["example.com"]].target_runs == 2
    assert by_target[estate.targets["other.com"]].id == estate.scans["only"]
