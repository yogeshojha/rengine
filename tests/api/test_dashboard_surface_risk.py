from __future__ import annotations

from datetime import timedelta

import pytest
import sqlalchemy as sa

from app.services.dashboard_surface_risk import SurfaceRiskService
from shared.models.tag import Tag, TargetTag

pytestmark = pytest.mark.api


async def test_rows_read_live_and_open_findings_per_target(estate, now):
    await estate.scan("big.example", "big", at=now)
    await estate.hosts("big", ["a.big.example", "b.big.example"], at=now, status=200)
    await estate.hosts("big", ["c.big.example"], at=now)
    await estate.vulns("big", [("f1", "low")], at=now, host="a.big.example")
    await estate.scan("small.example", "small", at=now)
    await estate.hosts("small", ["www.small.example"], at=now, status=200)
    await estate.vulns(
        "small",
        [("c1", "critical"), ("h1", "high"), ("m1", "medium"), ("l1", "low")],
        at=now,
        host="www.small.example",
        kev=True,
    )
    await estate.target("never.example")

    out = await SurfaceRiskService(estate.session).rows(estate.project_id)

    assert out.targets_total == 3
    assert out.scanned == 2
    assert [r.target_value for r in out.rows] == ["small.example", "big.example"]
    small, big = out.rows
    assert big.names == 3
    assert big.live == 2
    assert big.findings == 1
    assert big.actionable == 0
    assert small.live == 1
    assert small.findings == 4
    assert small.actionable == 3
    assert small.kev == 4
    assert small.act == 4, "every KEV row is act now"
    assert small.by_severity == {"critical": 1, "high": 1, "medium": 1, "low": 1}
    assert out.live == 3
    assert out.findings == 5


async def test_the_newest_covering_scan_speaks_for_a_target(estate, now):
    old = now - timedelta(days=2)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", ["a.example.com", "b.example.com"], at=old, status=200)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", ["a.example.com"], at=now, status=200)

    out = await SurfaceRiskService(estate.session).rows(estate.project_id)

    assert out.rows[0].live == 1
    assert out.rows[0].scan_id == estate.scans["second"]


async def test_a_tag_filter_narrows_the_rows(estate, now):
    await estate.scan("tagged.example", "tagged", at=now)
    await estate.hosts("tagged", ["www.tagged.example"], at=now, status=200)
    await estate.scan("plain.example", "plain", at=now)
    await estate.hosts("plain", ["www.plain.example"], at=now, status=200)
    never = await estate.target("never.example")
    tag = Tag(
        name="prod",
        slug="prod",
        color="#6B7280",
        project_id=estate.project_id,
        created_by=estate.user_id,
    )
    estate.session.add(tag)
    await estate.session.flush()
    estate.session.add(
        TargetTag(target_id=estate.targets["tagged.example"], tag_id=tag.id)
    )
    estate.session.add(TargetTag(target_id=never, tag_id=tag.id))
    await estate.session.flush()

    out = await SurfaceRiskService(estate.session).rows(
        estate.project_id, tag_id=tag.id
    )

    assert out.targets_total == 2
    assert [r.target_value for r in out.rows] == ["tagged.example"]
    assert out.rows[0].tags == [tag.id]
    assert await estate.session.scalar(sa.select(sa.func.count()).select_from(Tag)) == 1
