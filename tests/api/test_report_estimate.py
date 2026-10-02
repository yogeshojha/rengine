from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.report import ReportService
from shared.definitions.reports import ReportScope, subject_scope
from shared.definitions.vulnerabilities import VulnState
from shared.models.report import ReportCreate
from shared.models.vulnerability import VulnerabilityTriage

pytestmark = pytest.mark.api


async def _two_runs(estate, now):
    old = now - timedelta(days=1)
    await estate.scan("example.com", "first", at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("first", ["a.example.com"], at=old)
    await estate.hosts("second", ["a.example.com", "b.example.com"], at=now)
    await estate.vulns("first", [("old-a", "high")], at=old)
    await estate.vulns("second", [("new-a", "medium"), ("new-b", "low")], at=now)
    await estate.activity("second", {"vulnerability_scan": "success"})


def test_a_target_subject_reads_the_target_scope():
    assert subject_scope(ReportScope.SCAN.value, has_scan=False) == "target"
    assert subject_scope(None, has_scan=True) == "scan"
    assert subject_scope(ReportScope.TARGET.value, has_scan=True) == "target"


async def test_a_target_subject_is_estimated_from_its_latest_run(estate, now):
    await _two_runs(estate, now)
    target_id = estate.targets["example.com"]

    estimate = await ReportService(estate.session).estimate(
        ReportCreate(target_id=target_id), estate.project_id
    )

    assert estimate.findings == 2
    assert estimate.assets == 2


async def test_a_scan_subject_is_estimated_from_that_scan(estate, now):
    await _two_runs(estate, now)

    estimate = await ReportService(estate.session).estimate(
        ReportCreate(scan_id=estate.scans["first"]), estate.project_id
    )

    assert estimate.findings == 1
    assert estimate.assets == 1


async def test_a_suppressed_finding_is_not_estimated(estate, now):
    await _two_runs(estate, now)
    target_id = estate.targets["example.com"]
    estate.session.add(
        VulnerabilityTriage(
            project_id=estate.project_id,
            target_id=target_id,
            fingerprint="new-b",
            template_id="new-b",
            matched_at="https://www.example.com/",
            state=VulnState.FALSE_POSITIVE.value,
        )
    )
    await estate.session.flush()

    estimate = await ReportService(estate.session).estimate(
        ReportCreate(target_id=target_id), estate.project_id
    )

    assert estimate.findings == 1
