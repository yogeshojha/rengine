from __future__ import annotations

import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.services.watch import WatchService
from shared.definitions.bounty_programs import ScopeState
from shared.definitions.watch import (
    CT_SOURCE,
    WATCH_HOST_KEY,
    WatchEventKind,
    WatchHostState,
    WatchItem,
    WatchStatus,
    excluded_by,
    host_pattern,
    plan_scope,
)
from shared.enums.target import TargetType
from shared.models.bounty_program import BountyProgram, BountyScope
from shared.models.http_asset import HttpAsset
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.watch import ProgramWatch, WatchEvent, WatchHost, WatchUpdate
from shared.services import watch_sync
from shared.utils.datetime import utc_now
from tests.conftest import Estate

pytestmark = pytest.mark.api


def _scope(identifier: str, state: str, asset_type: str = "WILDCARD", **kw):
    return SimpleNamespace(
        id=uuid.uuid4(),
        asset_identifier=identifier,
        scope_state=state,
        asset_type=asset_type,
        target_value=kw.get("target_value"),
        target_type=kw.get("target_type"),
    )


# ---------- pure planning ----------


def test_plan_scope_turns_wildcards_into_subtree_items_and_exclusions_into_patterns():
    scopes = [
        _scope(
            "*.example.com",
            ScopeState.IN_SCOPE.value,
            target_value="example.com",
            target_type=TargetType.DOMAIN,
        ),
        _scope(
            "shop.example.net",
            ScopeState.IN_SCOPE.value,
            "URL",
            target_value="shop.example.net",
            target_type=TargetType.DOMAIN,
        ),
        _scope("community.example.com", ScopeState.OUT_OF_SCOPE.value, "URL"),
        _scope("*.stores.example.com", ScopeState.OUT_OF_SCOPE.value),
        _scope("10.0.0.0/8", ScopeState.OUT_OF_SCOPE.value, "CIDR"),
        _scope("https://example.com/legacy/", ScopeState.OUT_OF_SCOPE.value, "URL"),
    ]
    plan = plan_scope(scopes)
    assert [i.item for i in plan.items] == [".example.com", "shop.example.net"]
    assert plan.wildcards == 1
    assert plan.targets == [
        ("example.com", TargetType.DOMAIN),
        ("shop.example.net", TargetType.DOMAIN),
    ]
    assert plan.excluded_ips == ["10.0.0.0/8"]
    assert plan.unenforceable == ["https://example.com/legacy/"]
    assert excluded_by("community.example.com", plan.excluded_subdomains)
    assert excluded_by("a.stores.example.com", plan.excluded_subdomains)
    assert excluded_by("stores.example.com", plan.excluded_subdomains)
    assert not excluded_by("communityx.example.com", plan.excluded_subdomains)
    assert not excluded_by("api.example.com", plan.excluded_subdomains)


def test_host_pattern_escapes_and_anchors():
    assert host_pattern("docs.example.com") == r"^docs\.example\.com$"
    assert host_pattern("*.example.com") == r"(^|\.)example\.com$"
    assert host_pattern("https://example.com/path") is None
    assert host_pattern("1.2.3.4") is None


def test_watch_item_matching():
    subtree = WatchItem(item=".example.com", target_value="example.com", scope_id="s")
    exact = WatchItem(
        item="shop.example.com", target_value="shop.example.com", scope_id="s"
    )
    assert subtree.matches("a.b.example.com")
    assert subtree.matches("example.com")
    assert not subtree.matches("example.com.evil.net")
    assert not subtree.matches("notexample.com")
    assert exact.matches("SHOP.example.com")
    assert not exact.matches("x.shop.example.com")


# ---------- database paths ----------


async def _program(estate, handle: str | None = None) -> BountyProgram:
    program = BountyProgram(
        platform="hackerone",
        handle=handle or f"acme-{uuid.uuid4().hex[:8]}",
        name="Acme",
        program_state="public",
        submission_state="open",
    )
    estate.session.add(program)
    await estate.session.flush()
    estate.session.add_all(
        [
            BountyScope(
                program_id=program.id,
                asset_type="WILDCARD",
                asset_identifier="*.acme.test",
                scope_state=ScopeState.IN_SCOPE.value,
                target_value="acme.test",
                target_type=TargetType.DOMAIN,
            ),
            BountyScope(
                program_id=program.id,
                asset_type="URL",
                asset_identifier="forum.acme.test",
                scope_state=ScopeState.OUT_OF_SCOPE.value,
            ),
        ]
    )
    await estate.session.flush()
    return program


async def _watch(estate, program: BountyProgram, **kw) -> ProgramWatch:
    watch = ProgramWatch(
        project_id=estate.project_id,
        program_id=program.id,
        status=WatchStatus.ACTIVE.value,
        cadence="off",
        created_by=estate.user_id,
        watch_items=[
            WatchItem(
                item=".acme.test", target_value="acme.test", scope_id="s"
            ).to_dict()
        ],
        notify_in_app=False,
        **kw,
    )
    estate.session.add(watch)
    await estate.session.flush()
    return watch


@pytest.fixture
async def estate(session):
    return await Estate(session).setup()


async def test_match_and_place_host_into_a_watching_run(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    target_id = await estate.target("acme.test")
    session = estate.session

    watches = await session.run_sync(watch_sync.active_watches)
    hits = watch_sync.match("new.acme.test", watches)
    assert [(w.id, i.item) for w, i in hits] == [(watch.id, ".acme.test")]
    assert watch_sync.match("acme.test.evil", watches) == []

    item = hits[0][1]
    target = await session.run_sync(watch_sync.target_for, watch, item)
    assert target is not None
    assert target.id == target_id

    host, created = await session.run_sync(
        lambda s: watch_sync.record_sighting(
            s,
            watch=watch,
            target=target,
            item=item,
            name="new.acme.test",
            cert={
                "sha256": "ab",
                "issuer": "CN=T",
                "not_before": "2026-09-12T09:00:00Z",
            },
        )
    )
    assert created
    assert host.state == WatchHostState.NEW.value
    assert watch.hosts_seen == 1

    _again, created_again = await session.run_sync(
        lambda s: watch_sync.record_sighting(
            s, watch=watch, target=target, item=item, name="new.acme.test", cert={}
        )
    )
    assert not created_again
    assert host.sightings == 2

    host.resolved_ips = ["192.0.2.10"]
    scan = await session.run_sync(
        lambda s: watch_sync.place_host(
            s, watch=watch, program_name=program.name, target=target, host=host
        )
    )
    assert scan is not None
    assert scan.engine_name == "Watching · Acme"
    assert scan.scope == "full"
    row = (
        await session.execute(
            select(Subdomain).where(
                Subdomain.scan_id == scan.id, Subdomain.name == "new.acme.test"
            )
        )
    ).scalar_one()
    assert row.sources == [CT_SOURCE]
    assert row.is_active
    assert row.resolved_ips == ["192.0.2.10"]

    again = await session.run_sync(
        lambda s: watch_sync.place_host(
            s, watch=watch, program_name=program.name, target=target, host=host
        )
    )
    assert again.id == scan.id

    assert await session.run_sync(
        watch_sync.known_host, estate.project_id, "new.acme.test"
    )
    assert not await session.run_sync(
        watch_sync.known_host, estate.project_id, "other.acme.test"
    )


async def test_place_host_defers_while_a_census_scan_runs(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    await estate.target("acme.test")
    await estate.scan("acme.test", "live", at=utc_now(), status="running")
    session = estate.session
    target = await session.run_sync(
        watch_sync.target_for, watch, WatchItem(".acme.test", "acme.test", "s")
    )
    host, _ = await session.run_sync(
        lambda s: watch_sync.record_sighting(
            s,
            watch=watch,
            target=target,
            item=WatchItem(".acme.test", "acme.test", "s"),
            name="wait.acme.test",
            cert={},
        )
    )
    assert (
        await session.run_sync(
            lambda s: watch_sync.place_host(
                s, watch=watch, program_name=program.name, target=target, host=host
            )
        )
        is None
    )


async def test_out_of_scope_uses_the_program_exclusions(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    session = estate.session
    assert await session.run_sync(watch_sync.out_of_scope, watch, "forum.acme.test")
    assert not await session.run_sync(watch_sync.out_of_scope, watch, "api.acme.test")


async def test_settle_probe_alerts_once_per_fingerprint_and_honours_the_query(estate):
    program = await _program(estate)
    watch = await _watch(estate, program, alert_query="status:200")
    target_id = await estate.target("acme.test")
    session = estate.session
    now = utc_now()

    host = WatchHost(
        watch_id=watch.id,
        project_id=estate.project_id,
        target_id=target_id,
        name="app.acme.test",
        state=WatchHostState.PROBING.value,
        matched_item=".acme.test",
        resolved_ips=["192.0.2.20"],
    )
    session.add(host)
    await session.flush()

    scan_id = await estate.scan(
        "acme.test",
        "probe",
        at=now,
        scope="focused",
        config={WATCH_HOST_KEY: str(host.id)},
    )
    host.scan_id = scan_id
    await estate.hosts("probe", ["app.acme.test"], at=now, status=200, title="Login")
    session.add(
        HttpAsset(
            scan_id=scan_id,
            target_id=target_id,
            project_id=estate.project_id,
            url="https://app.acme.test",
            host="app.acme.test",
            scheme="https",
            status_code=200,
            title="Login",
            tech=["Nginx"],
            ip="192.0.2.20",
            discovered_at=now,
        )
    )
    await session.flush()
    scan = await session.get(Scan, scan_id)

    state = await session.run_sync(watch_sync.settle_probe, scan)
    assert state == WatchHostState.ALERTED.value
    assert host.alerts == 1
    assert host.status_code == 200
    assert host.title == "Login"
    assert host.tech == ["Nginx"]
    events = (
        (
            await session.execute(
                select(WatchEvent.kind).where(WatchEvent.watch_id == watch.id)
            )
        )
        .scalars()
        .all()
    )
    assert events == [WatchEventKind.HOST_ALERTED.value]

    state = await session.run_sync(watch_sync.settle_probe, scan)
    assert state == WatchHostState.ALERTED.value
    assert host.alerts == 1

    watch.alert_query = "status:500"
    host.fingerprint = None
    state = await session.run_sync(watch_sync.settle_probe, scan)
    assert state == WatchHostState.QUIET.value
    assert host.alerts == 1


async def test_settle_probe_rejects_a_bad_query_and_still_alerts(estate):
    program = await _program(estate)
    watch = await _watch(estate, program, alert_query="status:")
    target_id = await estate.target("acme.test")
    session = estate.session
    now = utc_now()
    host = WatchHost(
        watch_id=watch.id,
        project_id=estate.project_id,
        target_id=target_id,
        name="bad.acme.test",
        state=WatchHostState.PROBING.value,
        resolved_ips=["192.0.2.30"],
    )
    session.add(host)
    await session.flush()
    scan_id = await estate.scan(
        "acme.test",
        "probe2",
        at=now,
        scope="focused",
        config={WATCH_HOST_KEY: str(host.id)},
    )
    host.scan_id = scan_id
    await estate.hosts("probe2", ["bad.acme.test"], at=now, status=404)
    scan = await session.get(Scan, scan_id)
    state = await session.run_sync(watch_sync.settle_probe, scan)
    assert state == WatchHostState.ALERTED.value
    assert watch.last_error
    assert watch.last_error.startswith("Alert query rejected")


async def test_reconcile_creates_targets_and_records_scope_changes(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    session = estate.session

    first = await session.run_sync(watch_sync.reconcile, watch, initial=True)
    assert first["created"] == 1
    assert first["items"] == 1

    session.add(
        BountyScope(
            program_id=program.id,
            asset_type="WILDCARD",
            asset_identifier="*.acme.dev",
            scope_state=ScopeState.IN_SCOPE.value,
            target_value="acme.dev",
            target_type=TargetType.DOMAIN,
        )
    )
    await session.flush()
    second = await session.run_sync(watch_sync.reconcile, watch)
    assert second["created"] == 1
    assert second["added"] == 1
    assert second["removed"] == 0
    assert sorted(i["item"] for i in watch.watch_items) == [".acme.dev", ".acme.test"]
    kinds = (
        await session.execute(
            select(WatchEvent.kind, WatchEvent.name).where(
                WatchEvent.watch_id == watch.id
            )
        )
    ).all()
    assert (WatchEventKind.SCOPE_ADDED.value, "acme.dev") in kinds


def test_next_retry_backs_off_and_gives_up():
    fresh = SimpleNamespace(first_seen_at=utc_now(), sightings=1)
    assert watch_sync.next_retry(fresh) is not None
    old = SimpleNamespace(first_seen_at=utc_now() - timedelta(hours=49), sightings=3)
    assert watch_sync.next_retry(old) is None


def test_watch_update_validates_like_create():
    with pytest.raises(ValueError, match="cadence"):
        WatchUpdate(cadence="hourly")
    with pytest.raises(ValueError, match="Rate ceiling"):
        WatchUpdate(rate_limit=9000)
    assert WatchUpdate(cadence="weekly", rate_limit=10).rate_limit == 10


def test_next_retry_ladder_grows_with_age():
    fresh = SimpleNamespace(first_seen_at=utc_now(), sightings=1)
    day_old = SimpleNamespace(
        first_seen_at=utc_now() - timedelta(hours=25), sightings=1
    )
    soon = watch_sync.next_retry(fresh) - utc_now()
    later = watch_sync.next_retry(day_old) - utc_now()
    assert soon < timedelta(minutes=15)
    assert later > timedelta(minutes=120)


async def test_settle_probe_alerts_when_the_probe_never_ran(estate):
    program = await _program(estate)
    watch = await _watch(estate, program, alert_query="status:200")
    target_id = await estate.target("acme.test")
    session = estate.session
    host = WatchHost(
        watch_id=watch.id,
        project_id=estate.project_id,
        target_id=target_id,
        name="ghost.acme.test",
        state=WatchHostState.PROBING.value,
        resolved_ips=["192.0.2.40"],
    )
    session.add(host)
    await session.flush()
    scan_id = await estate.scan(
        "acme.test",
        "broken",
        at=utc_now(),
        scope="focused",
        status="failed",
        config={WATCH_HOST_KEY: str(host.id)},
    )
    host.scan_id = scan_id
    scan = await session.get(Scan, scan_id)
    state = await session.run_sync(watch_sync.settle_probe, scan)
    assert state == WatchHostState.ALERTED.value
    assert host.reason == "probe failed"
    assert host.alerts == 1


async def test_record_sighting_survives_a_duplicate_insert(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    await estate.target("acme.test")
    session = estate.session
    item = WatchItem(".acme.test", "acme.test", "s")
    target = await session.run_sync(watch_sync.target_for, watch, item)
    first, created = await session.run_sync(
        lambda s: watch_sync.record_sighting(
            s, watch=watch, target=target, item=item, name="dup.acme.test", cert={}
        )
    )
    assert created
    session.expunge(first)
    again, created_again = await session.run_sync(
        lambda s: watch_sync.record_sighting(
            s, watch=watch, target=target, item=item, name="dup.acme.test", cert={}
        )
    )
    assert not created_again
    assert again.id == first.id


async def test_reconcile_keeps_items_when_the_scope_comes_back_empty(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    session = estate.session
    await session.run_sync(watch_sync.reconcile, watch, initial=True)
    await session.execute(
        BountyScope.__table__.delete().where(BountyScope.program_id == program.id)
    )
    await session.flush()
    result = await session.run_sync(watch_sync.reconcile, watch)
    assert result == {"skipped": "empty scope"}
    assert [i["item"] for i in watch.watch_items] == [".acme.test"]
    assert watch.last_error
    assert "empty" in watch.last_error


async def test_mute_restores_the_prior_state(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    target_id = await estate.target("acme.test")
    session = estate.session
    host = WatchHost(
        watch_id=watch.id,
        project_id=estate.project_id,
        target_id=target_id,
        name="quiet.acme.test",
        state=WatchHostState.UNRESOLVED.value,
    )
    session.add(host)
    await session.flush()
    service = WatchService(session)
    muted = await service.mute_host(watch.id, host.id, estate.project_id)
    assert muted.state == WatchHostState.MUTED.value
    back = await service.mute_host(watch.id, host.id, estate.project_id)
    assert back.state == WatchHostState.UNRESOLVED.value


async def test_events_query_filters_scope_changes_since_a_mark(estate):
    program = await _program(estate)
    watch = await _watch(estate, program)
    session = estate.session
    mark = utc_now()
    session.add_all(
        [
            WatchEvent(
                watch_id=watch.id,
                project_id=estate.project_id,
                kind=WatchEventKind.SCOPE_ADDED.value,
                name="new.acme.dev",
                created_at=mark + timedelta(minutes=1),
            ),
            WatchEvent(
                watch_id=watch.id,
                project_id=estate.project_id,
                kind=WatchEventKind.WATCH_UPDATED.value,
                created_at=mark + timedelta(minutes=1),
            ),
            WatchEvent(
                watch_id=watch.id,
                project_id=estate.project_id,
                kind=WatchEventKind.SCOPE_REMOVED.value,
                name="old.acme.dev",
                created_at=mark - timedelta(minutes=1),
            ),
        ]
    )
    await session.flush()
    service = WatchService(session)
    rows = (
        (
            await session.execute(
                service.events_query(watch.id, kind="scope", since=mark)
            )
        )
        .scalars()
        .all()
    )
    assert [r.name for r in rows] == ["new.acme.dev"]
    all_scope = (
        (await session.execute(service.events_query(watch.id, kind="scope")))
        .scalars()
        .all()
    )
    assert len(all_scope) == 2
