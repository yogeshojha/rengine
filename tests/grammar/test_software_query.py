from __future__ import annotations

from datetime import datetime

import pytest

from app.services.software import SoftwareService
from shared.definitions.software import Caveat, Confidence, VersionSource
from shared.definitions.vulnerabilities import Severity
from shared.models.software import SoftwareCve, SoftwareFilter

pytestmark = pytest.mark.grammar


async def _add(
    estate,
    scan: str,
    *,
    at: datetime,
    cve: str,
    name: str = "nginx",
    version: str = "1.18.0",
    host: str = "www.example.com",
    severity: str = Severity.HIGH.value,
    cvss: float | None = 7.5,
    epss: float | None = None,
    kev: bool = False,
    caveats: list[str] | None = None,
    source: str = VersionSource.BANNER.value,
) -> None:
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    caveats = caveats or []
    confidence = (
        Confidence.HIGH.value
        if not caveats
        else Confidence.MEDIUM.value
        if len(caveats) == 1
        else Confidence.LOW.value
    )
    estate.session.add(
        SoftwareCve(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=target_id,
            fingerprint=f"{host}|{name}|{version}|{cve}",
            cve=cve,
            name=name,
            version=version,
            vendor="f5",
            product="nginx",
            cpe=f"cpe:2.3:a:f5:nginx:{version}:*:*:*:*:*:*:*",
            version_source=source,
            severity=severity,
            cvss_score=cvss,
            epss_score=epss,
            is_kev=kev,
            confidence=confidence,
            caveats=caveats,
            host=host,
            port=443,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _search(estate, scan: str, q: str) -> tuple[int, list[str]]:
    page = await SoftwareService(estate.session).search(
        estate.scans[scan], SoftwareFilter(q=q, limit=50)
    )
    assert page.error is None, page.error
    return page.total, [row.cve for row in page.items]


async def test_the_total_equals_the_rows_it_opens(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017")
    await _add(
        estate, "run", at=now, cve="CVE-2023-44487", severity=Severity.MEDIUM.value
    )
    total, cves = await _search(estate, "run", "")
    assert total == len(cves) == 2


async def test_severity_and_score_filter_the_same_set(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(
        estate,
        "run",
        at=now,
        cve="CVE-2021-23017",
        severity=Severity.HIGH.value,
        cvss=7.5,
    )
    await _add(
        estate,
        "run",
        at=now,
        cve="CVE-2023-44487",
        severity=Severity.LOW.value,
        cvss=3.1,
    )
    assert await _search(estate, "run", "severity:high") == (1, ["CVE-2021-23017"])
    assert await _search(estate, "run", "cvss>=7") == (1, ["CVE-2021-23017"])
    assert (await _search(estate, "run", "cvss<5"))[1] == ["CVE-2023-44487"]


async def test_flags_read_the_intelligence_columns(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017", kev=True, epss=0.6)
    await _add(estate, "run", at=now, cve="CVE-2023-44487", epss=0.001)
    assert (await _search(estate, "run", "is:kev"))[1] == ["CVE-2021-23017"]
    assert (await _search(estate, "run", "is:likely"))[1] == ["CVE-2021-23017"]
    assert (await _search(estate, "run", "epss>=0.5"))[1] == ["CVE-2021-23017"]


async def test_confidence_and_caveats_are_searchable(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017")
    await _add(
        estate,
        "run",
        at=now,
        cve="CVE-2023-44487",
        caveats=[Caveat.BACKPORT.value],
    )
    assert (await _search(estate, "run", "is:firm"))[1] == ["CVE-2021-23017"]
    assert (await _search(estate, "run", "caveat:backport"))[1] == ["CVE-2023-44487"]
    assert (await _search(estate, "run", "confidence:medium"))[1] == ["CVE-2023-44487"]
    assert (await _search(estate, "run", "not caveat:backport"))[1] == [
        "CVE-2021-23017"
    ]


async def test_source_separates_a_stated_version_from_a_fingerprinted_one(
    estate, now
) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017")
    await _add(
        estate,
        "run",
        at=now,
        cve="CVE-2023-44487",
        source=VersionSource.FINGERPRINT.value,
    )
    assert (await _search(estate, "run", "is:stated"))[1] == ["CVE-2021-23017"]
    assert (await _search(estate, "run", "is:fingerprinted"))[1] == ["CVE-2023-44487"]


async def test_the_first_scan_of_a_target_reports_nothing_new(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017")
    assert (await _search(estate, "run", "is:new")) == (0, [])


async def test_new_is_what_the_earlier_scan_did_not_carry(estate, now) -> None:
    earlier = now.replace(year=now.year - 1)
    await estate.scan("example.com", "first", at=earlier)
    await _add(estate, "first", at=earlier, cve="CVE-2021-23017")
    await estate.scan("example.com", "second", at=now)
    await _add(estate, "second", at=now, cve="CVE-2021-23017")
    await _add(estate, "second", at=now, cve="CVE-2023-44487")
    total, cves = await _search(estate, "second", "is:new")
    assert total == 1
    assert cves == ["CVE-2023-44487"]


async def test_an_upgraded_release_retires_the_old_match(estate, now) -> None:
    earlier = now.replace(year=now.year - 1)
    await estate.scan("example.com", "first", at=earlier)
    await _add(estate, "first", at=earlier, cve="CVE-2021-23017", version="1.18.0")
    await estate.scan("example.com", "second", at=now)
    await _add(estate, "second", at=now, cve="CVE-2021-23017", version="1.24.0")
    total, _ = await _search(estate, "second", "is:new")
    assert total == 1


async def test_free_text_reaches_cve_software_and_host(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017", host="a.example.com")
    await _add(
        estate,
        "run",
        at=now,
        cve="CVE-2023-44487",
        name="Apache HTTP Server",
        host="b.example.com",
    )
    assert (await _search(estate, "run", "apache"))[1] == ["CVE-2023-44487"]
    assert (await _search(estate, "run", "a.example.com"))[1] == ["CVE-2021-23017"]
    assert (await _search(estate, "run", "23017"))[1] == ["CVE-2021-23017"]


async def test_a_parse_error_comes_back_on_the_page(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, cve="CVE-2021-23017")
    page = await SoftwareService(estate.session).search(
        estate.scans["run"], SoftwareFilter(q="severity:", limit=10)
    )
    assert page.error is not None
    assert page.items == []


async def test_facets_count_what_the_query_would_return(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(
        estate, "run", at=now, cve="CVE-2021-23017", severity=Severity.HIGH.value
    )
    await _add(
        estate, "run", at=now, cve="CVE-2023-44487", severity=Severity.HIGH.value
    )
    await _add(
        estate,
        "run",
        at=now,
        cve="CVE-2020-11022",
        severity=Severity.LOW.value,
        caveats=[Caveat.CONDITIONAL.value],
    )
    facets = await SoftwareService(estate.session).facets(estate.scans["run"])
    counts = {f.key: f.count for f in facets.severity}
    assert counts[Severity.HIGH.value] == 2
    for key, count in counts.items():
        total, _ = await _search(estate, "run", f"severity:{key}")
        assert total == count
    caveats = {f.key: f.count for f in facets.caveat}
    assert caveats[Caveat.CONDITIONAL.value] == 1
