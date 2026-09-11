from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.seed_selection import SeedSelectionService
from app.services.subdomain import SubdomainService
from shared.definitions.rescan import MAX_RUN_ASSETS
from shared.definitions.surface import SurfaceDimension
from shared.models.scan import QuerySelection, SeedPick, SeedSelection
from shared.models.subdomain import SubdomainFilter

pytestmark = pytest.mark.grammar

QUERIES = ["", "tech:nginx", "is:live", "status:200", "tech:nginx and is:live"]


async def _two_targets(estate, now):
    await estate.scan("a.example", "run_a", at=now)
    await estate.hosts(
        "run_a",
        ["www.a.example", "api.a.example"],
        at=now,
        ips=["10.0.0.1"],
        status=200,
        tech=["nginx"],
    )
    await estate.hosts("run_a", ["dark.a.example"], at=now)

    await estate.scan("b.example", "run_b", at=now)
    await estate.hosts(
        "run_b",
        ["www.b.example"],
        at=now,
        ips=["10.0.0.2"],
        status=200,
        tech=["nginx"],
    )
    return estate


@pytest.mark.parametrize("q", QUERIES)
async def test_a_query_seeds_exactly_the_rows_it_counts(estate, now, q):
    await _two_targets(estate, now)
    scan = estate.scans["run_a"]
    counted = await SubdomainService(estate.session).search(
        estate.project_id, scan, SubdomainFilter(q=q, limit=1)
    )
    assert counted.error is None, f"{q}: {counted.error}"

    resolved = await SeedSelectionService(estate.session).resolve(
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            query=QuerySelection(filter={"q": q}, scan_ids=[scan]),
        ),
        estate.project_id,
    )
    assert resolved.total == counted.total, (
        f"{q}: search counts {counted.total}, selection seeds {resolved.total}"
    )


async def test_a_selection_fans_out_one_group_per_target(estate, now):
    await _two_targets(estate, now)
    resolved = await SeedSelectionService(estate.session).resolve(
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            query=QuerySelection(filter={"q": "tech:nginx"}),
        ),
        estate.project_id,
    )
    assert {g.target_value for g in resolved.groups} == {"a.example", "b.example"}
    assert resolved.total == sum(len(g.values) for g in resolved.groups)
    assert not resolved.capped


async def test_picks_keep_their_own_scan(estate, now):
    await _two_targets(estate, now)
    resolved = await SeedSelectionService(estate.session).resolve(
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            picks=[
                SeedPick(value="www.a.example", scan_id=estate.scans["run_a"]),
                SeedPick(value="www.b.example", scan_id=estate.scans["run_b"]),
            ],
        ),
        estate.project_id,
    )
    by_scan = {g.scan_id: g.values for g in resolved.groups}
    assert by_scan[estate.scans["run_a"]] == ["www.a.example"]
    assert by_scan[estate.scans["run_b"]] == ["www.b.example"]


async def test_a_pick_without_a_scan_is_placed_by_the_dimension_scope(estate, now):
    await _two_targets(estate, now)
    resolved = await SeedSelectionService(estate.session).resolve(
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            picks=[SeedPick(value="www.b.example")],
        ),
        estate.project_id,
    )
    assert [g.scan_id for g in resolved.groups] == [estate.scans["run_b"]]
    assert resolved.total == 1


async def test_exclude_removes_a_row_the_query_matched(estate, now):
    await _two_targets(estate, now)
    service = SeedSelectionService(estate.session)
    selection = SeedSelection(
        dimension=SurfaceDimension.WEB_ASSETS.value,
        query=QuerySelection(filter={"q": "tech:nginx"}),
    )
    before = await service.resolve(selection, estate.project_id)
    selection.exclude = ["www.a.example"]
    after = await service.resolve(selection, estate.project_id)
    assert after.total == before.total - 1
    assert "www.a.example" not in [v for g in after.groups for v in g.values]


async def test_an_older_scan_does_not_seed_the_project_view(estate, now):
    """A project-wide selection reads each target's latest covering scan, not its history."""
    old = now - timedelta(days=7)
    await estate.scan("a.example", "old_a", at=old)
    await estate.hosts("old_a", ["gone.a.example"], at=old, status=200, tech=["nginx"])
    await _two_targets(estate, now)

    resolved = await SeedSelectionService(estate.session).resolve(
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            query=QuerySelection(filter={"q": "tech:nginx"}),
        ),
        estate.project_id,
    )
    seeded = [v for g in resolved.groups for v in g.values]
    assert "gone.a.example" not in seeded


async def test_a_selection_matching_nothing_resolves_to_no_groups(estate, now):
    await _two_targets(estate, now)
    resolved = await SeedSelectionService(estate.session).resolve(
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            query=QuerySelection(filter={"q": "tech:nothing-here"}),
        ),
        estate.project_id,
    )
    assert resolved.groups == []
    assert resolved.total == 0


def test_a_selection_takes_one_form_or_the_other():
    with pytest.raises(ValueError, match="not both"):
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            picks=[SeedPick(value="a.example")],
            query=QuerySelection(filter={}),
        )
    with pytest.raises(ValueError, match="not both"):
        SeedSelection(dimension=SurfaceDimension.WEB_ASSETS.value)


def test_the_cap_is_a_field_bound_not_a_silent_truncation():
    with pytest.raises(ValueError, match="at most"):
        SeedSelection(
            dimension=SurfaceDimension.WEB_ASSETS.value,
            picks=[SeedPick(value=f"h{i}.example") for i in range(MAX_RUN_ASSETS + 1)],
        )
