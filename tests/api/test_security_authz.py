from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import get_current_superuser
from app.main import app
from app.services.note import NoteService
from app.services.scan import ScanService
from app.services.scan_context import ScanContextService
from app.services.scan_engine import ScanEngineService
from app.services.scan_schedule import ScanScheduleService
from shared.definitions.rescan import SeedKind
from shared.definitions.vulnerabilities import Protocol, Severity, TemplateOrigin
from shared.enums.scan_context import AuthType
from shared.enums.scan_schedule import ScheduleType
from shared.enums.target import TargetType
from shared.models.ip_address import IpAddress
from shared.models.note import NoteCreate, NoteUpdate
from shared.models.proxy import Proxy
from shared.models.scan import ScanCreate, SeedAsset
from shared.models.scan_context import (
    AuthConfig,
    ScanContext,
    ScanContextCreate,
    ScanContextUpdate,
)
from shared.models.scan_engine import ScanEngine, ScanEngineUpdate
from shared.models.scan_schedule import ScanScheduleCreate, ScanScheduleUpdate
from shared.models.target import Target
from shared.models.user import User
from shared.models.vuln_template import TemplateSelection, VulnTemplate
from shared.services import target_seeds
from shared.services.credential_access import (
    context_carries_credentials,
    engine_carries_credentials,
    launch_refusal,
)
from shared.services.scan_factory import ScanFactoryError, build_scan_for_target_sync
from shared.services.vuln_templates import picked_predicate
from shared.utils.crypto import encrypt_secret

pytestmark = pytest.mark.api

API = "/api/v1"


@pytest.fixture
def flush_only(session, monkeypatch):
    monkeypatch.setattr(session, "commit", session.flush)
    return session


async def _user(session, *, superuser: bool = False) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"u{tag}",
        email=f"u{tag}@test.local",
        hashed_password="x",
        is_superuser=superuser,
    )
    session.add(user)
    await session.flush()
    return user


def _route(method: str, path: str):
    for route in app.routes:
        if getattr(route, "path", None) == API + path and method in route.methods:
            return route
    msg = f"{method} {path} is not routed"
    raise AssertionError(msg)


def _admin_only(method: str, path: str) -> bool:
    stack = [_route(method, path).dependant]
    while stack:
        dependant = stack.pop()
        if dependant.call is get_current_superuser:
            return True
        stack.extend(dependant.dependencies)
    return False


# ---------- E1, E3, E4: routes ----------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/vuln-templates/sync"),
        ("POST", "/vuln-templates/upload"),
        ("PATCH", "/vuln-templates/{template_id}"),
        ("PUT", "/vuln-templates/{template_id}/source"),
        ("DELETE", "/vuln-templates/{template_id}"),
        ("POST", "/reports/themes"),
        ("DELETE", "/reports/themes/{slug}"),
        ("POST", "/reports/fonts"),
        ("DELETE", "/reports/fonts/{slug}"),
        ("POST", "/wordlists"),
        ("DELETE", "/wordlists/{wordlist_id}"),
    ],
)
def test_a_shared_library_write_needs_an_administrator(method, path):
    assert _admin_only(method, path)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/vuln-templates/search"),
        ("POST", "/vuln-templates/selection"),
        ("GET", "/vuln-templates/{template_id}/source"),
        ("GET", "/wordlists"),
        ("GET", "/reports/themes/{slug}/source"),
    ],
)
def test_reading_a_shared_library_stays_open(method, path):
    assert not _admin_only(method, path)


def test_rule_suggestions_are_never_a_get():
    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", ())
        if getattr(route, "path", "").endswith("/suggestions")
    }
    assert paths == {("POST", f"{API}/interest/scan/{{scan_id}}/suggestions")}


# ---------- E1: checks picked by id ----------


async def test_a_check_picked_by_id_obeys_the_protocol_exclusions(session):
    tag = uuid.uuid4().hex[:8]
    rows = {
        protocol: VulnTemplate(
            origin=TemplateOrigin.CUSTOM.value,
            template_id=f"{protocol}-{tag}",
            path=f"custom/{protocol}-{tag}.yaml",
            name=protocol,
            severity=Severity.HIGH.value,
            protocol=protocol,
        )
        for protocol in (
            Protocol.HTTP.value,
            Protocol.FILE.value,
            Protocol.HEADLESS.value,
        )
    }
    session.add_all(rows.values())
    await session.flush()

    async def picked(headless: bool) -> set[str]:
        selection = TemplateSelection(
            custom_templates=[row.id for row in rows.values()], headless=headless
        )
        found = await session.scalars(
            select(VulnTemplate.protocol).where(picked_predicate(selection))
        )
        return set(found.all())

    assert await picked(False) == {Protocol.HTTP.value}
    assert await picked(True) == {Protocol.HTTP.value, Protocol.HEADLESS.value}


# ---------- E2: notes ----------


async def _note(estate, author: uuid.UUID):
    target_id = await estate.target("example.com")
    return await NoteService(estate.session).create(
        NoteCreate(target_id=target_id, body="Login form takes any password"),
        estate.project_id,
        author,
    )


async def test_only_the_author_or_an_administrator_edits_a_note(estate, flush_only):
    author = await _user(flush_only)
    other = await _user(flush_only)
    admin = await _user(flush_only, superuser=True)
    note = await _note(estate, author.id)
    service = NoteService(flush_only)

    for change in (
        NoteUpdate(body="Rewritten"),
        NoteUpdate(title="Rewritten"),
        NoteUpdate(tags=["noise"]),
    ):
        with pytest.raises(HTTPException) as refused:
            await service.update(note.id, change, estate.project_id, other)
        assert refused.value.status_code == 403
    with pytest.raises(HTTPException) as refused:
        await service.delete(note.id, estate.project_id, other)
    assert refused.value.status_code == 403

    mine = await service.update(
        note.id, NoteUpdate(body="Checked"), estate.project_id, author
    )
    assert mine.body == "Checked"
    theirs = await service.update(
        note.id, NoteUpdate(body="Confirmed"), estate.project_id, admin
    )
    assert theirs.body == "Confirmed"


async def test_any_member_resolves_a_note(estate, flush_only):
    author = await _user(flush_only)
    other = await _user(flush_only)
    note = await _note(estate, author.id)

    resolved = await NoteService(flush_only).update(
        note.id, NoteUpdate(status="resolved"), estate.project_id, other
    )
    assert resolved.status == "resolved"


async def test_an_administrator_deletes_any_note(estate, flush_only):
    author = await _user(flush_only)
    admin = await _user(flush_only, superuser=True)
    note = await _note(estate, author.id)

    await NoteService(flush_only).delete(note.id, estate.project_id, admin)


# ---------- E5: proxy on a context ----------


async def _proxy(session, owner: uuid.UUID, *, default: bool) -> Proxy:
    proxy = Proxy(
        name=f"proxy-{uuid.uuid4().hex[:6]}",
        is_active=True,
        is_default=default,
        endpoints_encrypted=encrypt_secret(
            json.dumps([{"scheme": "http", "host": "10.0.0.9", "port": 3128}])
        ),
        endpoint_count=1,
        created_by=owner,
    )
    session.add(proxy)
    await session.flush()
    return proxy


async def test_a_member_cannot_choose_a_proxy(estate, flush_only):
    member = await _user(flush_only)
    fallback = await _proxy(flush_only, estate.user_id, default=True)
    chosen = await _proxy(flush_only, estate.user_id, default=False)
    contexts = ScanContextService(flush_only)

    for proxy_id in (chosen.id, None):
        with pytest.raises(HTTPException) as refused:
            await contexts.create(
                estate.project_id,
                member.id,
                ScanContextCreate(name="mine", proxy_id=proxy_id),
                actor=member,
            )
        assert refused.value.status_code == 403

    implied = await contexts.create(
        estate.project_id, member.id, ScanContextCreate(name="mine"), actor=member
    )
    assert implied.proxy_id == fallback.id

    with pytest.raises(HTTPException) as refused:
        await contexts.update(
            implied.id,
            estate.project_id,
            ScanContextUpdate(proxy_id=chosen.id),
            actor=member,
        )
    assert refused.value.status_code == 403

    renamed = await contexts.update(
        implied.id,
        estate.project_id,
        ScanContextUpdate(name="renamed", proxy_id=fallback.id),
        actor=member,
    )
    assert (renamed.name, renamed.proxy_id) == ("renamed", fallback.id)


async def test_an_administrator_chooses_any_proxy(estate, flush_only):
    admin = await _user(flush_only, superuser=True)
    await _proxy(flush_only, estate.user_id, default=True)
    chosen = await _proxy(flush_only, estate.user_id, default=False)
    contexts = ScanContextService(flush_only)

    made = await contexts.create(
        estate.project_id,
        admin.id,
        ScanContextCreate(name="routed", proxy_id=chosen.id),
        actor=admin,
    )
    assert made.proxy_id == chosen.id


# ---------- E6: credential-bearing contexts and engines ----------


def _context(project_id, owner, **fields) -> ScanContext:
    return ScanContext(project_id=project_id, created_by=owner, name="ctx", **fields)


def _engine(project_id, owner, **fields) -> ScanEngine:
    return ScanEngine(project_id=project_id, created_by=owner, name="eng", **fields)


def test_what_carries_credentials():
    pid, owner = uuid.uuid4(), uuid.uuid4()
    assert not context_carries_credentials(_context(pid, owner))
    assert context_carries_credentials(
        _context(pid, owner, auth_type=AuthType.BEARER.value)
    )
    assert context_carries_credentials(
        _context(pid, owner, extra_headers=[{"name": "X-Team", "value": "red"}])
    )
    plain = _engine(pid, owner, tool_options={"nuclei": "-tags cve"})
    assert not engine_carries_credentials(plain)
    assert engine_carries_credentials(
        _engine(pid, owner, global_headers=["X-Team: red"])
    )
    assert engine_carries_credentials(
        _engine(pid, owner, tool_options={"nuclei": "-H 'Authorization: Bearer x'"})
    )


def test_only_the_creator_or_an_administrator_launches_with_credentials():
    pid, owner, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    context = _context(pid, owner, auth_type=AuthType.COOKIE.value)
    engine = _engine(pid, owner, global_headers=["Cookie: sid=1"])

    refused = launch_refusal(
        engine=None, context=context, user_id=other, superuser=False
    )
    assert refused == (
        "Context ctx carries credentials. "
        "Its creator or an administrator can launch with it."
    )
    assert launch_refusal(engine=engine, context=None, user_id=other, superuser=False)
    for user_id, superuser in ((owner, False), (other, True)):
        assert (
            launch_refusal(
                engine=engine, context=context, user_id=user_id, superuser=superuser
            )
            is None
        )


async def _secret_context(session, project_id, owner) -> ScanContext:
    ctx = ScanContext(
        project_id=project_id,
        created_by=owner,
        name="prod session",
        auth_type=AuthType.BEARER.value,
        auth={"auth_type": AuthType.BEARER.value, "bearer_token": "tok-123"},
        extra_headers=[{"name": "X-Tenant", "value": "acme"}],
    )
    session.add(ctx)
    await session.flush()
    return ctx


async def test_a_context_with_credentials_is_changed_by_its_creator(estate, flush_only):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    ctx = await _secret_context(flush_only, estate.project_id, owner.id)
    contexts = ScanContextService(flush_only)

    with pytest.raises(HTTPException) as refused:
        await contexts.update(
            ctx.id, estate.project_id, ScanContextUpdate(name="x"), actor=other
        )
    assert refused.value.status_code == 403
    with pytest.raises(HTTPException) as refused:
        await contexts.delete(ctx.id, estate.project_id, actor=other)
    assert refused.value.status_code == 403

    updated = await contexts.update(
        ctx.id, estate.project_id, ScanContextUpdate(name="prod"), actor=owner
    )
    assert updated.name == "prod"
    assert updated.carries_credentials


async def test_a_member_cannot_add_credentials_to_another_context(estate, flush_only):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    plain = ScanContext(project_id=estate.project_id, created_by=owner.id, name="p")
    flush_only.add(plain)
    await flush_only.flush()

    with pytest.raises(HTTPException) as refused:
        await ScanContextService(flush_only).update(
            plain.id,
            estate.project_id,
            ScanContextUpdate(
                auth_type=AuthType.BEARER.value,
                auth=AuthConfig(auth_type=AuthType.BEARER.value, bearer_token="t"),
            ),
            actor=other,
        )
    assert refused.value.status_code == 403


async def test_a_copy_by_another_member_leaves_the_secrets_behind(estate, flush_only):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    ctx = await _secret_context(flush_only, estate.project_id, owner.id)
    contexts = ScanContextService(flush_only)

    copied = await contexts.duplicate(ctx.id, estate.project_id, other.id, actor=other)
    stored = await flush_only.get(ScanContext, copied.id)
    assert stored.auth_type == AuthType.NONE.value
    assert stored.extra_headers == []
    assert "tok-123" not in json.dumps(stored.auth)
    assert not copied.carries_credentials

    own = await contexts.duplicate(ctx.id, estate.project_id, owner.id, actor=owner)
    kept = await flush_only.get(ScanContext, own.id)
    assert kept.auth["bearer_token"] == "tok-123"


async def test_an_engine_with_credentials_is_changed_and_copied_by_its_creator(
    estate, flush_only
):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    engine = ScanEngine(
        project_id=estate.project_id,
        created_by=owner.id,
        name="authed",
        global_headers=["Authorization: Bearer abc"],
        tool_options={
            "nuclei": "-H 'X-Api-Key: secret-1'",
            "httpx": "-follow-redirects",
        },
    )
    flush_only.add(engine)
    await flush_only.flush()
    engines = ScanEngineService(flush_only)

    with pytest.raises(HTTPException) as refused:
        await engines.update(
            engine.id,
            estate.project_id,
            ScanEngineUpdate(name="mine"),
            actor_id=other.id,
        )
    assert refused.value.status_code == 403
    with pytest.raises(HTTPException) as refused:
        await engines.delete(engine.id, estate.project_id, actor_id=other.id)
    assert refused.value.status_code == 403

    copied = await engines.duplicate(engine.id, estate.project_id, other.id)
    stored = await flush_only.get(ScanEngine, copied.id)
    assert stored.global_headers == []
    assert stored.tool_options == {"httpx": "-follow-redirects"}
    assert not copied.carries_credentials


async def _launchable(estate, session, owner: User):
    target_id = await estate.target("example.com")
    ctx = await _secret_context(session, estate.project_id, owner.id)
    return target_id, ctx


@pytest.fixture
def no_dispatch(monkeypatch):
    monkeypatch.setattr(ScanService, "_dispatch_scan", lambda *_: None)


async def test_a_launch_with_another_members_context_is_refused(
    estate, flush_only, no_dispatch
):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    target_id, ctx = await _launchable(estate, flush_only, owner)
    scans = ScanService(flush_only)
    launch = ScanCreate(target_id=target_id, context_id=ctx.id)

    with pytest.raises(HTTPException) as refused:
        await scans.create(launch, estate.project_id, other.id)
    assert refused.value.status_code == 403
    assert "prod session carries credentials" in refused.value.detail

    started = await scans.create(launch, estate.project_id, owner.id)
    assert started.context_id == ctx.id


async def test_a_rescan_reuses_its_runs_context_on_the_targets_own_assets(
    estate, flush_only, no_dispatch, now
):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    target_id, ctx = await _launchable(estate, flush_only, owner)
    await estate.scan("example.com", "census", at=now - timedelta(hours=1))
    await estate.hosts("census", ["api.example.com"], at=now)
    scans = ScanService(flush_only)

    def rescan(value: str) -> ScanCreate:
        return ScanCreate(
            target_id=target_id,
            context_id=ctx.id,
            seed_assets=[SeedAsset(kind=SeedKind.HOST.value, value=value)],
        )

    started = await scans.create(
        rescan("api.example.com"), estate.project_id, other.id, reused_context=True
    )
    assert started.context_id == ctx.id

    with pytest.raises(HTTPException) as refused:
        await scans.create(
            rescan("collector.attacker.test"),
            estate.project_id,
            other.id,
            reused_context=True,
        )
    assert refused.value.status_code == 400
    assert "collector.attacker.test" in refused.value.detail


async def test_a_schedule_with_another_members_context_is_refused(estate, flush_only):
    owner = await _user(flush_only)
    other = await _user(flush_only)
    target_id, ctx = await _launchable(estate, flush_only, owner)
    plain = ScanContext(project_id=estate.project_id, created_by=other.id, name="p")
    engine = ScanEngine(project_id=estate.project_id, created_by=owner.id, name="e")
    flush_only.add_all([plain, engine])
    await flush_only.flush()
    schedules = ScanScheduleService(flush_only)

    def plan(context_id) -> ScanScheduleCreate:
        return ScanScheduleCreate(
            name="nightly",
            target_ids=[target_id],
            engine_id=engine.id,
            context_id=context_id,
            schedule_type=ScheduleType.INTERVAL.value,
            interval_every=1,
            interval_unit="days",
        )

    with pytest.raises(HTTPException) as refused:
        await schedules.create(plan(ctx.id), estate.project_id, other.id)
    assert refused.value.status_code == 403

    mine = await schedules.create(plan(plain.id), estate.project_id, other.id)
    with pytest.raises(HTTPException) as refused:
        await schedules.update(
            mine.id,
            estate.project_id,
            ScanScheduleUpdate(context_id=ctx.id),
            actor_id=other.id,
        )
    assert refused.value.status_code == 403

    def fire(session):
        return build_scan_for_target_sync(
            session,
            project_id=estate.project_id,
            target_id=target_id,
            engine_id=engine.id,
            context_id=ctx.id,
            created_by=other.id,
        )

    with pytest.raises(ScanFactoryError, match="carries credentials"):
        await flush_only.run_sync(fire)


# ---------- E7: launch seeds ----------


async def _target(session, project_id, owner, value: str, kind: TargetType):
    target = Target(
        project_id=project_id, target_value=value, target_type=kind, created_by=owner
    )
    session.add(target)
    await session.flush()
    return target


def _seed(kind: SeedKind, value: str) -> dict:
    return {"kind": kind.value, "value": value}


async def test_a_launch_seed_must_belong_to_its_target(estate, now):
    await estate.scan("example.com", "census", at=now)
    await estate.hosts("census", ["api.example.com"], at=now)
    estate.session.add(
        IpAddress(
            scan_id=estate.scans["census"],
            target_id=estate.targets["example.com"],
            project_id=estate.project_id,
            ip="203.0.113.7",
            source="test",
        )
    )
    await estate.session.flush()
    target = await estate.session.get(Target, estate.targets["example.com"])

    async def refusal(*seeds):
        return await target_seeds.launch_refusal(estate.session, list(seeds), target)

    assert await refusal(_seed(SeedKind.HOST, "API.example.com")) is None
    assert await refusal(_seed(SeedKind.URL, "https://new.example.com/x")) is None
    assert await refusal(_seed(SeedKind.ADDRESS, "203.0.113.7")) is None
    assert await refusal(_seed(SeedKind.HOST, "evil.test")) == (
        "Seed evil.test not accepted. Not under example.com."
    )
    assert await refusal(_seed(SeedKind.ADDRESS, "198.51.100.1"))
    assert await refusal(_seed(SeedKind.URL, "https://evil.test/"))


async def test_an_address_target_takes_urls_on_its_own_addresses(estate):
    owner = estate.user_id
    single = await _target(
        estate.session, estate.project_id, owner, "192.0.2.10", TargetType.IP
    )
    network = await _target(
        estate.session, estate.project_id, owner, "AS64500", TargetType.ASN
    )

    async def refusal(target, *seeds):
        return await target_seeds.launch_refusal(estate.session, list(seeds), target)

    assert await refusal(single, _seed(SeedKind.URL, "http://192.0.2.10:8080/")) is None
    assert await refusal(single, _seed(SeedKind.URL, "http://192.0.2.11/"))
    assert await refusal(network, _seed(SeedKind.ADDRESS, "192.0.2.10"))
