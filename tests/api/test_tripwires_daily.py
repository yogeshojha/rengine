from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.services.infostealer import InfostealerService
from app.services.tripwire import TripwireError, TripwireService
from shared.definitions.notifications import FiredRowLike, TripwireLeak, tripwire_leak
from shared.definitions.surface import SurfaceDimension
from shared.definitions.tripwires import (
    SOURCES,
    TEMPLATES,
    CheckStatus,
    FireOn,
    OutcomeStatus,
    ScopeKind,
    Source,
    Trigger,
    clean_params,
)
from shared.enums.notification import NotificationSeverity
from shared.enums.target import TargetType
from shared.models.infostealer import InfostealerChange, InfostealerSighting
from shared.models.target import Target
from shared.models.tripwire import (
    DailyPreviewRequest,
    Outcome,
    Tripwire,
    TripwireCreate,
    TripwireRun,
    TripwireUpdate,
)
from shared.services import infostealer
from shared.services.tripwires import applicable
from shared.services.tripwires.daily import (
    check_changes,
    rise,
    rows_of,
    watched_targets,
    watching,
)
from tools.hudsonrock.models import InfostealerReport, LoginUrl

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value
LEAKS = Source.LEAKED_LOGINS.value


def _report(employees: int, users: int, logins: dict[tuple[str, str], int]):
    return InfostealerReport(
        domain="example.com",
        total=employees + users,
        employees=employees,
        users=users,
        logins=[
            LoginUrl(audience=audience, host=host, path="/login", credentials=n)
            for (audience, host), n in logins.items()
        ],
    )


async def _store(estate, target_id, report):
    change = await estate.session.run_sync(
        lambda s: infostealer.store(s, target_id, report)
    )
    await estate.session.flush()
    return change


def _tripwire(estate, **kwargs) -> Tripwire:
    row = Tripwire(
        project_id=estate.project_id,
        name=kwargs.pop("name", "New leaked logins"),
        dimension=WEB,
        query="",
        trigger=Trigger.DAILY.value,
        fire_on=FireOn.APPEARS.value,
        source=LEAKS,
        params=kwargs.pop("params", {"audience": "any"}),
        scope_kind=kwargs.pop("scope_kind", ScopeKind.ALL.value),
        scope_ids=kwargs.pop("scope_ids", []),
        actions=kwargs.pop("actions", []),
        created_by=estate.user_id,
    )
    estate.session.add(row)
    return row


BASE = {("employee", "sso.example.com"): 4, ("user", "shop.example.com"): 10}


# ---------- the diff ----------


async def test_a_first_lookup_is_a_baseline_and_records_no_change(estate):
    target = await estate.target("example.com")
    assert await _store(estate, target, _report(3, 20, BASE)) is None
    seen = (await estate.session.scalars(select(InfostealerSighting))).all()
    assert {(s.audience, s.host, s.credentials_peak) for s in seen} == {
        ("employee", "sso.example.com", 4),
        ("user", "shop.example.com", 10),
    }


async def test_an_unchanged_lookup_records_no_change(estate):
    target = await estate.target("example.com")
    await _store(estate, target, _report(3, 20, BASE))
    assert await _store(estate, target, _report(3, 20, BASE)) is None


async def test_a_rise_records_the_counts_and_the_hosts_that_moved(estate):
    target = await estate.target("example.com")
    await _store(estate, target, _report(3, 20, BASE))
    change = await _store(
        estate,
        target,
        _report(
            5,
            20,
            {
                ("employee", "sso.example.com"): 6,
                ("employee", "vpn.example.com"): 2,
                ("user", "shop.example.com"): 10,
            },
        ),
    )
    assert (change.employees_from, change.employees_to) == (3, 5)
    assert (change.users_from, change.users_to) == (20, 20)
    assert change.previous_checked_at is not None
    assert {
        (h["host"], h["credentials_from"], h["credentials_to"], h["new"])
        for h in change.hosts
    } == {
        ("sso.example.com", 4, 6, False),
        ("vpn.example.com", 0, 2, True),
    }


async def test_a_count_that_dips_and_returns_is_not_a_change(estate):
    target = await estate.target("example.com")
    await _store(estate, target, _report(3, 20, BASE))
    assert await _store(estate, target, _report(2, 18, {})) is None
    assert await _store(estate, target, _report(3, 20, BASE)) is None


# ---------- rows ----------


def _change(**kwargs) -> InfostealerChange:
    return InfostealerChange(
        employees_from=3,
        employees_to=5,
        users_from=20,
        users_to=21,
        hosts=[
            {
                "audience": "employee",
                "host": "vpn.example.com",
                "credentials_from": 0,
                "credentials_to": 2,
                "new": True,
            },
            {
                "audience": "user",
                "host": "shop.example.com",
                "credentials_from": 10,
                "credentials_to": 12,
                "new": False,
            },
        ],
        **kwargs,
    )


def test_rows_put_counts_first_and_only_hosts_carry_a_seed():
    rows = rows_of(_change())
    assert [r.key for r in rows] == [
        "employees",
        "users",
        "employee|vpn.example.com",
        "user|shop.example.com",
    ]
    assert rows[0].detail == "3 to 5"
    assert rows[2].detail == "Employees · 2 credentials · first listed"
    assert rows[3].detail == "Users · 10 to 12 credentials"
    assert [r.seed for r in rows] == [None, None, "vpn.example.com", "shop.example.com"]


def test_an_audience_narrows_the_rows_and_the_rise():
    change = _change()
    assert [r.key for r in rows_of(change, {"audience": "user"})] == [
        "users",
        "user|shop.example.com",
    ]
    assert rise(change, {"audience": "user"}) == (0, 1)
    assert rise(change, {"audience": "any"}) == (2, 1)


# ---------- checks ----------


async def _rise(estate, name: str = "example.com"):
    target = await estate.target(name)
    await _store(estate, target, _report(3, 20, BASE))
    await _store(
        estate, target, _report(4, 20, {**BASE, ("employee", "vpn.example.com"): 1})
    )
    return target


async def test_a_change_fires_each_watching_tripwire_once(estate, flush_only):
    target = await _rise(estate)
    tripwire = _tripwire(estate)
    await estate.session.flush()
    acted: list[int] = []

    def act(_s, _tripwire, _run, _target, _change, rows):
        acted.append(len(rows))
        return [Outcome(kind="notify", status=OutcomeStatus.DONE.value, detail="Sent")]

    runs = await estate.session.run_sync(lambda s: check_changes(s, act=act))
    assert [(r.status, r.fired, r.scan_id) for r in runs] == [
        (CheckStatus.FIRED.value, 2, None)
    ]
    assert runs[0].target_id == target
    assert runs[0].outcomes[0]["detail"] == "Sent"
    assert acted == [2]
    assert tripwire.fired_count == 1

    again = await estate.session.run_sync(lambda s: check_changes(s, act=act))
    assert again == []
    assert acted == [2]


async def test_a_change_outside_the_audience_is_recorded_as_not_fired(
    estate, flush_only
):
    await _rise(estate)
    _tripwire(estate, params={"audience": "user"})
    await estate.session.flush()
    runs = await estate.session.run_sync(lambda s: check_changes(s))
    assert [(r.status, r.fired, r.matched) for r in runs] == [
        (CheckStatus.QUIET.value, 0, 2)
    ]


async def test_only_tripwires_whose_scope_holds_the_target_watch_it(estate):
    inside = await estate.target("example.com")
    outside = await estate.target("example.org")
    scoped = _tripwire(
        estate, scope_kind=ScopeKind.TARGETS.value, scope_ids=[str(inside)]
    )
    paused = _tripwire(estate, name="Paused")
    paused.enabled = False
    await estate.session.flush()

    def read(sync):
        return (
            [t.id for t in watching(sync, sync.get(Target, inside))],
            [t.id for t in watching(sync, sync.get(Target, outside))],
            watched_targets(sync),
        )

    held, missed, watched = await estate.session.run_sync(read)
    assert held == [scoped.id]
    assert missed == []
    assert watched == {inside}


async def test_a_scan_never_checks_a_daily_tripwire(estate, now):
    await estate.scan("example.com", "first", at=now)
    _tripwire(estate)
    await estate.session.flush()
    from shared.models.scan import Scan  # noqa: PLC0415

    scan = await estate.session.get(Scan, estate.scans["first"])
    assert await estate.session.run_sync(lambda s: applicable(s, scan)) == []


# ---------- stored shape ----------


def test_a_daily_tripwire_needs_a_source_and_takes_no_query():
    with pytest.raises(ValidationError):
        TripwireCreate(name="x", dimension=WEB, trigger=Trigger.DAILY.value)
    with pytest.raises(ValidationError):
        TripwireCreate(
            name="x",
            dimension=WEB,
            trigger=Trigger.DAILY.value,
            source=LEAKS,
            params={"audience": "nobody"},
        )
    made = TripwireCreate(
        name="x",
        dimension=SurfaceDimension.VULNERABILITIES.value,
        query="severity:critical",
        fire_on=FireOn.MATCHES.value,
        trigger=Trigger.DAILY.value,
        source=LEAKS,
    )
    assert made.query == ""
    assert made.dimension == SOURCES[LEAKS].dimension
    assert made.fire_on == FireOn.APPEARS.value
    assert made.params == {"audience": "any"}


def test_a_scan_tripwire_drops_a_source():
    made = TripwireCreate(name="x", dimension=WEB, query="status:200", source=LEAKS)
    assert made.source is None
    assert made.params == {}


def test_unknown_settings_are_refused():
    with pytest.raises(ValueError, match="Unknown setting"):
        clean_params(LEAKS, {"audience": "any", "extra": "1"})


async def test_a_daily_tripwire_round_trips_and_an_update_keeps_its_shape(
    estate, flush_only
):
    service = TripwireService(estate.session)
    made = await service.create(
        TripwireCreate(
            name="Leaks",
            dimension=WEB,
            trigger=Trigger.DAILY.value,
            source=LEAKS,
            params={"audience": "employee"},
        ),
        estate.project_id,
        estate.user_id,
    )
    assert (made.trigger, made.source, made.params) == (
        Trigger.DAILY.value,
        LEAKS,
        {"audience": "employee"},
    )
    renamed = await service.update(
        made.id, TripwireUpdate(name="Staff leaks"), estate.project_id
    )
    assert (renamed.name, renamed.source) == ("Staff leaks", LEAKS)
    moved = await service.update(
        made.id, TripwireUpdate(params={"audience": "user"}), estate.project_id
    )
    assert moved.params == {"audience": "user"}
    with pytest.raises(TripwireError):
        await service.update(
            made.id,
            TripwireUpdate(trigger=Trigger.SCAN_SETTLED.value),
            estate.project_id,
        )
    scanned = await service.update(
        made.id,
        TripwireUpdate(trigger=Trigger.SCAN_SETTLED.value, query="status:200"),
        estate.project_id,
    )
    assert (scanned.source, scanned.params, scanned.query) == (None, {}, "status:200")


def test_every_daily_template_names_a_source():
    daily = [t for t in TEMPLATES if t.trigger == Trigger.DAILY.value]
    assert daily
    assert all(t.source in SOURCES and t.query == "" for t in daily)


# ---------- reads ----------


async def test_the_preview_counts_the_targets_read_and_lists_recent_changes(
    estate, flush_only
):
    await _rise(estate)
    await estate.target("203.0.113.9", TargetType.IP)
    service = TripwireService(estate.session)
    preview = await service.daily_preview(
        DailyPreviewRequest(source=LEAKS), estate.project_id
    )
    assert (preview.targets, preview.read, preview.reported) == (2, 1, 1)
    assert [(c.target_value, c.fired) for c in preview.changes] == [("example.com", 2)]
    users = await service.daily_preview(
        DailyPreviewRequest(source=LEAKS, params={"audience": "user"}),
        estate.project_id,
    )
    assert users.changes == []


async def test_the_report_carries_its_changes_first_seen_and_watchers(
    estate, flush_only
):
    target = await _rise(estate)
    tripwire = _tripwire(estate)
    await estate.session.flush()
    report = await InfostealerService(estate.session).report(target)
    assert [(c.employees_from, c.employees_to) for c in report.changes] == [(3, 4)]
    assert [w.id for w in report.watchers] == [tripwire.id]
    first = {h.host: h.first_seen for h in report.hosts}
    assert first["vpn.example.com"] == report.changes[0].checked_at
    assert first["sso.example.com"] < report.changes[0].checked_at


# ---------- the message ----------


def test_the_message_leads_with_employees_and_warns():
    payload = tripwire_leak(
        TripwireLeak(
            name="Leaks",
            target="example.com",
            employees=2,
            users=1,
            hosts=[FiredRowLike("vpn.example.com", "Employees · 2 credentials")],
            run_id="r",
            target_id="t",
        )
    )
    assert payload["severity"] is NotificationSeverity.WARNING
    assert payload["message"].split("\n") == [
        "2 more compromised employees on example.com",
        "1 more compromised user",
        "vpn.example.com · Employees · 2 credentials",
    ]
    assert payload["metadata"]["url"].endswith("run=r")


def test_a_host_only_change_names_the_hostnames():
    payload = tripwire_leak(
        TripwireLeak(
            name="Leaks",
            target="example.com",
            employees=0,
            users=0,
            hosts=[FiredRowLike("shop.example.com", "Users · 10 to 12 credentials")],
            run_id="r",
            target_id="t",
        )
    )
    assert payload["severity"] is NotificationSeverity.INFO
    assert payload["message"].startswith(
        "1 hostname with more leaked logins on example.com"
    )


async def test_a_run_row_of_a_daily_check_reads_back_without_a_scan(estate, flush_only):
    await _rise(estate)
    tripwire = _tripwire(estate)
    await estate.session.flush()
    await estate.session.run_sync(lambda s: check_changes(s))
    service = TripwireService(estate.session)
    rows = (await estate.session.scalars(select(TripwireRun))).all()
    reads = await service.run_reads(list(rows))
    assert [(r.scan_id, r.event_id is not None, r.target_value) for r in reads] == [
        (None, True, "example.com")
    ]
    counts = await service.counts(tripwire.id, estate.project_id)
    assert (counts.fired, counts.total) == (1, 1)


async def test_a_started_rescan_holds_the_leak_message_until_its_result(
    estate, now, flush_only, monkeypatch
):
    from shared.definitions.tripwires import TRIPWIRE_KEY  # noqa: PLC0415
    from shared.models.scan import Scan  # noqa: PLC0415
    from shared.services.tripwires import actions  # noqa: PLC0415

    await estate.scan("example.com", "census", at=now)
    await _rise(estate)
    tripwire = _tripwire(
        estate,
        actions=[
            {"kind": "notify", "channel_ids": []},
            {"kind": "scan", "stages": ["http_probe"], "intensity": None},
        ],
    )
    await estate.session.flush()
    sent: list[dict] = []
    seeded: list[list[dict]] = []

    def record(*_args, **kwargs):
        sent.append(kwargs)
        return Outcome(kind="notify", status=OutcomeStatus.DONE.value)

    def start(_s, _tripwire, _run, scan, seeds, _action):
        seeded.append(seeds)
        assert scan.id == estate.scans["census"]
        return Outcome(kind="scan", status=OutcomeStatus.DONE.value)

    monkeypatch.setattr(actions, "notify_leak", record)
    monkeypatch.setattr(actions, "start_run", start)
    runs = await estate.session.run_sync(
        lambda s: check_changes(s, act=actions.run_leak_actions)
    )
    assert sent == []
    assert [o["kind"] for o in runs[0].outcomes] == ["scan"]
    assert [[seed["value"] for seed in seeds] for seeds in seeded] == [
        ["vpn.example.com"]
    ]

    rescan_id = await estate.scan(
        "example.com",
        "rescan",
        at=now,
        scope="focused",
        config={
            TRIPWIRE_KEY: {"tripwire_id": str(tripwire.id), "run_id": str(runs[0].id)}
        },
    )
    rescan = await estate.session.get(Scan, rescan_id)
    await estate.session.run_sync(lambda s: actions.settle_run(s, rescan))
    assert len(sent) == 1
    assert sent[0]["rescan"].completed is True


async def test_a_rescan_of_a_target_with_no_completed_scan_is_skipped(
    estate, flush_only, monkeypatch
):
    from shared.definitions.tripwires import DAILY_NOT_SCANNED  # noqa: PLC0415
    from shared.services.tripwires import actions  # noqa: PLC0415

    await _rise(estate)
    _tripwire(
        estate, actions=[{"kind": "scan", "stages": ["http_probe"], "intensity": None}]
    )
    await estate.session.flush()
    runs = await estate.session.run_sync(
        lambda s: check_changes(s, act=actions.run_leak_actions)
    )
    assert [(o["status"], o["detail"]) for o in runs[0].outcomes] == [
        (OutcomeStatus.SKIPPED.value, DAILY_NOT_SCANNED)
    ]
