from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.secret import SecretService
from shared.definitions.secrets import SecretGroup, SecretSource, SecretState
from shared.models.secret import Secret, SecretFilter

pytestmark = pytest.mark.grammar


async def _add(
    estate,
    scan: str,
    *,
    at: datetime,
    kind: str = "aws_access_key",
    group: str = SecretGroup.CLOUD.value,
    state: str = SecretState.EXPOSED.value,
    is_secret: bool = True,
    host: str = "www.example.com",
    subject: str | None = None,
    vendor: str = "Amazon Web Services",
    value: str = "AKIAV",
) -> None:
    ids = estate.row_ids(scan)
    estate.session.add(
        Secret(
            **ids,
            fingerprint=f"{kind}|{value}",
            kind=kind,
            group=group,
            vendor=vendor,
            state=state,
            is_secret=is_secret,
            value=f"AKIA{value}",
            subject=subject,
            host=host,
            url=f"https://{host}/app.js",
            source=SecretSource.BODY.value,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _search(estate, scan: str, q: str) -> tuple[int, list[str]]:
    page = await SecretService(estate.session).search(
        estate.scans[scan], SecretFilter(q=q, limit=50)
    )
    assert page.error is None, page.error
    return page.total, [row.kind for row in page.items]


async def test_the_total_equals_the_rows_it_opens(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, kind="aws_access_key", value="a")
    await _add(
        estate,
        "run",
        at=now,
        kind="email",
        group=SecretGroup.CONTACT.value,
        state=SecretState.PUBLIC.value,
        is_secret=False,
        subject="example.com",
        value="b",
    )

    total, kinds = await _search(estate, "run", "")
    assert total == 2

    total, kinds = await _search(estate, "run", "is:exposed")
    assert total == 1
    assert kinds == ["aws_access_key"]

    total, _ = await _search(estate, "run", "secret:email")
    assert total == 1

    total, _ = await _search(estate, "run", "group:cloud")
    assert total == 1

    total, _ = await _search(estate, "run", "state:public")
    assert total == 1


async def test_is_new_needs_a_baseline(estate, now) -> None:
    await estate.scan("example.com", "first", at=now)
    await _add(estate, "first", at=now, value="k")

    total, _ = await _search(estate, "first", "is:new")
    assert total == 0


async def test_a_value_seen_in_an_earlier_scan_is_not_new(estate, now) -> None:
    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await _add(estate, "first", at=old, value="k")
    await estate.scan("example.com", "second", at=now)
    await _add(estate, "second", at=now, value="k")
    await _add(estate, "second", at=now, kind="google_api_key", value="new")

    total, kinds = await _search(estate, "second", "is:new")
    assert total == 1
    assert kinds == ["google_api_key"]


async def test_a_facet_count_equals_its_search(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, kind="aws_access_key", value="a")
    await _add(estate, "run", at=now, kind="google_api_key", value="b")
    await _add(estate, "run", at=now, kind="google_api_key", value="c")

    service = SecretService(estate.session)
    facets = await service.facets(estate.scans["run"])
    for facet in facets.kind:
        total, _ = await _search(estate, "run", f"secret:{facet.key}")
        assert total == facet.count, facet.key


async def test_a_group_count_equals_its_drilldown(estate, now) -> None:
    await estate.scan("example.com", "run", at=now)
    await _add(estate, "run", at=now, kind="aws_access_key", value="a")
    await _add(estate, "run", at=now, kind="google_api_key", value="b")
    await _add(estate, "run", at=now, kind="google_api_key", value="c")

    service = SecretService(estate.session)
    groups = await service.groups(estate.scans["run"], SecretFilter(), "secret")
    assert groups.total_groups == 2
    for group in groups.groups:
        total, _ = await _search(estate, "run", group.query)
        assert total == group.count, group.query
