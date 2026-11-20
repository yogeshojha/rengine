"""Project access on results, search, dashboard and interest routes beyond the guard walk."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.models.interest import InterestDismissal, InterestRule
from shared.models.subdomain import Subdomain
from tests.api.test_project_access import Call, walker  # noqa: F401

pytestmark = pytest.mark.api

SCAN_PAIRED = [
    ("GET", "/subdomains/hosting", None),
    ("GET", "/subdomains/tech", None),
    ("GET", "/subdomains/insights", None),
    ("POST", "/subdomains/timeline", {}),
    ("POST", "/subdomains/timeline/renders", {}),
    ("POST", "/ports/timeline", {}),
    ("POST", "/vulnerabilities/timeline", {}),
]


async def _send(walker, method, url, params=None, body=None, *, admin=False):  # noqa: F811
    world = walker.world
    user = world.admin if admin else world.member
    return await walker.send(method, Call("x", url, params or {}, body), user)


async def _count(walker, model, *where) -> int:  # noqa: F811
    maker = async_sessionmaker(walker.engine, class_=AsyncSession)
    async with maker() as session:
        return await session.scalar(
            select(func.count()).select_from(model).where(*where)
        )


@pytest.mark.parametrize(("method", "url", "body"), SCAN_PAIRED)
async def test_a_scan_of_another_project_under_an_open_project_is_not_found(
    walker,  # noqa: F811
    method,
    url,
    body,
):
    a, b = walker.world.a, walker.world.b
    mixed = {"project_id": str(a["project_id"]), "scan_id": str(b["scan_id"])}
    refused = await _send(walker, method, url, mixed, body)
    assert refused.status_code == 404
    assert refused.json()["detail"] == "Scan not found."

    own = {"project_id": str(a["project_id"]), "scan_id": str(a["scan_id"])}
    assert (await _send(walker, method, url, own, body)).status_code == 200
    theirs = {"project_id": str(b["project_id"]), "scan_id": str(b["scan_id"])}
    assert (
        await _send(walker, method, url, theirs, body, admin=True)
    ).status_code == 200


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("GET", "/endpoints/coverage", None),
        ("GET", "/endpoints/structure", None),
        ("POST", "/endpoints/gone", {}),
        ("POST", "/endpoints/verify", {"host": "x"}),
        ("GET", "/ports/origins", None),
    ],
)
async def test_a_scan_of_another_project_is_not_found(walker, method, url, body):  # noqa: F811
    b = walker.world.b
    theirs = await _send(walker, method, url, {"scan_id": str(b["scan_id"])}, body)
    unknown = await _send(walker, method, url, {"scan_id": str(uuid.uuid4())}, body)
    assert theirs.status_code == unknown.status_code == 404
    assert theirs.json() == unknown.json()


async def test_an_endpoint_of_another_project_is_not_found(walker):  # noqa: F811
    a, b = walker.world.a, walker.world.b
    url = f"/endpoints/{b['endpoint_id']}"
    for scan in (b["scan_id"], a["scan_id"]):
        refused = await _send(walker, "GET", url, {"scan_id": str(scan)})
        assert refused.status_code == 404
    own = await _send(
        walker, "GET", f"/endpoints/{a['endpoint_id']}", {"scan_id": str(a["scan_id"])}
    )
    assert own.status_code == 200


async def test_a_finding_of_another_project_has_no_intel(walker):  # noqa: F811
    a, b = walker.world.a, walker.world.b
    theirs = await _send(
        walker, "GET", f"/threat-intel/finding/{b['vulnerability_id']}"
    )
    unknown = await _send(walker, "GET", f"/threat-intel/finding/{uuid.uuid4()}")
    assert theirs.status_code == unknown.status_code == 404
    assert theirs.json() == unknown.json()
    own = await _send(walker, "GET", f"/threat-intel/finding/{a['vulnerability_id']}")
    assert own.status_code == 200


async def test_a_bulk_dismissal_naming_another_project_writes_nothing(walker):  # noqa: F811
    a, b = walker.world.a, walker.world.b
    before = await _count(walker, InterestDismissal)
    rows = [
        {"host": "www.ownrows.test", "target_id": str(a["target_id"]), "kind": "k"},
        {"host": "www.qzcanary.test", "target_id": str(b["target_id"]), "kind": "k"},
    ]
    refused = await _send(walker, "POST", "/interest/dismiss/bulk", body={"rows": rows})
    assert refused.status_code == 404
    assert refused.json()["detail"] == "Target not found."
    assert await _count(walker, InterestDismissal) == before

    one = await _send(walker, "POST", "/interest/dismiss", body=rows[1])
    assert one.status_code == 404
    assert await _count(walker, InterestDismissal) == before

    done = await _send(
        walker, "POST", "/interest/dismiss/bulk", body={"rows": rows[:1]}
    )
    assert done.status_code == 200


async def test_a_rule_preview_reads_open_scans_only(walker):  # noqa: F811
    a, b = walker.world.a, walker.world.b
    body = {"query": "host:www"}
    for params in (
        {"scan_id": str(b["scan_id"])},
        {"scan_id": str(b["scan_id"]), "project_id": str(a["project_id"])},
        {"scan_id": str(a["scan_id"]), "project_id": str(b["project_id"])},
    ):
        refused = await _send(walker, "POST", "/interest/rules/preview", params, body)
        assert refused.status_code == 404
    own = await _send(
        walker, "POST", "/interest/rules/preview", {"scan_id": str(a["scan_id"])}, body
    )
    assert own.status_code == 200


async def test_deleting_rows_of_another_project_removes_nothing(walker):  # noqa: F811
    b = walker.world.b
    held = await _count(walker, Subdomain, Subdomain.scan_id == b["scan_id"])
    body = {"dimension": "web_assets", "ids": [str(b["subdomain_id"])]}
    for params in (
        {"scan_id": str(b["scan_id"])},
        {"project_id": str(b["project_id"])},
    ):
        refused = await _send(walker, "POST", "/surface/delete", params, body)
        assert refused.status_code == 404
    assert await _count(walker, Subdomain, Subdomain.scan_id == b["scan_id"]) == held


async def test_a_project_page_filtered_to_another_projects_target_is_not_found(walker):  # noqa: F811
    a, b = walker.world.a, walker.world.b
    url = "/interest/project"
    params = {"project_id": str(a["project_id"]), "target_id": str(b["target_id"])}
    assert (await _send(walker, "POST", url, params, {})).status_code == 404
    params["target_id"] = str(a["target_id"])
    assert (await _send(walker, "POST", url, params, {})).status_code == 200


async def test_a_member_cannot_edit_a_rule_every_project_reads(walker):  # noqa: F811
    a = walker.world.a
    maker = async_sessionmaker(walker.engine, class_=AsyncSession)
    rule_id = uuid.uuid4()
    async with maker() as session:
        session.add(
            InterestRule(
                id=rule_id, name="Shared", kind="other", builtin=True, query="host:x"
            )
        )
        await session.commit()
    url = f"/interest/rules/{rule_id}"
    params = {"project_id": str(a["project_id"])}
    body = {"enabled": False, "weight": 1}
    refused = await _send(walker, "PATCH", url, params, body)
    assert refused.status_code == 404
    assert refused.json()["detail"] == "Rule not found."
    async with maker() as session:
        stored = await session.get(InterestRule, rule_id)
        assert (stored.enabled, stored.weight) == (True, None)
    done = await _send(walker, "PATCH", url, params, body, admin=True)
    assert done.status_code == 200
    assert done.json()["enabled"] is False
    own = await _send(
        walker,
        "POST",
        "/interest/rules",
        params,
        {"name": "Own", "query": "host:www", "kind": "other"},
    )
    assert own.status_code == 201
    edited = await _send(
        walker, "PATCH", f"/interest/rules/{own.json()['id']}", params, body
    )
    assert edited.status_code == 200
