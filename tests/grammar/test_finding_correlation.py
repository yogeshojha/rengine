from __future__ import annotations

from datetime import datetime

import pytest

from app.services.vulnerability import VulnerabilityService
from shared.definitions.vulnerabilities import Severity
from shared.models.software import SoftwareCve
from shared.models.vulnerability import Vulnerability, VulnerabilityFilter

pytestmark = pytest.mark.grammar

HOST = "www.example.com"


async def _finding(
    estate,
    *,
    at: datetime,
    template: str,
    host: str = HOST,
    severity: str = Severity.HIGH.value,
) -> None:
    sid = estate.scans["run"]
    estate.session.add(
        Vulnerability(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=await estate._target_of(sid),
            fingerprint=f"{template}|{host}",
            template_id=template,
            template_name=template,
            severity=severity,
            matched_at=f"https://{host}/",
            host=host,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _software(estate, *, at: datetime) -> None:
    sid = estate.scans["run"]
    estate.session.add(
        SoftwareCve(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=await estate._target_of(sid),
            fingerprint=f"{HOST}|nginx",
            cve="CVE-2021-23017",
            name="nginx",
            version="1.18.0",
            vendor="f5",
            product="nginx",
            cpe="cpe:2.3:a:f5:nginx:1.18.0:*:*:*:*:*:*:*",
            host=HOST,
            port=443,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _search(estate, q: str):
    page = await VulnerabilityService(estate.session).search(
        estate.scans["run"], VulnerabilityFilter(q=q, limit=50)
    )
    assert page.error is None, page.error
    return page


async def test_findings_on_the_same_web_asset_equal_the_host_search(
    estate, now
) -> None:
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, at=now, template="a", severity=Severity.CRITICAL.value)
    await _finding(estate, at=now, template="b")
    await _finding(estate, at=now, template="c", severity=Severity.INFO.value)
    await _finding(estate, at=now, template="a", host="api.example.com")
    await _software(estate, at=now)

    row = next(r for r in (await _search(estate, "template=b")).items)
    assert row.host_findings == {
        Severity.CRITICAL.value: 1,
        Severity.HIGH.value: 1,
        Severity.INFO.value: 1,
    }
    on_host = await _search(estate, f'host="{HOST}"')
    assert sum(row.host_findings.values()) == on_host.total
    assert row.asset is not None
    assert row.asset.software_cves == 1

    other = next(r for r in (await _search(estate, "host=api.example.com")).items)
    assert other.host_findings == {Severity.HIGH.value: 1}
    assert other.host_count == 2
