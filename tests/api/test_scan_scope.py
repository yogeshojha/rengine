from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.dashboard_overview import DashboardOverviewService
from app.services.surface_scope import SurfaceScopeService
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import Scanner
from shared.services.scan_scope import covering_stages

pytestmark = pytest.mark.api

VULNS = SurfaceDimension.VULNERABILITIES.value
SOFTWARE = SurfaceDimension.SOFTWARE.value


async def _checks_after_nuclei(estate, now):
    old = now - timedelta(days=1)
    nuclei = await estate.scan("example.com", "nuclei", at=old)
    await estate.activity("nuclei", {"vulnerability_scan": "success"})
    await estate.vulns("nuclei", [("rce", "critical"), ("sqli", "high")], at=old)
    checks = await estate.scan("example.com", "checks", at=now)
    await estate.activity("checks", {"http_probe": "success"})
    await estate.vulns(
        "checks", [("broken-link", "low")], at=now, scanner=Scanner.RENGINE.value
    )
    return nuclei, checks


async def test_check_findings_alone_do_not_cover_vulnerabilities(estate, now):
    nuclei, _ = await _checks_after_nuclei(estate, now)

    picks = await SurfaceScopeService(estate.session).scans_by_target(
        estate.project_id, VULNS
    )

    assert picks[estate.targets["example.com"]] == nuclei


async def test_scanner_findings_cover_without_a_stage_success(estate, now):
    old = now - timedelta(days=1)
    await estate.scan("example.com", "first", at=old)
    await estate.activity("first", {"vulnerability_scan": "success"})
    cancelled = await estate.scan("example.com", "cancelled", at=now)
    await estate.vulns("cancelled", [("rce", "critical")], at=now)

    picks = await SurfaceScopeService(estate.session).scans_by_target(
        estate.project_id, VULNS
    )

    assert picks[estate.targets["example.com"]] == cancelled


async def test_dashboard_counts_the_scanner_run(estate, now):
    await _checks_after_nuclei(estate, now)

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d"
    )

    vulns = next(m for m in out.surface if m.key == VULNS)
    assert vulns.value == 2


def test_the_probe_covers_software():
    assert "http_probe" in covering_stages()[SOFTWARE]


async def test_a_probe_without_matches_is_the_software_pick(estate, now):
    old = now - timedelta(days=1)
    await estate.scan("example.com", "ports", at=old)
    await estate.activity("ports", {"port_scan": "success"})
    probe = await estate.scan("example.com", "probe", at=now)
    await estate.activity("probe", {"http_probe": "success"})

    picks = await SurfaceScopeService(estate.session).scans_by_target(
        estate.project_id, SOFTWARE
    )

    assert picks[estate.targets["example.com"]] == probe
