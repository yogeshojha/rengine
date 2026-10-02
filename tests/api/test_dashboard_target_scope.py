from __future__ import annotations

import pytest

from app.services.dashboard_activity import DashboardActivityService
from app.services.dashboard_overview import DashboardOverviewService
from app.services.surface_scope import SurfaceScopeService
from app.services.target_scope import TargetFilter, resolve_targets
from shared.definitions.surface import SurfaceDimension
from shared.models.tag import Tag, TargetTag

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value


async def _two_targets(estate, now):
    await estate.scan("one.example", "one", at=now)
    await estate.hosts("one", ["a.one.example", "b.one.example"], at=now, status=200)
    await estate.vulns("one", [("c1", "critical")], at=now, host="a.one.example")
    await estate.scan("two.example", "two", at=now)
    await estate.hosts("two", ["a.two.example"], at=now, status=200)


async def test_no_filter_resolves_to_none(estate):
    assert (
        await resolve_targets(estate.session, estate.project_id, TargetFilter()) is None
    )


async def test_the_overview_reads_only_the_scoped_targets(estate, now):
    await _two_targets(estate, now)
    one = estate.targets["one.example"]

    out = await DashboardOverviewService(estate.session).overview(
        estate.project_id, "7d", frozenset({one})
    )

    assert out.targets_total == 1
    assert [t.value for t in out.targets] == ["one.example"]
    web = next(m for m in out.surface if m.key == WEB)
    assert web.value == 2
    assert out.risk.total == 1


async def test_the_surface_scope_keeps_only_the_scoped_targets_scans(estate, now):
    await _two_targets(estate, now)
    two = estate.targets["two.example"]

    scope = await SurfaceScopeService(estate.session).scope(
        estate.project_id, WEB, targets=frozenset({two})
    )

    assert scope.ids == (estate.scans["two"],)


async def test_a_tag_and_a_target_must_both_hold(estate, now):
    await _two_targets(estate, now)
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
        TargetTag(target_id=estate.targets["one.example"], tag_id=tag.id)
    )
    await estate.session.flush()

    both = await resolve_targets(
        estate.session,
        estate.project_id,
        TargetFilter(target_ids=(estate.targets["two.example"],), tag_id=tag.id),
    )

    assert both == frozenset()


async def test_activity_under_a_scope_lists_only_its_runs(estate, now):
    await _two_targets(estate, now)
    one = estate.targets["one.example"]

    out = await DashboardActivityService(estate.session).activity(
        estate.project_id, "7d", programs=False, targets=frozenset({one})
    )

    assert out.events
    assert {e.scan_id for e in out.events} == {estate.scans["one"]}
