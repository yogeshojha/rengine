from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.api.v1.whats_new import whats_new
from app.services.whats_new import WhatsNewService
from shared.definitions.bounty_programs import BountyEvent
from shared.definitions.watch import CT_SOURCE, WatchHostState
from shared.definitions.whats_new import Fact, NewBasis, NewKind, ProgramRing
from shared.enums.target import TargetType
from shared.models.bounty_program import BountyEventRow, BountyProgram, BountyScope
from shared.models.watch import ProgramWatch, WatchHost

pytestmark = pytest.mark.api


def _program(handle: str, name: str) -> BountyProgram:
    return BountyProgram(
        platform="hackerone",
        handle=handle,
        name=name,
        program_state="public",
        submission_state="open",
    )


def _service(estate) -> WhatsNewService:
    return WhatsNewService(estate.session)


def _sections(out, kind: str):
    return [s for g in out.groups for s in g.sections if s.kind == kind]


def _rows(out, kind: str):
    return [i for s in _sections(out, kind) for i in s.items]


def _values(out, kind: str) -> list[str]:
    return [i.value for i in _rows(out, kind)]


async def _rescan(estate, now, fresh_rows, *, kev=False, host="www.example.com"):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.vulns("older", [("old-check", "low")], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now)
    await estate.vulns("fresh", fresh_rows, at=now, kev=kev, host=host)


async def test_a_rescan_reports_new_critical_and_high_findings(estate, now):
    await _rescan(
        estate,
        now,
        [
            ("old-check", "low"),
            ("solr-rce", "critical"),
            ("info-leak", "high"),
            ("weak-tls", "medium"),
        ],
        kev=True,
    )

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[NewKind.FINDING.value] == 2
    assert out.facts[NewKind.FINDING.value] == {
        Fact.CRITICAL.value: 1,
        Fact.HIGH.value: 1,
        Fact.KEV.value: 2,
    }
    assert out.basis == NewBasis.MARK.value
    group = out.groups[0]
    assert group.scan_id == estate.scans["fresh"]
    assert group.previous_scan_id == estate.scans["older"]
    assert group.at == group.completed_at
    assert group.severities == {"critical": 1, "high": 1}
    assert [e.query for e in group.evidence] == [
        "is:new template=solr-rce",
        "is:new template=info-leak",
    ]
    today = now.date().isoformat()
    assert [d.counts for d in out.daily if d.date == today] == [
        {NewKind.FINDING.value: 2, "critical": 1, "high": 1}
    ]


async def test_a_first_scan_is_not_an_event(estate, now):
    await estate.scan("example.com", "first", at=now)
    await estate.vulns("first", [("solr-rce", "critical")], at=now)

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.groups == []
    assert out.counts[NewKind.FINDING.value] == 0


async def test_a_rescan_with_only_lower_severities_is_not_an_event(estate, now):
    await _rescan(estate, now, [("old-check", "low"), ("weak-tls", "medium")])

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.groups == []
    assert out.counts[NewKind.FINDING.value] == 0


async def test_a_day_range_bounds_the_feed(estate, now):
    old = now - timedelta(days=5)
    await estate.scan("example.com", "base", at=now - timedelta(days=9))
    await estate.vulns("base", [("old-check", "low")], at=now - timedelta(days=9))
    await estate.scan("example.com", "mid", at=old)
    await estate.vulns("mid", [("mid-rce", "critical")], at=old)
    await estate.scan("example.com", "fresh", at=now)
    await estate.vulns("fresh", [("new-rce", "high")], at=now)

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, day_from=old.date(), day_to=old.date()
    )

    assert out.basis == NewBasis.DAYS.value
    assert out.counts[NewKind.FINDING.value] == 1
    assert [g.scan_id for g in out.groups] == [estate.scans["mid"]]


async def test_text_filter_picks_runs_and_keeps_their_whole_count(estate, now):
    await _rescan(estate, now, [("solr-rce", "critical"), ("info-leak", "high")])

    service = _service(estate)
    hit = await service.feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1), q="solr"
    )
    miss = await service.feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1), q="zimbra"
    )

    assert hit.counts[NewKind.FINDING.value] == 2
    assert miss.groups == []


async def test_a_period_starting_mid_run_counts_the_whole_run(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.vulns("older", [("old-check", "low")], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now)
    await estate.vulns(
        "fresh", [("early-rce", "critical")], at=now - timedelta(hours=3)
    )
    await estate.vulns("fresh", [("late-rce", "high")], at=now)

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.groups[0].severities == {"critical": 1, "high": 1}
    assert out.events == 1


async def test_bounty_days_follow_the_viewer_zone(estate, now):
    program = _program("acme", "Acme")
    estate.session.add(program)
    await estate.session.flush()
    late = now.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
    for at in (late, late + timedelta(hours=2)):
        estate.session.add(
            BountyEventRow(
                platform=program.platform,
                program_id=program.id,
                handle=program.handle,
                program_name=program.name,
                kind=BountyEvent.PROGRAM_ADDED.value,
                created_at=at,
            )
        )
    await estate.session.flush()

    service = _service(estate)
    utc = await service.feed(estate.project_id, estate.user_id, window="7d")
    nepal = await service.feed(
        estate.project_id, estate.user_id, window="7d", tz="Asia/Kathmandu"
    )

    assert len(utc.groups) == 1
    assert len(nepal.groups) == 2


async def test_an_unknown_program_filter_shows_nothing(estate, now):
    await _rescan(estate, now, [("solr-rce", "critical")])

    out = await _service(estate).feed(
        estate.project_id,
        estate.user_id,
        since=now - timedelta(hours=1),
        platform="hackerone",
        handle="missing",
    )

    assert out.groups == []
    assert out.counts[NewKind.FINDING.value] == 0


async def test_a_kind_filter_leaves_no_empty_run(estate, now):
    await _rescan(estate, now, [("solr-rce", "critical")])

    out = await _service(estate).feed(
        estate.project_id,
        estate.user_id,
        since=now - timedelta(hours=1),
        kinds={NewKind.SCOPE.value},
    )

    assert out.groups == []
    assert out.counts[NewKind.FINDING.value] == 1


async def test_a_hand_added_target_is_not_new(estate, now):
    await estate.target("example.com")

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[NewKind.TARGET.value] == 0


async def test_a_certificate_host_is_reported_by_the_watch_alone(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.hosts("older", ["a.example.com"], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now)
    await estate.hosts("fresh", ["ct.example.com"], at=now, sources=[CT_SOURCE])
    program = _program("acme", "Acme")
    estate.session.add(program)
    await estate.session.flush()
    watch = ProgramWatch(
        project_id=estate.project_id,
        program_id=program.id,
        created_by=estate.user_id,
    )
    estate.session.add(watch)
    await estate.session.flush()
    estate.session.add(
        WatchHost(
            watch_id=watch.id,
            project_id=estate.project_id,
            target_id=estate.targets["example.com"],
            name="ct.example.com",
            state=WatchHostState.ALERTED.value,
            first_seen_at=now,
            status_code=200,
            title="Hello",
        )
    )
    await estate.session.flush()

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[NewKind.CERT_HOST.value] == 1
    assert out.facts[NewKind.CERT_HOST.value] == {Fact.ANSWERING.value: 1}
    group = next(g for g in out.groups if g.subject.kind == "program")
    assert group.subject.watched is True
    assert group.subject.watch_id == watch.id
    row = _rows(out, NewKind.CERT_HOST.value)[0]
    assert row.host_id is not None
    assert row.watch_id == watch.id


async def test_scope_events_count_for_engaged_programs_only(estate, now):
    mine = _program("acme", "Acme")
    other = _program("globex", "Globex")
    estate.session.add_all([mine, other])
    await estate.session.flush()
    estate.session.add(
        ProgramWatch(
            project_id=estate.project_id,
            program_id=mine.id,
            created_by=estate.user_id,
        )
    )
    estate.session.add_all(
        [
            BountyScope(
                program_id=mine.id,
                asset_type="WILDCARD",
                asset_identifier="*.acme.com",
                scope_state="in_scope",
                target_value="acme.com",
                target_type=TargetType.DOMAIN,
            ),
            BountyScope(
                program_id=other.id,
                asset_type="DOMAIN",
                asset_identifier="app.globex.com",
                scope_state="in_scope",
                target_value="app.globex.com",
                target_type=TargetType.DOMAIN,
            ),
        ]
    )
    for program, identifier in ((mine, "*.acme.com"), (other, "app.globex.com")):
        estate.session.add(
            BountyEventRow(
                platform=program.platform,
                program_id=program.id,
                handle=program.handle,
                program_name=program.name,
                kind=BountyEvent.SCOPE_ADDED.value,
                asset_type="WILDCARD",
                asset_identifier=identifier,
                created_at=now,
            )
        )
    estate.session.add(
        BountyEventRow(
            platform=other.platform,
            program_id=other.id,
            handle=other.handle,
            program_name=other.name,
            kind=BountyEvent.PROGRAM_ADDED.value,
            created_at=now,
        )
    )
    await estate.session.flush()

    service = _service(estate)
    out = await service.feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )
    assert _values(out, NewKind.SCOPE.value) == ["*.acme.com"]
    row = _rows(out, NewKind.SCOPE.value)[0]
    assert row.importable is True
    assert row.target_exists is False
    assert row.scope_id is not None
    assert out.facts[NewKind.SCOPE.value] == {Fact.NOT_TARGET.value: 1}
    assert _values(out, NewKind.PROGRAM.value) == ["Globex"]

    wide = await service.feed(
        estate.project_id,
        estate.user_id,
        since=now - timedelta(hours=1),
        ring=ProgramRing.LIBRARY.value,
    )
    assert sorted(_values(wide, NewKind.SCOPE.value)) == [
        "*.acme.com",
        "app.globex.com",
    ]


async def test_an_asset_leaving_scope_names_the_target_it_covers(estate, now):
    program = _program("acme", "Acme")
    estate.session.add(program)
    await estate.session.flush()
    tid = await estate.target("legacy.acme.com")
    estate.session.add(
        BountyScope(
            program_id=program.id,
            asset_type="DOMAIN",
            asset_identifier="legacy.acme.com",
            scope_state="out_of_scope",
            target_value="legacy.acme.com",
            target_type=TargetType.DOMAIN,
        )
    )
    estate.session.add(
        BountyEventRow(
            platform=program.platform,
            program_id=program.id,
            handle=program.handle,
            program_name=program.name,
            kind=BountyEvent.WENT_OUT_OF_SCOPE.value,
            asset_type="DOMAIN",
            asset_identifier="legacy.acme.com",
            created_at=now,
        )
    )
    await estate.session.flush()

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[NewKind.OUT_OF_SCOPE.value] == 1
    row = _rows(out, NewKind.OUT_OF_SCOPE.value)[0]
    assert row.target_id == tid
    assert row.target_exists is True
    assert row.importable is False


async def test_a_target_the_scope_added_is_new(estate, now):
    program = _program("acme", "Acme")
    estate.session.add(program)
    await estate.session.flush()
    estate.session.add(
        BountyScope(
            program_id=program.id,
            asset_type="DOMAIN",
            asset_identifier="acme.com",
            scope_state="in_scope",
            target_value="acme.com",
            target_type=TargetType.DOMAIN,
        )
    )
    await estate.target("acme.com")
    await estate.session.flush()

    out = await _service(estate).feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert out.counts[NewKind.TARGET.value] == 1
    assert out.facts[NewKind.TARGET.value] == {Fact.NOT_SCANNED.value: 1}
    row = _rows(out, NewKind.TARGET.value)[0]
    assert row.program_name == "Acme"
    assert row.scanned is False


async def test_a_host_whose_screenshot_moved_is_a_visual_pair(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.hosts(
        "older",
        ["a.example.com"],
        at=now - timedelta(days=2),
        status=200,
        title="Home",
        phash=1,
    )
    await estate.hosts(
        "older", ["same.example.com"], at=now - timedelta(days=2), phash=255
    )
    await estate.scan("example.com", "fresh", at=now)
    await estate.hosts(
        "fresh",
        ["a.example.com"],
        at=now,
        status=200,
        title="Home",
        phash=0xFFFF,
    )
    await estate.hosts("fresh", ["same.example.com"], at=now, phash=255)

    service = _service(estate)
    out = await service.visual(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )
    feed = await service.feed(
        estate.project_id, estate.user_id, since=now - timedelta(hours=1)
    )

    assert [p.host for p in out.pairs] == ["a.example.com"]
    pair = out.pairs[0]
    assert pair.distance == 15
    assert pair.moved == []
    assert pair.silent is True
    assert pair.scan_id == estate.scans["fresh"]
    assert pair.previous_scan_id == estate.scans["older"]
    assert out.silent == 1
    assert feed.visual == 1


async def test_the_mark_moves_and_unseen_reads_it(estate, now):
    await estate.scan("example.com", "older", at=now - timedelta(days=2))
    await estate.vulns("older", [("old-check", "low")], at=now - timedelta(days=2))
    await estate.scan("example.com", "fresh", at=now - timedelta(minutes=5))
    await estate.vulns(
        "fresh", [("solr-rce", "critical")], at=now - timedelta(minutes=5)
    )
    service = _service(estate)

    before = await service.unseen(estate.project_id, estate.user_id, bounty=True)
    marked = await service.mark_seen(estate.user_id, estate.project_id)
    after = await service.unseen(estate.project_id, estate.user_id, bounty=True)
    feed = await service.feed(estate.project_id, estate.user_id)

    assert before == 1
    assert after == 0
    assert feed.basis == NewBasis.MARK.value
    assert feed.marked_at == marked


async def test_the_route_rejects_a_bad_window_and_ring(estate):
    with pytest.raises(HTTPException) as bad_window:
        await whats_new(
            current_user=None,
            service=None,
            session=None,
            project_id=uuid.uuid4(),
            window="1y",
        )
    assert bad_window.value.status_code == 422
    with pytest.raises(HTTPException) as bad_ring:
        await whats_new(
            current_user=None,
            service=None,
            session=None,
            project_id=uuid.uuid4(),
            ring="everyone",
        )
    assert bad_ring.value.status_code == 422
