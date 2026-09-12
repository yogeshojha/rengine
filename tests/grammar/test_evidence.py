from __future__ import annotations

from datetime import datetime

import pytest

from app.services.cve_exposure import CveExposureService
from app.services.software import SoftwareService
from app.services.vulnerability import VulnerabilityService
from shared.definitions.evidence import Evidence
from shared.definitions.notifications import SoftwareExposure, software_exposed
from shared.definitions.vulnerabilities import Severity
from shared.models.software import SoftwareCve, SoftwareFilter
from shared.models.vulnerability import Vulnerability, VulnerabilityFilter

pytestmark = pytest.mark.grammar

HOST = "www.example.com"
CVE = "CVE-2021-23017"


async def _software(
    estate, scan: str, *, at: datetime, cve: str = CVE, host: str = HOST
) -> None:
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    estate.session.add(
        SoftwareCve(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=target_id,
            fingerprint=f"{host}|nginx|1.18.0|{cve}",
            cve=cve,
            name="nginx",
            version="1.18.0",
            vendor="f5",
            product="nginx",
            cpe="cpe:2.3:a:f5:nginx:1.18.0:*:*:*:*:*:*:*",
            severity=Severity.HIGH.value,
            cvss_score=7.5,
            host=host,
            port=443,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _finding(
    estate,
    scan: str,
    *,
    at: datetime,
    template: str,
    cves: list[str] | None = None,
    host: str = HOST,
    interaction: dict | None = None,
    severity: str = Severity.HIGH.value,
) -> None:
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    estate.session.add(
        Vulnerability(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=target_id,
            fingerprint=f"{template}|{host}",
            template_id=template,
            template_name=template,
            severity=severity,
            matched_at=f"https://{host}/",
            host=host,
            cve_ids=cves or [],
            interaction=interaction or {},
            evidence=Evidence.PROVEN.value if interaction else Evidence.OBSERVED.value,
            request="GET / HTTP/1.1" if interaction is None else None,
            response="HTTP/1.1 200 OK" if interaction is None else None,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _vulns(estate, scan: str, q: str) -> list[str]:
    page = await VulnerabilityService(estate.session).search(
        estate.scans[scan], VulnerabilityFilter(q=q, limit=50)
    )
    assert page.error is None, page.error
    return sorted(row.template_id for row in page.items)


async def _software_rows(estate, scan: str, q: str) -> list[str]:
    page = await SoftwareService(estate.session).search(
        estate.scans[scan], SoftwareFilter(q=q, limit=50)
    )
    assert page.error is None, page.error
    return sorted(row.cve for row in page.items)


async def test_a_version_inference_corroborates_the_check_naming_its_cve(
    estate, now
) -> None:
    await estate.scan("example.com", "run", at=now)
    await _software(estate, "run", at=now)
    await _finding(estate, "run", at=now, template="nginx-cve", cves=[CVE])
    await _finding(estate, "run", at=now, template="other-check", cves=["CVE-2020-1"])

    assert await _vulns(estate, "run", "evidence:corroborated") == ["nginx-cve"]
    assert await _vulns(estate, "run", "evidence:observed") == ["other-check"]
    assert await _vulns(estate, "run", "is:corroborated") == ["nginx-cve"]

    page = await VulnerabilityService(estate.session).search(
        estate.scans["run"], VulnerabilityFilter(q="template=nginx-cve", limit=5)
    )
    row = page.items[0]
    assert row.evidence == Evidence.CORROBORATED.value
    assert [p.shared for p in row.corroborated_by] == [[CVE]]


async def test_proven_is_the_stored_column_and_never_also_corroborated(
    estate, now
) -> None:
    await estate.scan("example.com", "run", at=now)
    await _software(estate, "run", at=now)
    await _finding(
        estate,
        "run",
        at=now,
        template="oob-check",
        cves=[CVE],
        interaction={"protocol": "dns", "unique_id": "abc"},
    )
    assert await _vulns(estate, "run", "evidence:proven") == ["oob-check"]
    assert await _vulns(estate, "run", "evidence:corroborated") == []
    assert await _vulns(estate, "run", "is:proven") == ["oob-check"]
    assert await _vulns(estate, "run", "is:recorded") == []


async def test_software_evidence_is_a_column_the_grammar_reads(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _software(estate, "run", at=now)
    await _software(estate, "run", at=now, cve="CVE-2020-2")
    rows = (
        await estate.session.execute(
            SoftwareCve.__table__.select().where(SoftwareCve.cve == CVE)
        )
    ).all()
    await estate.session.execute(
        SoftwareCve.__table__.update()
        .where(SoftwareCve.id == rows[0].id)
        .values(evidence=Evidence.CORROBORATED.value)
    )
    assert await _software_rows(estate, "run", "evidence:corroborated") == [CVE]
    assert await _software_rows(estate, "run", "is:corroborated") == [CVE]
    assert await _software_rows(estate, "run", "evidence:inferred") == ["CVE-2020-2"]


async def test_the_cve_page_counts_equal_the_searches_they_open(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _software(estate, "run", at=now)
    await _software(estate, "run", at=now, host="api.example.com")
    await _finding(estate, "run", at=now, template="nginx-cve", cves=[CVE])
    await _finding(
        estate, "run", at=now, template="oob", cves=[CVE], interaction={"x": 1}
    )
    await _finding(
        estate,
        "run",
        at=now,
        template="info-only",
        cves=[CVE],
        severity=Severity.INFO.value,
        host="api.example.com",
    )

    report = await CveExposureService(estate.session).exposure(estate.project_id, CVE)
    steps = {s.evidence: s for s in report.ladder}
    for step in report.ladder:
        software = await _software_rows(
            estate, "run", f"cve={CVE} evidence:{step.evidence}"
        )
        findings = await _vulns(estate, "run", f"cve={CVE} evidence:{step.evidence}")
        assert step.software == len(software), step.evidence
        assert step.findings == len(findings), step.evidence
    assert steps[Evidence.INFERRED.value].software == 2
    assert steps[Evidence.CORROBORATED.value].findings == 1
    assert steps[Evidence.PROVEN.value].findings == 1
    assert steps[Evidence.OBSERVED.value].findings == 1
    assert report.assets == 2
    assert report.locations_total == 5


def test_the_exposure_notification_is_delta_only_and_severe_only() -> None:
    def row(cve: str, host: str, severity: str, kev: bool = False) -> SoftwareExposure:
        return SoftwareExposure(
            cve=cve,
            host=host,
            name="nginx",
            version="1.18.0",
            severity=severity,
            is_kev=kev,
            kev_ransomware=False,
        )

    assert software_exposed([row(CVE, "a", Severity.LOW.value)]) is None
    payload = software_exposed(
        [
            row(CVE, "a", Severity.HIGH.value),
            row(CVE, "a", Severity.HIGH.value),
            row(CVE, "b", Severity.MEDIUM.value),
            row(CVE, "c", Severity.CRITICAL.value, kev=True),
        ]
    )
    assert payload is not None
    assert payload["title"] == f"2 assets newly match {CVE}"
    assert payload["message"].count("•") == 2
    assert payload["metadata"]["url"] == f"/surface/cve/{CVE}"
    assert payload["severity"].value == "error"
