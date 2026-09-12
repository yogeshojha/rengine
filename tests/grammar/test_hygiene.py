from __future__ import annotations

import pytest
from sqlalchemy import select, update

from app.services.subdomain import SubdomainService
from shared.definitions.hygiene import CHECK_KEYS
from shared.definitions.hygiene import HygieneCheck as C
from shared.models.subdomain import Subdomain, SubdomainFilter

pytestmark = pytest.mark.grammar


async def _seed(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run",
        ["a.example.com", "b.example.com", "c.example.com", "quiet.example.com"],
        at=now,
        status=200,
    )
    sid = estate.scans["run"]
    marks = {
        "a.example.com": (
            [C.NO_HSTS, C.CORS_CREDENTIALS],
            [C.NO_HSTS, C.CORS_CREDENTIALS, C.NO_NOSNIFF],
        ),
        "b.example.com": ([C.NO_HSTS], [C.NO_HSTS, C.NO_NOSNIFF]),
        "c.example.com": ([], [C.NO_HSTS, C.NO_NOSNIFF]),
    }
    for name, (issues, checked) in marks.items():
        await estate.session.execute(
            update(Subdomain)
            .where(Subdomain.scan_id == sid, Subdomain.name == name)
            .values(
                hygiene_issues=[str(k) for k in issues],
                hygiene_checked=[str(k) for k in checked],
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


async def test_hygiene_filters_match_the_rows_they_promise(estate, session, now):
    sid = await _seed(estate, now)
    service = SubdomainService(session)
    pid = estate.project_id
    assert await _count(service, pid, sid, "hygiene:no_hsts") == 2
    assert await _count(service, pid, sid, "hygiene:cors_credentials") == 1
    assert await _count(service, pid, sid, "hygiene:warning") == 1
    assert await _count(service, pid, sid, "hygiene:info") == 2
    assert await _count(service, pid, sid, "hygiene:any") == 2
    assert await _count(service, pid, sid, "hygiene:none") == 1
    assert await _count(service, pid, sid, "not hygiene:no_hsts") == 2
    assert await _count(service, pid, sid, "hygiene:[no_hsts,cors_credentials]") == 2


async def test_unknown_check_is_a_parse_error(estate, session, now):
    sid = await _seed(estate, now)
    result = await SubdomainService(session).search(
        project_id=estate.project_id,
        scope=sid,
        f=SubdomainFilter(q="hygiene:nope", limit=5),
    )
    assert result.error is not None
    assert "nope" in result.error.message


async def test_summary_counts_equal_the_filters(estate, session, now):
    sid = await _seed(estate, now)
    service = SubdomainService(session)
    pid = estate.project_id
    summary = await service.hygiene(project_id=pid, scope=sid)
    assert summary.evaluated == 3
    assert summary.pending == 1
    assert summary.clean == 1
    assert summary.warning == 1
    assert summary.info == 2
    by_key = {c.key: c for c in summary.checks}
    assert set(by_key) == set(CHECK_KEYS)
    for check in summary.checks:
        assert check.failing == await _count(service, pid, sid, check.query)
    assert by_key[C.NO_HSTS].applicable == 3
    assert by_key[C.NO_NOSNIFF].failing == 0


async def test_facet_lists_only_failing_checks(estate, session, now):
    sid = await _seed(estate, now)
    service = SubdomainService(session)
    facets = await service.facets(project_id=estate.project_id, scope=sid)
    assert {f.value: f.count for f in facets.hygiene} == {
        C.NO_HSTS: 2,
        C.CORS_CREDENTIALS: 1,
    }
    rows = (
        await session.execute(select(Subdomain.name).where(Subdomain.scan_id == sid))
    ).scalars()
    assert len(list(rows)) == 4
