from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.dashboard_overview import DashboardOverviewService
from app.services.dashboard_window import DashboardWindowService
from app.services.ip_address import IpAddressService
from app.services.port import PortService
from app.services.subdomain import SubdomainService
from app.services.surface_scope import SurfaceScopeService
from app.services.threat_intel import ThreatIntelService
from app.services.vulnerability import VulnerabilityService
from shared.definitions.dashboard import new_in_window, window_since
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import SUPPRESSED_STATES
from shared.models.ip_address import IpAddress
from shared.models.scan_correlation import IpGroupFilter, ServiceFilter
from shared.models.subdomain import SubdomainFilter
from shared.models.vulnerability import VulnerabilityFilter, VulnerabilityTriage

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value
SERVICES = SurfaceDimension.SERVICES.value
IPS = SurfaceDimension.IPS.value
VULNS = SurfaceDimension.VULNERABILITIES.value


async def _addresses(estate, scan: str, ips: list[str], *, at) -> None:
    sid = estate.scans[scan]
    for ip in ips:
        estate.session.add(
            IpAddress(
                scan_id=sid,
                target_id=await estate._target_of(sid),
                project_id=estate.project_id,
                ip=ip,
                source="test",
                discovered_at=at,
            )
        )
    await estate.session.flush()


async def _two_runs(estate, *, last):
    first = last - timedelta(days=20)
    await estate.scan("example.com", "first", at=first)
    await estate.hosts("first", ["a.example.com"], at=first, ips=["10.0.0.1"])
    await estate.vulns("first", [("old-check", "high")], at=first)
    await estate.ports("first", [("10.0.0.1", 22, "ssh")], at=first)
    await _addresses(estate, "first", ["10.0.0.1"], at=first)

    await estate.scan("example.com", "second", at=last)
    await estate.hosts(
        "second", ["a.example.com", "b.example.com"], at=last, ips=["10.0.0.1"]
    )
    await estate.vulns(
        "second", [("old-check", "high"), ("new-check", "critical")], at=last
    )
    await estate.ports(
        "second", [("10.0.0.1", 22, "ssh"), ("10.0.0.2", 443, "https")], at=last
    )
    await _addresses(estate, "second", ["10.0.0.1", "10.0.0.2"], at=last)


def _by_key(counts):
    return {row.key: row for row in counts.new}


async def _page_totals(estate, query: str) -> dict[str, int]:
    surfaces = SurfaceScopeService(estate.session)
    pid = estate.project_id
    web = await SubdomainService(estate.session).search(
        pid, await surfaces.scope(pid, WEB), SubdomainFilter(q=query)
    )
    vulns = await VulnerabilityService(estate.session).search(
        await surfaces.scope(pid, VULNS), VulnerabilityFilter(q=query)
    )
    services = await PortService(estate.session).search(
        await surfaces.scope(pid, SERVICES), ServiceFilter(q=query)
    )
    ips = await IpAddressService(estate.session).search(
        await surfaces.scope(pid, IPS), IpGroupFilter(q=query)
    )
    return {
        WEB: web.total,
        VULNS: vulns.total,
        SERVICES: services.total,
        IPS: ips.total,
    }


async def test_each_count_is_the_total_its_link_opens(estate, now):
    await _two_runs(estate, last=now - timedelta(days=2))

    counts = await DashboardWindowService(estate.session).counts(
        estate.project_id, "7d"
    )
    query = new_in_window("7d")
    rows = _by_key(counts)
    pages = await _page_totals(estate, query)

    assert all(row.query == query for row in counts.new)
    for key, total in pages.items():
        assert rows[key].count == total, key
    assert rows[WEB].count == 1, "b.example.com is the only new web asset"
    assert rows[VULNS].count == 1
    assert rows[SERVICES].count == 1
    assert rows[IPS].count == 1
    assert counts.findings == {"critical": 1}
    assert counts.targets_with_new_web_assets == 1


async def test_rows_recorded_before_the_window_are_not_counted(estate, now):
    await _two_runs(estate, last=now - timedelta(days=10))

    week = await DashboardWindowService(estate.session).counts(estate.project_id, "7d")
    fortnight = await DashboardWindowService(estate.session).counts(
        estate.project_id, "14d"
    )

    assert all(row.count == 0 for row in week.new)
    assert week.findings == {}
    assert _by_key(fortnight)[WEB].count == 1
    assert _by_key(fortnight)[VULNS].count == 1


async def test_a_first_scan_reports_nothing_new(estate, now):
    await estate.scan("example.com", "only", at=now)
    await estate.hosts("only", ["a.example.com"], at=now)
    await estate.vulns("only", [("check", "high")], at=now)

    counts = await DashboardWindowService(estate.session).counts(
        estate.project_id, "7d"
    )

    assert all(row.count == 0 for row in counts.new)


async def test_the_overview_window_slides_from_now(estate, now):
    await estate.scan("example.com", "inside", at=now - timedelta(days=6, hours=23))
    await estate.scan(
        "example.com", "outside", at=now - timedelta(days=7, hours=1), status="failed"
    )
    await estate.scan(
        "example.com", "broken", at=now - timedelta(hours=2), status="failed"
    )

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    assert out.runs_in_window == 2
    assert out.outcomes_in_window == {"completed": 1, "failed": 1}
    assert out.failed_in_window == 1
    assert abs((out.since - window_since("7d", now)).total_seconds()) < 60
    drawn = [d for d in out.daily if d.date >= out.since.date().isoformat()]
    assert sum(d.runs for d in drawn) >= out.runs_in_window


async def test_exploitation_counts_read_the_covering_scans(estate, now):
    old = now - timedelta(days=9)
    await estate.scan("example.com", "older", at=old)
    await estate.vulns("older", [("gone-kev", "critical")], at=old, kev=True)
    await estate.scan("example.com", "latest", at=now)
    await estate.vulns(
        "latest",
        [("kept-kev", "critical"), ("hidden-kev", "high")],
        at=now,
        kev=True,
    )
    estate.session.add(
        VulnerabilityTriage(
            project_id=estate.project_id,
            target_id=estate.targets["example.com"],
            fingerprint="hidden-kev",
            template_id="hidden-kev",
            matched_at="https://www.example.com/",
            state=SUPPRESSED_STATES[0],
        )
    )
    await estate.session.flush()

    scope = await SurfaceScopeService(estate.session).scope(estate.project_id, VULNS)
    service = ThreatIntelService(estate.session)
    coverage = await service.coverage(scope)
    listed = await service.signal_findings("kev", scope, limit=500)
    page = await VulnerabilityService(estate.session).search(
        scope, VulnerabilityFilter(q="is:kev")
    )

    assert coverage.kev == page.total == len(listed) == 1
    assert [f.template_name for f in listed] == ["Kept Kev"]
