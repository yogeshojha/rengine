"""Project access: the rule, its dependencies, and a walk of every route as a member of another project."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import column, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api import access as access_api
from app.api.deps import (
    get_current_superuser,
    get_current_user,
    get_stream_user,
)
from app.config import API_V1_PREFIX, settings
from app.core import database
from app.core.database import get_session
from app.main import app
from shared.models.project_member import ProjectMember
from shared.models.target import Target
from shared.models.user import User
from shared.services import celery_dispatch
from shared.services.project_access import (
    EVERY_PROJECT,
    may_create_projects,
    may_open,
    member_projects,
    member_projects_sync,
    narrowed,
    project_clause,
    project_ids,
    replace_members,
    scoped,
)
from shared.utils.datetime import utc_now
from tests.api.route_table import calls, routes
from tests.conftest import Estate, _truncate, ask_threads

pytestmark = pytest.mark.api

WORD = "qzcanary"
REFUSED = frozenset({401, 403, 404, 422})
TIMEOUT_SECONDS = 20

# ---------- classification ----------

# routes that read no project row at all
INSTANCE: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/"),
        ("GET", "/auth/me"),
        ("POST", "/projects"),
        ("POST", "/auth/change-password"),
        ("POST", "/auth/change-username"),
        ("GET", "/auth/2fa/status"),
        ("POST", "/auth/2fa/setup"),
        ("POST", "/auth/2fa/verify"),
        ("POST", "/auth/2fa/disable"),
        ("GET", "/about"),
        ("GET", "/health/health"),
        ("GET", "/surface/schemas"),
        ("GET", "/engines/catalog"),
        ("GET", "/scans/rescan/schema"),
        ("GET", "/interest/catalog"),
        ("GET", "/tripwires/catalog"),
        ("GET", "/toolbox/catalog"),
        ("GET", "/datasets"),
        ("GET", "/wordlists"),
        ("GET", "/wordlists/{wordlist_id}/preview"),
        ("GET", "/vuln-templates/{template_id}/source"),
        ("GET", "/reports/catalog"),
        ("GET", "/reports/themes/{slug}/source"),
        ("GET", "/ai/catalog"),
        ("GET", "/ai/status"),
        ("GET", "/ai/calls"),
        ("GET", "/ai/connections"),
        ("GET", "/onboarding/status"),
        ("GET", "/instance-settings"),
        ("GET", "/mcp/status"),
        ("GET", "/mcp/tools"),
        ("GET", "/remote-control/channels/{channel}/status"),
        ("GET", "/remote-control/channels/{channel}/commands"),
        ("GET", "/ask/estate/status"),
        ("GET", "/toolbox/runs"),
        ("GET", "/toolbox/runs/{run_id}"),
        ("DELETE", "/toolbox/runs"),
        ("POST", "/targets/validate"),
        ("GET", "/users/{user_id}/summary"),
        ("GET", "/dashboard/readiness"),
        ("GET", "/reports/defaults"),
        ("GET", "/bounty-programs/vocabulary"),
        ("GET", "/bounty-programs/events"),
        ("POST", "/bounty-programs/events/seen"),
        ("GET", "/bounty-programs/settings"),
        ("GET", "/bounty-programs/status"),
        ("POST", "/bounty-programs/watches/validate-query"),
        ("GET", "/bounty-programs/watches/stream"),
        ("GET", "/bounty-reports/{platform}/summary"),
        ("GET", "/bounty-reports/{platform}/programs"),
        ("GET", "/bounty-reports/{platform}/counts"),
        ("GET", "/bounty-reports/{platform}"),
        ("GET", "/connectors/catalog"),
        ("GET", "/connectors/client/{kind}"),
        ("GET", "/issue-trackers"),
        ("GET", "/vuln-templates/stats"),
        ("POST", "/vuln-templates/seen"),
        ("POST", "/vuln-templates/search"),
        ("POST", "/vuln-templates/selection"),
    }
)

# responses that never end
STREAMED: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/events/stream"),
        ("GET", "/bounty-programs/watches/stream"),
        ("POST", "/ask/threads/{thread_id}/messages"),
        ("POST", "/ask/estate/threads/{thread_id}/messages"),
    }
)

READ_POST_ENDINGS = (
    "/search",
    "/counts",
    "/tabs",
    "/leads",
    "/groups",
    "/renders",
    "/timeline",
    "/tree",
    "/tree/hosts",
    "/tree/leaves",
    "/gone",
    "/issues",
    "/preview",
    "/backtest",
    "/estimate",
    "/selection",
    "/plan",
    "/validate-query",
    "/cached-counts",
    "/assets",
)

# routes an administrator must see project B through, per router
ANCHORS: dict[str, frozenset[tuple[str, str]]] = {
    "projects": frozenset({("GET", "/projects")}),
    "tags": frozenset({("GET", "/tags")}),
    "activity_logs": frozenset({("GET", "/activity")}),
}

# path parameters read by name, then by the longest path prefix
BY_PREFIX: dict[tuple[str, str], str] = {
    ("/engines", "id"): "engine_id",
    ("/contexts", "id"): "context_id",
    ("/schedules", "id"): "schedule_id",
    ("/scans", "id"): "scan_id",
    ("/ask/threads", "thread_id"): "thread_id",
    ("/ask/estate/threads", "thread_id"): "estate_thread_id",
    ("/tripwires/runs", "run_id"): "tripwire_run_id",
    ("/tripwires", "run_id"): "tripwire_run_id",
}
PROJECT_FIELDS = frozenset({"project_id", "project_slug"})
LIST_FIELDS = {
    "target_ids": "target_id",
    "scan_ids": "scan_id",
    "organization_ids": "organization_id",
    "tag_ids": "tag_id",
    "vulnerability_ids": "vulnerability_id",
    "fingerprints": "fingerprint",
    "ids": "subdomain_id",
}


def _short(path: str) -> str:
    return path.removeprefix(API_V1_PREFIX) or "/"


def _router(route) -> str:
    return route.endpoint.__module__.rsplit(".", 1)[-1]


def _served() -> list[tuple[str, str, Any]]:
    found = []
    for route in routes(app):
        if getattr(route, "dependant", None) is None:
            continue
        for method in sorted(route.methods):
            found.append((method, _short(route.path), route))
    return found


SERVED = _served()
ROUTERS = sorted({_router(route) for _, _, route in SERVED})
_only = {r for r in os.environ.get("ACCESS_ROUTERS", "").split(",") if r}
WALKED = [r for r in ROUTERS if not _only or r in _only]

_USER_GATES = {get_current_user, get_stream_user}
_ACCESS_GATES = {access_api.get_access, access_api.get_stream_access}


def classify(method: str, path: str, route) -> str:
    found = calls(route.dependant)
    if get_current_superuser in found:
        return "admin"
    if not found & _USER_GATES:
        return "public"
    if found & _ACCESS_GATES:
        return "scoped"
    if (method, path) in INSTANCE:
        return "instance"
    return "unclassified"


def is_read(method: str, path: str) -> bool:
    return method == "GET" or (method == "POST" and path.endswith(READ_POST_ENDINGS))


# ---------- requests ----------


def _walk(dependant):
    yield dependant
    for child in dependant.dependencies:
        yield from _walk(child)


def _annotation_sample(annotation) -> Any:
    try:
        schema = TypeAdapter(annotation).json_schema()
    except Exception:
        return "x"
    return _sample(schema, schema.get("$defs", {}), "", {})


def _resolve(schema: dict, defs: dict) -> dict:
    while "$ref" in schema:
        schema = defs[schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def _sample(schema: dict, defs: dict, name: str, ids: dict[str, Any]) -> Any:  # noqa: PLR0911
    schema = _resolve(schema, defs)
    if name in ids:
        value = ids[name]
        return [str(value)] if schema.get("type") == "array" else _plain(value)
    if name in LIST_FIELDS and LIST_FIELDS[name] in ids:
        return [_plain(ids[LIST_FIELDS[name]])]
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            options = [
                o for o in schema[key] if _resolve(o, defs).get("type") != "null"
            ]
            return _sample(options[0] if options else {}, defs, name, ids)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        wanted = set(schema.get("required", ())) | (set(props) & _known(ids))
        return {key: _sample(props[key], defs, key, ids) for key in sorted(wanted)}
    if kind == "array":
        count = schema.get("minItems", 0)
        return [_sample(schema.get("items", {}), defs, "", ids) for _ in range(count)]
    if kind == "string":
        fmt = schema.get("format")
        if fmt == "uuid":
            return str(uuid.uuid4())
        if fmt == "date-time":
            return utc_now().isoformat()
        if fmt == "date":
            return utc_now().date().isoformat()
        return "x" * max(1, schema.get("minLength", 1))
    if kind in ("integer", "number"):
        return schema.get("minimum", schema.get("exclusiveMinimum", 0) + 1)
    if kind == "boolean":
        return False
    return None


def _known(ids: dict[str, Any]) -> set[str]:
    return set(ids) | {k for k, v in LIST_FIELDS.items() if v in ids}


def _plain(value: Any) -> Any:
    return str(value) if isinstance(value, uuid.UUID) else value


def _path_key(path: str, name: str) -> str:
    best = ""
    key = name
    for (prefix, param), wanted in BY_PREFIX.items():
        if param == name and path.startswith(prefix) and len(prefix) > len(best):
            best, key = prefix, wanted
    return key


@dataclass
class Call:
    variant: str
    url: str
    params: dict[str, Any]
    body: Any
    names_b: bool = False


def build_calls(method: str, path: str, route, world: World) -> list[Call]:
    """The requests a member sends with B's ids: B's project, A's project, no project."""
    b = world.b
    dependant = route.dependant
    url = path
    for param in dependant.path_params:
        value = b.get(_path_key(path, param.name))
        if value is None:
            value = _annotation_sample(param.field_info.annotation)
        url = url.replace("{" + param.name + "}", str(_plain(value)))

    variants = [
        ("b", b),
        ("a", {**b, **{k: world.a[k] for k in PROJECT_FIELDS}}),
        ("none", {k: v for k, v in b.items() if k not in PROJECT_FIELDS}),
    ]

    built = []
    for variant, ids in variants:
        params: dict[str, Any] = {}
        for dep in _walk(dependant):
            for q in dep.query_params:
                name = q.alias
                if name in ids:
                    params[name] = _plain(ids[name])
                elif name in LIST_FIELDS and LIST_FIELDS[name] in ids:
                    params[name] = _plain(ids[LIST_FIELDS[name]])
                elif name == "path" and "scan_id" in ids:
                    params[name] = f"{ids['scan_id']}/screenshot/x.png"
                elif q.field_info.is_required():
                    params[name] = _annotation_sample(q.field_info.annotation)
        body = _body(dependant, ids)
        sent = url + json.dumps(params, default=str) + json.dumps(body, default=str)
        call = Call(variant, url, params, body, world.carries_b(sent) is not None)
        if variant != "a" or call.names_b:
            built.append(call)
    return built


def _body(dependant, ids: dict[str, Any]) -> Any:
    fields = dependant.body_params
    if not fields:
        return None

    def one(f) -> Any:
        try:
            schema = TypeAdapter(f.field_info.annotation).json_schema()
        except Exception:
            return {}
        return _sample(schema, schema.get("$defs", {}), f.alias, ids)

    embed = len(fields) > 1 or getattr(fields[0].field_info, "embed", False)
    if embed:
        return {f.alias: one(f) for f in fields}
    return one(fields[0])


# ---------- the world ----------


@dataclass
class World:
    admin: User
    member: User
    a: dict[str, Any]
    b: dict[str, Any]
    marks: tuple[str, ...]

    def carries_b(self, text: str) -> str | None:
        return next((mark for mark in self.marks if mark in text), None)


async def _seed(session: AsyncSession) -> World:
    now = utc_now()
    mine = await Estate(session).setup(name="Mine")
    other = await mine.sibling(name=WORD)
    member = await mine.member(mine.project_id)
    a = await mine.canary("ownrows", now)
    b = await other.canary(WORD, now)
    b.update(await ask_threads(other, WORD, member.id, b["target_id"]))
    a.update(await ask_threads(mine, "ownrows", member.id, a["target_id"]))
    await session.commit()
    admin = await session.get(User, mine.user_id)
    marks = (WORD, *(str(v) for v in b.values() if isinstance(v, uuid.UUID)))
    return World(admin=admin, member=member, a=a, b=b, marks=marks)


class Walker:
    def __init__(self, engine, monkeypatch):
        self.engine = engine
        self.maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        self.monkeypatch = monkeypatch
        self.world: World | None = None
        self.user: User | None = None

    async def reseed(self) -> World:
        await _truncate(self.engine)
        async with self.maker() as session:
            self.world = await _seed(session)
        return self.world

    def install(self) -> None:
        maker = self.maker

        async def session():
            async with maker() as s:
                yield s

        app.dependency_overrides[get_session] = session
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_stream_user] = lambda: self.user
        original = database.async_db_session
        for module in list(sys.modules.values()):
            if getattr(module, "async_db_session", None) is original:
                self.monkeypatch.setattr(module, "async_db_session", maker)
        self.monkeypatch.setattr(celery_dispatch, "_celery_client", MagicMock())
        self.monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_PER_MINUTE", 0)

    async def send(self, method: str, call: Call, user: User) -> httpx.Response | None:
        self.user = user
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            request = c.request(
                method,
                API_V1_PREFIX + call.url,
                params=call.params,
                json=call.body if call.body is not None else None,
            )
            try:
                return await asyncio.wait_for(request, TIMEOUT_SECONDS)
            except TimeoutError:
                return None


@pytest.fixture
async def walker(engine, monkeypatch):
    walking = Walker(engine, monkeypatch)
    walking.install()
    await walking.reseed()
    yield walking
    app.dependency_overrides.clear()
    await _truncate(engine)


def _text(response: httpx.Response) -> str:
    return " ".join(f"{k}: {v}" for k, v in response.headers.items()) + response.text


async def walk_router(walker: Walker, router: str) -> tuple[list[str], set]:
    """Failures of one router's routes, and the routes an administrator saw B through."""
    failures: list[str] = []
    seen: set[tuple[str, str]] = set()
    mine = [(m, p, r) for m, p, r in SERVED if _router(r) == router]
    mine.sort(key=lambda item: (not is_read(item[0], item[1]), item[0] == "DELETE"))
    for method, path, route in mine:
        kind = classify(method, path, route)
        if kind == "unclassified":
            failures.append(
                f"{method} {path} [unclassified] resolves no project access"
            )
        if kind in ("admin", "public") or (method, path) in STREAMED:
            continue
        reading = is_read(method, path)
        if reading:
            world = walker.world
            sample = build_calls(method, path, route, world)[0]
            response = await walker.send(method, sample, world.admin)
            if (
                response is not None
                and response.status_code < 400
                and world.carries_b(_text(response))
            ):
                seen.add((method, path))
        for call in build_calls(method, path, route, walker.world):
            world = walker.world
            response = await walker.send(method, call, world.member)
            where = f"{method} {path} [{call.variant}]"
            if response is None:
                failures.append(f"{where} did not answer in {TIMEOUT_SECONDS} s")
                continue
            code = response.status_code
            mark = None if code in REFUSED else world.carries_b(_text(response))
            if mark is not None:
                failures.append(f"{where} {code} carries {_label(mark, world)}")
            if not reading and code < 400 and call.names_b:
                failures.append(f"{where} {code} accepted a write on project B")
                await walker.reseed()
    for method, path in ANCHORS.get(router, ()):
        if (method, path) not in seen:
            failures.append(f"{method} {path} [admin] did not return project B")
    return failures, seen


def _label(mark: str, world: World) -> str:
    if mark == WORD:
        return "the canary"
    name = next(k for k, v in world.b.items() if str(v) == mark)
    return f"B's {name}"


# ---------- the guard ----------


@pytest.mark.parametrize("router", WALKED)
def test_guard_every_route_is_classified(router):
    loose = [
        f"{method} {path}"
        for method, path, route in SERVED
        if _router(route) == router and classify(method, path, route) == "unclassified"
    ]
    assert not loose, (
        f"{router}: {len(loose)} routes resolve no project access "
        "and are not listed as instance-wide:\n  " + "\n  ".join(loose)
    )


@pytest.mark.parametrize("router", WALKED)
async def test_guard_a_member_reads_nothing_of_another_project(walker, router):
    failures, seen = await walk_router(walker, router)
    reads = [(m, p) for m, p, r in SERVED if _router(r) == router and is_read(m, p)]
    unproven = [
        f"  not proven by the walk: {m} {p}" for m, p in sorted(set(reads) - seen)
    ]
    head = (
        f"{router}: an administrator saw project B on {len(seen)} of {len(reads)} reads"
    )
    sys.stdout.write("\n".join([head, *unproven]) + "\n")
    assert not failures, f"{router}: {len(failures)} failures\n  " + "\n  ".join(
        failures
    )


async def test_guard_anchors_name_served_routes():
    served = {(m, p) for m, p, _ in SERVED}
    for router, anchors in ANCHORS.items():
        assert anchors <= served, router
    assert served >= INSTANCE
    assert served >= STREAMED


# ---------- the rule ----------


def _user(*, superuser: bool = False, creates: bool = False) -> User:
    return User(
        id=uuid.uuid4(),
        username="u",
        email="u@test.local",
        hashed_password="x",
        is_superuser=superuser,
        can_create_projects=creates,
    )


def test_an_administrator_opens_every_project_and_a_member_its_own():
    one, two = uuid.uuid4(), uuid.uuid4()
    assert may_open(EVERY_PROJECT, one)
    assert may_open(frozenset({one}), one)
    assert not may_open(frozenset({one}), two)
    assert not may_open(frozenset(), one)
    assert not may_open(EVERY_PROJECT, None)


def test_a_named_project_narrows_the_access():
    one, two = uuid.uuid4(), uuid.uuid4()
    assert narrowed(EVERY_PROJECT, None) is EVERY_PROJECT
    assert narrowed(EVERY_PROJECT, one) == {one}
    assert narrowed(frozenset({one}), one) == {one}
    assert narrowed(frozenset({one}), two) == frozenset()
    assert narrowed(frozenset({one, two}), None) == {one, two}


def test_the_clause_reads_the_access():
    col = column("project_id")
    assert str(project_clause(EVERY_PROJECT, col)) == "true"
    assert str(project_clause(frozenset(), col)) == "false"
    assert "IN" in str(project_clause(frozenset({uuid.uuid4()}), col))
    statement = select(col)
    assert scoped(statement, EVERY_PROJECT, col) is statement


def test_who_creates_projects():
    assert may_create_projects(_user(superuser=True))
    assert may_create_projects(_user(creates=True))
    assert not may_create_projects(_user())


async def test_membership_is_read_from_the_rows(estate):
    other = await estate.sibling()
    member = await estate.member(estate.project_id)
    admin = await estate.session.get(User, estate.user_id)

    assert await member_projects(estate.session, admin) is EVERY_PROJECT
    assert await member_projects(estate.session, member) == {estate.project_id}
    assert await estate.session.run_sync(lambda s: member_projects_sync(s, member)) == {
        estate.project_id
    }
    assert set(await project_ids(estate.session, EVERY_PROJECT)) >= {
        estate.project_id,
        other.project_id,
    }
    assert await project_ids(estate.session, frozenset({other.project_id})) == [
        other.project_id
    ]


async def test_replacing_members_reports_a_move(estate):
    other = await estate.sibling()
    member = await estate.member(estate.project_id)
    s = estate.session

    assert not await replace_members(s, member.id, [estate.project_id], None)
    assert await replace_members(s, member.id, [other.project_id], estate.user_id)
    assert await member_projects(s, member) == {other.project_id}
    assert await replace_members(s, member.id, [], None)
    assert await member_projects(s, member) == frozenset()


# ---------- the dependencies ----------


class _Request:
    def __init__(self):
        self.state = type("State", (), {})()


async def test_access_is_resolved_once_per_request(estate, monkeypatch):
    member = await estate.member(estate.project_id)
    reads: list[int] = []
    original = access_api.member_projects

    async def counted(session, user):
        reads.append(1)
        return await original(session, user)

    monkeypatch.setattr(access_api, "member_projects", counted)
    request = _Request()
    first = await access_api.get_access(request, member, estate.session)
    again = await access_api.get_access(request, member, estate.session)
    assert first == again == {estate.project_id}
    assert len(reads) == 1


async def _refused(call) -> HTTPException:
    with pytest.raises(HTTPException) as caught:
        await call
    return caught.value


async def test_a_project_outside_the_access_is_not_found(estate):
    other = await estate.sibling()
    mine = frozenset({estate.project_id})

    assert await access_api.project_id_param(mine, estate.project_id) == (
        estate.project_id
    )
    refused = await _refused(access_api.project_id_param(mine, other.project_id))
    unknown = await _refused(access_api.project_id_param(mine, uuid.uuid4()))
    assert (refused.status_code, refused.detail) == (404, "Project not found.")
    assert (unknown.status_code, unknown.detail) == (
        refused.status_code,
        refused.detail,
    )

    assert await access_api.optional_project_param(mine, None) == mine
    assert await access_api.optional_project_param(EVERY_PROJECT, None) is None
    assert await access_api.optional_project_param(mine, estate.project_id) == mine
    await _refused(access_api.optional_project_param(mine, other.project_id))


async def test_a_slug_outside_the_access_is_not_found(estate):
    other = await estate.sibling()
    mine = frozenset({estate.project_id})
    s = estate.session

    assert await access_api.project_slug_param(mine, s, estate.slug) == (
        estate.project_id
    )
    refused = await _refused(access_api.project_slug_param(mine, s, other.slug))
    unknown = await _refused(access_api.project_slug_param(mine, s, "missing"))
    assert refused.detail == unknown.detail == "Project not found."
    assert await access_api.optional_project_slug_param(mine, s, None) == mine
    assert await access_api.optional_project_slug_param(
        EVERY_PROJECT, s, other.slug
    ) == {other.project_id}


async def test_a_row_of_another_project_is_not_found(estate):
    other = await estate.sibling()
    mine = frozenset({estate.project_id})
    s = estate.session
    own = await estate.target("example.com")
    theirs = await other.target("example.org")

    assert (await access_api.owned(s, mine, Target, own, "Target")).id == own
    assert await access_api.require_owned(s, mine, Target, own, "Target") == (
        estate.project_id
    )
    for row_id in (theirs, uuid.uuid4()):
        for call in (
            access_api.owned(s, mine, Target, row_id, "Target"),
            access_api.require_owned(s, mine, Target, row_id, "Target"),
        ):
            refused = await _refused(call)
            assert (refused.status_code, refused.detail) == (404, "Target not found.")


# ---------- projects and users ----------


@pytest.fixture
def no_revocation(monkeypatch) -> list[uuid.UUID]:
    from app.api.v1 import users as users_api  # noqa: PLC0415

    revoked: list[uuid.UUID] = []

    async def revoke(user_id):
        revoked.append(user_id)

    monkeypatch.setattr(users_api, "revoke_user_tokens", revoke)
    return revoked


async def test_a_member_lists_only_its_projects(estate):
    from app.api.v1.projects import list_projects  # noqa: PLC0415

    other = await estate.sibling()
    member = await estate.member(estate.project_id)
    s = estate.session

    mine = await list_projects(member, frozenset({estate.project_id}), s)
    every = await list_projects(member, EVERY_PROJECT, s)
    assert [p.id for p in mine] == [estate.project_id]
    assert {estate.project_id, other.project_id} <= {p.id for p in every}


async def test_project_creation_needs_the_right_and_makes_a_member(
    estate, flush_only, monkeypatch
):
    from app.api.v1 import projects as projects_api  # noqa: PLC0415
    from shared.models.project import ProjectCreate  # noqa: PLC0415

    async def builtin(*_args):
        return None

    monkeypatch.setattr(projects_api.ScanEngineService, "ensure_builtin", builtin)
    plain = await estate.member(estate.project_id)
    granted = await estate.member(estate.project_id, can_create_projects=True)

    refused = await _refused(
        projects_api.create_project(ProjectCreate(name="Nope"), plain, flush_only)
    )
    assert refused.status_code == 403
    made = await projects_api.create_project(
        ProjectCreate(name="Mine"), granted, flush_only
    )
    assert made.id in await member_projects(flush_only, granted)


async def test_an_administrator_sets_a_users_projects(
    estate, flush_only, no_revocation
):
    from app.api.v1.users import list_users, set_user_projects  # noqa: PLC0415
    from shared.models.user import UserProjects  # noqa: PLC0415

    other = await estate.sibling()
    member = await estate.member(estate.project_id)
    admin = await flush_only.get(User, estate.user_id)

    read = await set_user_projects(
        member.id, UserProjects(project_ids=[other.project_id]), flush_only, admin
    )
    assert read.project_ids == [other.project_id]
    assert no_revocation == [member.id]
    await set_user_projects(
        member.id, UserProjects(project_ids=[other.project_id]), flush_only, admin
    )
    assert no_revocation == [member.id]

    listed = {u.id: u for u in await list_users(flush_only, admin, 0, 100)}
    assert listed[member.id].project_ids == [other.project_id]

    unknown = await _refused(
        set_user_projects(
            member.id, UserProjects(project_ids=[uuid.uuid4()]), flush_only, admin
        )
    )
    assert unknown.status_code == 422


async def test_changing_the_creation_right_or_role_signs_the_user_out(
    estate, flush_only, no_revocation
):
    from app.api.v1.users import update_user  # noqa: PLC0415
    from shared.models.user import UserAdminUpdate  # noqa: PLC0415

    member = await estate.member(estate.project_id)
    admin = await flush_only.get(User, estate.user_id)

    same = await update_user(
        member.id, UserAdminUpdate(can_create_projects=False), flush_only, admin
    )
    assert not same.can_create_projects
    assert no_revocation == []
    granted = await update_user(
        member.id, UserAdminUpdate(can_create_projects=True), flush_only, admin
    )
    assert granted.can_create_projects
    assert granted.project_ids == [estate.project_id]
    await update_user(member.id, UserAdminUpdate(is_superuser=True), flush_only, admin)
    assert no_revocation == [member.id, member.id]


async def test_a_new_user_gets_its_projects(estate, flush_only):
    from app.api.v1.users import create_user  # noqa: PLC0415
    from shared.models.user import UserAdminCreate  # noqa: PLC0415

    admin = await flush_only.get(User, estate.user_id)
    tag = uuid.uuid4().hex[:8]
    made = await create_user(
        UserAdminCreate(
            email=f"n{tag}@test.local",
            username=f"n{tag}",
            password="Vq7#mT9!pLx2@wRz",
            can_create_projects=True,
            project_ids=[estate.project_id],
        ),
        flush_only,
        admin,
    )
    assert made.can_create_projects
    assert made.project_ids == [estate.project_id]
    stored = await flush_only.scalars(
        select(ProjectMember.project_id).where(ProjectMember.user_id == made.id)
    )
    assert stored.all() == [estate.project_id]
