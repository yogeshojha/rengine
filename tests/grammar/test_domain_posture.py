from __future__ import annotations

import pytest
from sqlalchemy import update

from app.services.domain_posture import DomainPostureService
from app.services.subdomain import SubdomainService
from shared.definitions.domain_posture import PostureCheck as C
from shared.models.domain_posture import DomainPosture
from shared.models.subdomain import Subdomain, SubdomainFilter

pytestmark = pytest.mark.grammar


async def _seed(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run",
        ["a.example.com", "b.example.com", "c.example.net", "quiet.example.com"],
        at=now,
        status=200,
    )
    sid = estate.scans["run"]
    tid = estate.targets["example.com"]
    zones = {
        "example.com": (
            [C.DMARC_NONE, C.CAA_MISSING],
            [C.SPF_MISSING, C.DMARC_MISSING, C.DMARC_NONE, C.CAA_MISSING],
            3,
        ),
        "example.net": ([], [C.SPF_MISSING, C.DMARC_MISSING, C.CAA_MISSING], 1),
    }
    for zone, (issues, checked, hosts) in zones.items():
        estate.session.add(
            DomainPosture(
                scan_id=sid,
                target_id=tid,
                project_id=estate.project_id,
                zone=zone,
                hosts=hosts,
                dnssec="unsigned",
                posture_issues=[str(k) for k in issues],
                posture_checked=[str(k) for k in checked],
            )
        )
    await estate.session.flush()
    for zone, (issues, checked, _) in zones.items():
        await estate.session.execute(
            update(Subdomain)
            .where(
                Subdomain.scan_id == sid,
                (Subdomain.name == zone) | Subdomain.name.like(f"%.{zone}"),
            )
            .values(
                posture_issues=[str(k) for k in issues],
                posture_checked=[str(k) for k in checked],
            )
        )
    await estate.session.flush()
    return sid


async def _count(service, project_id, sid, q: str) -> int:
    result = await service.search(
        project_id=project_id, scope=sid, f=SubdomainFilter(q=q, limit=50)
    )
    assert result.error is None, result.error
    return result.total


async def test_posture_filters_match_the_rows_they_promise(estate, session, now):
    sid = await _seed(estate, now)
    service = SubdomainService(session)
    pid = estate.project_id
    assert await _count(service, pid, sid, "posture:dmarc_none") == 3
    assert await _count(service, pid, sid, "posture:caa_missing") == 3
    assert await _count(service, pid, sid, "posture:warning") == 3
    assert await _count(service, pid, sid, "posture:info") == 3
    assert await _count(service, pid, sid, "posture:any") == 3
    assert await _count(service, pid, sid, "posture:none") == 1
    assert await _count(service, pid, sid, "not posture:dmarc_none") == 1
    assert await _count(service, pid, sid, "posture:[dmarc_none,spf_missing]") == 3


async def test_unknown_check_is_a_parse_error(estate, session, now):
    sid = await _seed(estate, now)
    result = await SubdomainService(session).search(
        project_id=estate.project_id,
        scope=sid,
        f=SubdomainFilter(q="posture:nope", limit=5),
    )
    assert result.error is not None
    assert "nope" in result.error.message


async def test_the_facet_counts_equal_the_filters(estate, session, now):
    sid = await _seed(estate, now)
    service = SubdomainService(session)
    facets = await service.facets(project_id=estate.project_id, scope=sid)
    by_key = {f.value: f.count for f in facets.posture}
    assert by_key[C.DMARC_NONE] == 3
    assert by_key[C.CAA_MISSING] == 3
    assert C.SPF_MISSING not in by_key
    filtered = await service.search(
        project_id=estate.project_id,
        scope=sid,
        f=SubdomainFilter(posture=[C.DMARC_NONE.value], limit=50),
    )
    assert filtered.total == 3


async def test_the_summary_counts_zones_not_hosts(estate, session, now):
    sid = await _seed(estate, now)
    summary = await DomainPostureService(session).summary(estate.project_id, sid)
    assert summary.covered is True
    assert summary.evaluated == 2
    assert summary.warning == 1
    assert summary.clean == 1
    assert summary.spoofable == 1
    assert summary.hosts == 4
    counts = {c.key: c for c in summary.checks}
    assert counts[C.DMARC_NONE].failing == 1
    assert counts[C.DMARC_NONE].applicable == 1
    assert counts[C.CAA_MISSING].applicable == 2
    assert [z.zone for z in summary.zones] == ["example.com", "example.net"]

    per_target = await DomainPostureService(session).for_target(
        estate.project_id, estate.targets["example.com"]
    )
    assert per_target.scan_id == sid
    assert per_target.evaluated == 2

    project = await DomainPostureService(session).for_project(estate.project_id)
    assert project.evaluated == 2
