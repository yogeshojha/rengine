from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.services.tripwire import TripwireError, TripwireService
from shared.definitions.notifications import FiredRowLike, TripwireFired, tripwire_fired
from shared.definitions.surface import SurfaceDimension
from shared.definitions.tripwires import (
    TEMPLATES,
    CheckStatus,
    FireOn,
    OutcomeStatus,
    ScopeKind,
    Trigger,
    appears_query,
)
from shared.enums.notification import NotificationSeverity
from shared.models.notification_channel import NotificationChannel
from shared.models.scan import Scan
from shared.models.tag import Tag, TargetTag
from shared.models.tripwire import (
    NotifyAction,
    Outcome,
    Tripwire,
    TripwireCreate,
    TripwireMark,
    TripwirePreviewRequest,
    TripwireRun,
    TripwireScope,
    TripwireUpdate,
)
from shared.services.asset_query import QuerySyntaxError
from shared.services.tripwires import applicable, evaluate, validate_query
from shared.services.tripwires.actions import delivery_outcome
from shared.services.tripwires.evaluate import check

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value
VULN = SurfaceDimension.VULNERABILITIES.value


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    monkeypatch.setattr(session.sync_session, "commit", session.sync_session.flush)
    return session


async def _two_runs(estate, now):
    """One host answers 200 on both runs, one flips to 200, one appears."""
    earlier = now - timedelta(days=3)
    await estate.scan("example.com", "first", at=earlier)
    await estate.hosts("first", ["www.example.com"], at=earlier, status=200)
    await estate.hosts("first", ["vpn.example.com"], at=earlier, status=403)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts(
        "second", ["www.example.com", "vpn.example.com"], at=now, status=200
    )
    await estate.hosts("second", ["new.example.com"], at=now, status=200)


async def _scan(estate, name: str):
    return await estate.session.get(Scan, estate.scans[name])


async def _evaluate(estate, scan, *, query: str, fire_on: str, dimension: str = WEB):
    now = scan.completed_at
    return await estate.session.run_sync(
        lambda s: evaluate(
            s, dimension=dimension, query=query, fire_on=fire_on, scan=scan, now=now
        )
    )


def _tripwire(estate, **kwargs) -> Tripwire:
    row = Tripwire(
        project_id=estate.project_id,
        name=kwargs.pop("name", "VPN portals"),
        dimension=kwargs.pop("dimension", WEB),
        query=kwargs.pop("query", "status:200"),
        trigger=kwargs.pop("trigger", Trigger.SCAN_SETTLED.value),
        fire_on=kwargs.pop("fire_on", FireOn.APPEARS.value),
        scope_kind=kwargs.pop("scope_kind", ScopeKind.ALL.value),
        scope_ids=kwargs.pop("scope_ids", []),
        actions=kwargs.pop("actions", []),
        created_by=estate.user_id,
    )
    estate.session.add(row)
    return row


# ---------- fire modes ----------


async def test_a_first_scan_never_fires_and_a_later_one_fires_on_what_appeared(
    estate, now
):
    await _two_runs(estate, now)
    first = await _evaluate(
        estate, await _scan(estate, "first"), query="", fire_on=FireOn.APPEARS.value
    )
    assert first.status == CheckStatus.NO_BASELINE.value
    assert first.fired == []

    second = await _evaluate(
        estate, await _scan(estate, "second"), query="", fire_on=FireOn.APPEARS.value
    )
    assert second.status == CheckStatus.FIRED.value
    assert [r.key for r in second.fired] == ["new.example.com"]
    assert second.matched == 3
    assert second.fired[0].seed == "new.example.com"


async def test_becomes_true_fires_on_the_row_that_flipped_not_the_one_that_held(
    estate, now
):
    await _two_runs(estate, now)
    result = await _evaluate(
        estate,
        await _scan(estate, "second"),
        query="status:200",
        fire_on=FireOn.BECOMES_TRUE.value,
    )
    assert result.status == CheckStatus.FIRED.value
    assert sorted(r.key for r in result.fired) == ["new.example.com", "vpn.example.com"]
    assert result.matched == 3
    assert result.previous_scan_id == estate.scans["first"]


async def test_matches_fires_on_every_run_including_the_first(estate, now):
    await _two_runs(estate, now)
    result = await _evaluate(
        estate,
        await _scan(estate, "first"),
        query="status:200",
        fire_on=FireOn.MATCHES.value,
    )
    assert result.status == CheckStatus.FIRED.value
    assert [r.key for r in result.fired] == ["www.example.com"]
    assert result.matched == 1


async def test_a_dimension_the_run_did_not_scan_is_not_covered(estate, now):
    await _two_runs(estate, now)
    result = await _evaluate(
        estate,
        await _scan(estate, "second"),
        query="severity:critical",
        fire_on=FireOn.MATCHES.value,
        dimension=VULN,
    )
    assert result.status == CheckStatus.NOT_COVERED.value
    assert result.fired == []


async def test_a_quiet_run_is_recorded_as_not_fired(estate, now):
    await _two_runs(estate, now)
    result = await _evaluate(
        estate,
        await _scan(estate, "second"),
        query="host:nothing",
        fire_on=FireOn.APPEARS.value,
    )
    assert result.status == CheckStatus.QUIET.value
    assert result.matched == 0


# ---------- recording ----------


async def test_a_check_records_the_run_and_a_second_pass_does_not_fire_the_same_rows(
    estate, now, flush_only
):
    await _two_runs(estate, now)
    tripwire = _tripwire(estate, query="", fire_on=FireOn.APPEARS.value)
    await estate.session.flush()
    scan = await _scan(estate, "second")
    outcomes = [Outcome(kind="notify", status=OutcomeStatus.DONE.value, detail="Sent")]

    run = await estate.session.run_sync(
        lambda s: check(s, tripwire, scan, act=lambda *_a: outcomes)
    )
    assert run.status == CheckStatus.FIRED.value
    assert run.fired == 1
    assert run.matched == 3
    assert [r["key"] for r in run.rows] == ["new.example.com"]
    assert run.outcomes[0]["detail"] == "Sent"
    assert tripwire.fired_count == 1
    assert tripwire.last_fired_at is not None
    marks = (await estate.session.execute(select(TripwireMark.key))).scalars().all()
    assert marks == ["new.example.com"]

    calls: list[int] = []

    def act(_s, _t, _r, _scan, rows):
        calls.append(len(rows))
        return []

    again = await estate.session.run_sync(lambda s: check(s, tripwire, scan, act=act))
    assert again.id == run.id
    assert again.fired == 1
    assert calls == []
    assert tripwire.fired_count == 1
    total = (await estate.session.execute(select(TripwireRun))).scalars().all()
    assert len(total) == 1


async def test_a_query_the_grammar_refuses_is_recorded_as_an_error(
    estate, now, flush_only
):
    await _two_runs(estate, now)
    tripwire = _tripwire(estate, query="is:nosuchflag", fire_on=FireOn.MATCHES.value)
    await estate.session.flush()
    scan = await _scan(estate, "second")
    run = await estate.session.run_sync(lambda s: check(s, tripwire, scan))
    assert run.status == CheckStatus.ERROR.value
    assert "nosuchflag" in (run.detail or "")


async def test_a_live_pass_fires_once_per_row_and_the_settle_pass_adds_only_the_rest(
    estate, now, flush_only
):
    earlier = now - timedelta(days=3)
    await estate.scan("example.com", "first", at=earlier)
    await estate.hosts("first", ["www.example.com"], at=earlier, status=200)
    await estate.scan("example.com", "live", at=now, status="running")
    await estate.hosts("live", ["www.example.com", "a.example.com"], at=now, status=200)
    tripwire = _tripwire(
        estate,
        query="is:web",
        fire_on=FireOn.APPEARS.value,
        trigger=Trigger.SCAN_LIVE.value,
    )
    await estate.session.flush()
    scan = await _scan(estate, "live")

    seen: list[list[str]] = []

    def act(_s, _t, _r, _scan, rows):
        seen.append([r.key for r in rows])
        return []

    first = await estate.session.run_sync(lambda s: check(s, tripwire, scan, act=act))
    assert first.fired == 1
    await estate.hosts(
        "live", ["b.example.com"], at=now + timedelta(minutes=5), status=200
    )
    second = await estate.session.run_sync(lambda s: check(s, tripwire, scan, act=act))
    assert second.id == first.id
    assert second.fired == 2
    assert seen == [["a.example.com"], ["b.example.com"]]
    assert tripwire.fired_count == 1


# ---------- scope ----------


async def test_only_tripwires_whose_scope_holds_the_target_apply(estate, now):
    await _two_runs(estate, now)
    other = await estate.target("other.com")
    tag = Tag(
        id=uuid.uuid4(),
        name="production",
        slug="production",
        color="#6B7280",
        project_id=estate.project_id,
        created_by=estate.user_id,
    )
    estate.session.add(tag)
    estate.session.add(
        TargetTag(target_id=estate.targets["example.com"], tag_id=tag.id)
    )
    _tripwire(estate, name="every")
    _tripwire(
        estate,
        name="mine",
        scope_kind=ScopeKind.TARGETS.value,
        scope_ids=[str(estate.targets["example.com"])],
    )
    theirs = _tripwire(
        estate,
        name="theirs",
        scope_kind=ScopeKind.TARGETS.value,
        scope_ids=[str(other)],
    )
    _tripwire(
        estate, name="tagged", scope_kind=ScopeKind.TAG.value, scope_ids=[str(tag.id)]
    )
    paused = _tripwire(estate, name="paused")
    paused.enabled = False
    _tripwire(estate, name="live", trigger=Trigger.SCAN_LIVE.value)
    await estate.session.flush()
    scan = await _scan(estate, "second")

    settled = await estate.session.run_sync(lambda s: applicable(s, scan))
    assert sorted(t.name for t in settled) == ["every", "live", "mine", "tagged"]
    assert theirs not in settled

    during = await estate.session.run_sync(
        lambda s: applicable(s, scan, live_dimension=WEB)
    )
    assert [t.name for t in during] == ["live"]


# ---------- the service ----------


async def test_a_query_the_grammar_refuses_is_not_stored(estate, flush_only):
    service = TripwireService(estate.session)
    with pytest.raises(TripwireError):
        await service.create(
            TripwireCreate(name="Bad", dimension=WEB, query="is:nosuchflag"),
            estate.project_id,
            estate.user_id,
        )


def test_an_empty_query_is_refused_before_it_reaches_the_service():
    with pytest.raises(ValidationError):
        TripwireCreate(name="Blank", dimension=WEB, query="   ")
    with pytest.raises(ValidationError):
        TripwireUpdate(query="")
    assert TripwireUpdate(query=" is:web ").query == "is:web"


async def test_scope_ids_must_belong_to_the_project(estate, flush_only):
    service = TripwireService(estate.session)
    with pytest.raises(TripwireError):
        await service.create(
            TripwireCreate(
                name="Elsewhere",
                dimension=WEB,
                query="is:web",
                scope=TripwireScope(kind=ScopeKind.TARGETS.value, ids=[uuid.uuid4()]),
            ),
            estate.project_id,
            estate.user_id,
        )


async def test_a_tripwire_round_trips_with_its_scope_labels_and_actions(
    estate, now, flush_only
):
    await _two_runs(estate, now)
    service = TripwireService(estate.session)
    created = await service.create(
        TripwireCreate(
            name="VPN portals answering 200",
            dimension=WEB,
            query="host:vpn status:200",
            fire_on=FireOn.BECOMES_TRUE.value,
            scope=TripwireScope(
                kind=ScopeKind.TARGETS.value, ids=[estate.targets["example.com"]]
            ),
            actions=[NotifyAction()],
        ),
        estate.project_id,
        estate.user_id,
    )
    assert created.scope.labels == ["example.com"]
    assert [a.kind for a in created.actions] == ["notify"]
    assert created.recent_fired == 0

    updated = await service.update(
        created.id,
        TripwireUpdate(enabled=False, query="  host:vpn  "),
        estate.project_id,
    )
    assert updated is not None
    assert updated.enabled is False
    assert updated.query == "host:vpn"
    assert (
        await service.update(
            uuid.uuid4(), TripwireUpdate(enabled=True), estate.project_id
        )
        is None
    )
    assert await service.delete(created.id, estate.project_id) is True
    assert await service.list(estate.project_id) == []


async def test_a_preview_reports_what_the_latest_run_would_have_fired(estate, now):
    await _two_runs(estate, now)
    service = TripwireService(estate.session)
    preview = await service.preview(
        TripwirePreviewRequest(dimension=WEB, query="", fire_on=FireOn.APPEARS.value),
        estate.project_id,
    )
    assert preview.error is None
    assert preview.fired == 1
    assert preview.matched == 3
    assert [r.label for r in preview.rows] == ["new.example.com"]
    assert [t.status for t in preview.targets] == [CheckStatus.FIRED.value]

    backtest = await service.backtest(
        TripwirePreviewRequest(
            dimension=WEB, query="status:200", fire_on=FireOn.BECOMES_TRUE.value
        ),
        estate.project_id,
    )
    assert backtest.error is None
    assert [(r.status, r.fired) for r in backtest.runs] == [
        (CheckStatus.FIRED.value, 2),
        (CheckStatus.NO_BASELINE.value, 0),
    ]

    refused = await service.preview(
        TripwirePreviewRequest(
            dimension=WEB, query="is:nosuchflag", fire_on=FireOn.MATCHES.value
        ),
        estate.project_id,
    )
    assert refused.error is not None
    assert refused.error.message == "Unknown flag 'nosuchflag'."
    assert refused.targets == []


# ---------- vocabulary ----------


def test_every_template_query_compiles_in_its_dimension():
    for template in TEMPLATES:
        validate_query(template.dimension, template.query)
        validate_query(template.dimension, appears_query(template.query))


def test_an_unknown_flag_is_refused_before_a_scan_is_read():
    with pytest.raises(QuerySyntaxError):
        validate_query(WEB, "is:nosuchflag")


def test_the_message_names_the_rows_and_takes_its_severity_from_them():
    payload = tripwire_fired(
        TripwireFired(
            name="Critical findings",
            target="example.com",
            dimension=VULN,
            fire_on=FireOn.APPEARS.value,
            fired=7,
            rows=[
                FiredRowLike("CVE-2024-3400", "critical · vpn.example.com", "critical")
            ]
            + [
                FiredRowLike(f"check-{i}", "high · www.example.com", "high")
                for i in range(6)
            ],
            run_id="run",
            scan_id="scan",
            live=True,
        )
    )
    assert payload["title"] == "Tripwire · Critical findings"
    assert payload["severity"] == NotificationSeverity.ERROR
    lines = payload["message"].split("\n")
    assert lines[0] == "7 findings appeared on example.com · scan running"
    assert lines[1] == "CVE-2024-3400 · critical · vpn.example.com"
    assert lines[-1] == "and 2 more"
    assert payload["metadata"]["url"] == "/tripwires?run=run"


# ---------- delivery ----------


async def test_the_notify_outcome_reports_what_each_channel_did(estate):
    good = NotificationChannel(
        name="Ops",
        provider="webhook",
        config_encrypted="",
        events={"types": ["tripwire"], "min_severity": "info"},
        created_by=estate.user_id,
    )
    bad = NotificationChannel(
        name="Old Slack",
        provider="slack",
        config_encrypted="",
        events={"types": ["tripwire"], "min_severity": "info"},
        created_by=estate.user_id,
    )
    estate.session.add_all([good, bad])
    await estate.session.flush()

    mixed = await estate.session.run_sync(
        lambda s: delivery_outcome(
            s, [(good.id, True, ""), (bad.id, False, "Connection refused")], chosen=True
        )
    )
    assert mixed.status == OutcomeStatus.DONE.value
    assert mixed.detail == "Sent to 1 channel · 1 channel failed: Old Slack"

    none_delivered = await estate.session.run_sync(
        lambda s: delivery_outcome(s, [(bad.id, False, "timeout")], chosen=True)
    )
    assert none_delivered.status == OutcomeStatus.FAILED.value
    assert none_delivered.detail == "1 channel failed: Old Slack"

    nobody = await estate.session.run_sync(
        lambda s: delivery_outcome(s, [], chosen=False)
    )
    assert nobody.status == OutcomeStatus.DONE.value
    assert nobody.detail == "No channel subscribed to Tripwires. Recorded in the app."
