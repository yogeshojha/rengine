from __future__ import annotations

import fnmatch
import uuid
from datetime import timedelta

import httpx
import pyotp
import pytest
from fastapi import HTTPException, Response
from sqlalchemy import func, select
from starlette.requests import Request

from app import reset_password
from app.api import deps
from app.api.v1 import auth, totp
from app.config import API_V1_PREFIX, settings
from app.core import ratelimit, throttle
from app.core.database import get_session
from app.core.security import ACCESS_TOKEN_COOKIE, create_access_token, hash_password
from app.main import app
from app.services import access_keys
from app.services import export as export_service
from app.services import totp as totp_service
from app.services.totp import TOTPService
from shared.definitions.access_keys import (
    CALLS_KEY,
    EXPIRY_DETAIL,
    FAILURE_KEY,
    FAILURE_LIMIT,
    INVALID_DETAIL,
    LIMIT_DETAIL,
    MAX_ACCESS_KEYS,
    OWNER_KEY,
    READ_ONLY_DETAIL,
    REFUSED_DETAIL,
    USED_KEY,
    AccessKeyLevel,
)
from shared.definitions.api_reference import first_request
from shared.enums.scan_context import AuthType
from shared.enums.target import TargetType
from shared.models.access_key import AccessKey, AccessKeyCreate
from shared.models.export import Export
from shared.models.scan_context import ScanContext
from shared.models.scan_schedule import ScanSchedule
from shared.models.target import Target
from shared.models.user import User
from shared.services.credential_access import hold_as_key
from shared.services.scan_factory import ScanFactoryError, build_scan_for_target_sync
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.api

OLD = "Vq7#mT9!pLx2@wRz"
NEW = "Hk4$nW8&qZy3^bUe"
ADDRESS = "203.0.113.9"


class _Pipe:
    def __init__(self, redis: _Redis):
        self.redis = redis
        self.ops: list = []

    def incr(self, key):
        self.ops.append(("incr", key))

    def expire(self, key, seconds, nx=False):  # noqa: ARG002
        self.ops.append(("expire", key))

    async def execute(self):
        return [
            await self.redis.incr(key) if op == "incr" else True for op, key in self.ops
        ]


class _Redis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.expiry: dict[str, int | None] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = str(value)
        self.expiry[key] = ex
        return True

    async def exists(self, key):
        return int(key in self.store)

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    async def incr(self, key):
        self.store[key] = str(int(self.store.get(key, 0)) + 1)
        return int(self.store[key])

    async def getdel(self, key):
        return self.store.pop(key, None)

    async def mget(self, keys):
        return [self.store.get(k) for k in keys]

    async def ttl(self, key):  # noqa: ARG002
        return 60

    def pipeline(self, **_kwargs):
        return _Pipe(self)

    async def scan_iter(self, match):
        for key in list(self.store):
            if fnmatch.fnmatchcase(key, match):
                yield key


class _Down:
    def __getattr__(self, name):
        raise ConnectionError(name)


@pytest.fixture
def redis(monkeypatch) -> _Redis:
    fake = _Redis()
    for module in (ratelimit, access_keys, totp_service, throttle):
        monkeypatch.setattr(module, "async_client", lambda: fake)
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT_PER_MINUTE", 0)
    return fake


@pytest.fixture
async def api(flush_only, redis):
    async def same():
        yield flush_only

    app.dependency_overrides[get_session] = same
    transport = httpx.ASGITransport(app=app, client=(ADDRESS, 4000))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _user(session, *, superuser: bool = False, **fields) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"key{tag}",
        email=f"key{tag}@test.local",
        hashed_password=hash_password(OLD),
        is_superuser=superuser,
        **fields,
    )
    session.add(user)
    await session.flush()
    return user


def _cookie(user: User) -> dict[str, str]:
    return {"cookie": f"{ACCESS_TOKEN_COOKIE}={create_access_token(str(user.id))}"}


def _bearer(secret: str) -> dict[str, str]:
    return {"authorization": f"Bearer {secret}"}


async def _key(
    session, user: User, access: AccessKeyLevel = AccessKeyLevel.WRITE, **fields
) -> str:
    created = await access_keys.create_key(
        session, user, AccessKeyCreate(name="script", access=access, **fields)
    )
    return created.key


def _url(path: str) -> str:
    return API_V1_PREFIX + path


# ---------- lifecycle ----------


async def test_a_key_is_shown_once_and_authenticates_as_its_owner(api, flush_only):
    user = await _user(flush_only)

    created = await api.post(
        _url("/access-keys"),
        json={"name": "Nightly export", "access": "read"},
        headers=_cookie(user),
    )
    assert created.status_code == 201
    body = created.json()
    secret = body["key"]
    assert secret.startswith("rngkey_")
    assert body["prefix"] == secret[: len("rngkey_") + 8]
    assert body["access"] == "read"
    assert body["expires_at"] is not None
    assert body["first_request"] == first_request(API_V1_PREFIX)
    stored = await flush_only.scalar(
        select(AccessKey).where(AccessKey.id == body["id"])
    )
    assert stored.token_hash != secret
    assert secret not in stored.token_hash

    listed = await api.get(_url("/access-keys"), headers=_cookie(user))
    assert [k["id"] for k in listed.json()] == [body["id"]]
    assert "key" not in listed.json()[0]
    assert "first_request" not in listed.json()[0]
    assert "token_hash" not in listed.json()[0]

    me = await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert me.status_code == 200
    assert me.json()["username"] == user.username

    revoked = await api.delete(
        _url(f"/access-keys/{body['id']}"), headers=_cookie(user)
    )
    assert revoked.status_code == 204
    after = await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert (after.status_code, after.json()["detail"]) == (401, INVALID_DETAIL)
    assert (await api.get(_url("/access-keys"), headers=_cookie(user))).json() == []


async def test_no_expiry_and_the_expiry_choices(api, flush_only):
    user = await _user(flush_only)
    never = await api.post(
        _url("/access-keys"),
        json={"name": "n", "expires_in_days": None},
        headers=_cookie(user),
    )
    assert never.status_code == 201
    assert never.json()["expires_at"] is None
    odd = await api.post(
        _url("/access-keys"),
        json={"name": "n", "expires_in_days": 7},
        headers=_cookie(user),
    )
    assert odd.status_code == 422
    assert EXPIRY_DETAIL in odd.text
    assert EXPIRY_DETAIL == "Choose an expiry: 30 days, 90 days, 1 year or No expiry."
    blank = await api.post(
        _url("/access-keys"), json={"name": "   "}, headers=_cookie(user)
    )
    assert blank.status_code == 422


async def test_a_key_of_another_account_is_not_found(api, flush_only):
    user = await _user(flush_only)
    other = await _user(flush_only)
    await _key(flush_only, other)
    theirs = (await access_keys.list_keys(flush_only, other.id))[0]
    response = await api.delete(
        _url(f"/access-keys/{theirs.id}"), headers=_cookie(user)
    )
    assert response.status_code == 404


# ---------- refusals ----------

REFUSED = [
    ("POST", "/auth/login", {"username": "a", "password": "b"}),
    ("POST", "/auth/refresh", None),
    ("POST", "/auth/logout", None),
    ("POST", "/auth/2fa/login", {"mfa_token": "x", "code": "1"}),
    ("POST", "/auth/2fa/setup", {"current_password": OLD}),
    ("POST", "/auth/2fa/verify", {"code": "1"}),
    ("POST", "/auth/2fa/disable", {"code": "1"}),
    ("GET", "/auth/2fa/status", None),
    ("POST", "/auth/change-password", {"current_password": OLD, "new_password": NEW}),
    ("POST", "/auth/change-username", {"current_password": OLD, "new_username": "z"}),
    ("GET", "/access-keys", None),
    ("POST", "/access-keys", {"name": "again"}),
    ("DELETE", f"/access-keys/{uuid.uuid4()}", None),
    ("GET", f"/users/{uuid.uuid4()}/access-keys", None),
    ("GET", "/users", None),
    ("GET", "/api-keys", None),
    ("GET", f"/api-keys/{uuid.uuid4()}/reveal", None),
    ("GET", "/mcp/tokens", None),
    ("GET", "/mcp/status", None),
    ("POST", "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}),
    ("GET", "/connectors", None),
    ("POST", "/connectors/ingest", {}),
    ("GET", "/remote-control/channels/telegram/status", None),
    ("GET", "/ask/threads", None),
    ("POST", "/ask/threads", {}),
    ("GET", "/ask/estate/status", None),
    ("POST", "/investigate/approve", {}),
    ("GET", "/events/stream", None),
    ("POST", f"/interest/scan/{uuid.uuid4()}/judge", None),
    ("POST", f"/interest/scan/{uuid.uuid4()}/suggestions", None),
    ("PATCH", "/instance-settings", {}),
]


@pytest.mark.parametrize(("method", "path", "body"), REFUSED)
async def test_a_key_never_calls_these(api, flush_only, method, path, body):
    admin = await _user(flush_only, superuser=True)
    secret = await _key(flush_only, admin)
    response = await api.request(method, _url(path), json=body, headers=_bearer(secret))
    assert (response.status_code, response.json()["detail"]) == (403, REFUSED_DETAIL)


async def test_a_stream_dependency_refuses_a_key(flush_only, redis):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    request = Request(
        {"type": "http", "headers": [(b"authorization", f"Bearer {secret}".encode())]}
    )
    with pytest.raises(HTTPException) as refused:
        await deps.get_stream_user(request, secret)
    assert refused.value.status_code == 403


async def test_a_key_in_the_cookie_is_not_a_key(api, flush_only):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    response = await api.get(
        _url("/auth/me"), headers={"cookie": f"{ACCESS_TOKEN_COOKIE}={secret}"}
    )
    assert response.status_code == 401


# ---------- levels ----------


async def test_a_read_key_reads_and_never_writes(api, estate):
    member = await estate.member(estate.project_id)
    target = Target(
        target_value="read.example.com",
        target_type=TargetType.DOMAIN,
        project_id=estate.project_id,
        created_by=estate.user_id,
    )
    estate.session.add(target)
    await estate.session.flush()
    reader = _bearer(await _key(estate.session, member, AccessKeyLevel.READ))
    writer = _bearer(await _key(estate.session, member, AccessKeyLevel.WRITE))
    project = {"project_id": str(estate.project_id)}

    listed = await api.get(_url("/targets"), params=project, headers=reader)
    assert listed.status_code == 200
    assert (
        await api.get(_url(f"/targets/{target.id}"), headers=reader)
    ).status_code == 200
    searched = await api.post(
        _url("/subdomains/search"), params=project, json={}, headers=reader
    )
    assert searched.status_code == 200
    exposures = await api.post(
        _url("/interest/project"), params=project, json={}, headers=reader
    )
    assert exposures.status_code == 200, exposures.text

    for method, path, body in (
        (
            "POST",
            "/targets",
            {"target_value": "x.example.com", "project_slug": estate.slug},
        ),
        ("PATCH", f"/targets/{target.id}", {"display_name": "x"}),
        ("DELETE", f"/targets/{target.id}", None),
        ("POST", "/scans/batch", {}),
        ("POST", "/notes", {}),
        ("GET", "/tools/viewdns/reverse-whois?q=example.com", None),
    ):
        refused = await api.request(method, _url(path), json=body, headers=reader)
        assert (refused.status_code, refused.json()["detail"]) == (
            403,
            READ_ONLY_DETAIL,
        ), path

    renamed = await api.patch(
        _url(f"/targets/{target.id}"), json={"display_name": "Renamed"}, headers=writer
    )
    assert renamed.status_code == 200

    for path, body in (
        (f"/targets/{target.id}/assets", {}),
        (
            "/tools/viewdns/cached-counts",
            {"queries": [{"source": "reverse_whois", "query": "example.com"}]},
        ),
    ):
        read = await api.post(_url(path), params=project, json=body, headers=reader)
        assert read.status_code == 200, (path, read.text)


@pytest.mark.parametrize("filters", [{"q": "and"}, {"tech": ["a\x00b"]}])
async def test_an_export_the_worker_would_fail_is_refused(
    api, estate, monkeypatch, filters
):
    member = await estate.member(estate.project_id)
    reader = _bearer(await _key(estate.session, member, AccessKeyLevel.READ))
    queued: list[str] = []
    monkeypatch.setattr(export_service, "dispatch_export", queued.append)
    response = await api.post(
        _url("/exports"),
        params={"project_id": str(estate.project_id)},
        json={
            "dimension": "web_assets",
            "export_format": "csv",
            "filters": filters,
        },
        headers=reader,
    )
    assert response.status_code == 422, response.text
    assert queued == []
    held = select(func.count()).where(Export.project_id == estate.project_id)
    assert await estate.session.scalar(held) == 0


async def test_a_key_opens_only_its_owners_projects(api, estate):
    other = await estate.sibling()
    member = await estate.member(estate.project_id)
    hidden = Target(
        target_value="hidden.example.com",
        target_type=TargetType.DOMAIN,
        project_id=other.project_id,
        created_by=estate.user_id,
    )
    estate.session.add(hidden)
    await estate.session.flush()
    secret = await _key(estate.session, member, AccessKeyLevel.READ)

    refused = await api.get(_url(f"/targets/{hidden.id}"), headers=_bearer(secret))
    assert (refused.status_code, refused.json()["detail"]) == (404, "Target not found.")
    for path, params in (
        (f"/targets/{hidden.id}", None),
        ("/targets", {"project_id": str(other.project_id)}),
    ):
        by_key = await api.get(_url(path), params=params, headers=_bearer(secret))
        by_session = await api.get(_url(path), params=params, headers=_cookie(member))
        assert hidden.target_value not in by_key.text
        assert (by_key.status_code, by_key.json()) == (
            by_session.status_code,
            by_session.json(),
        )


async def test_an_administrators_key_has_no_administrator_powers(api, estate):
    admin = await estate.session.get(User, estate.user_id)
    creator = await estate.member(estate.project_id)
    context = ScanContext(
        project_id=estate.project_id,
        created_by=creator.id,
        name="Signed in",
        auth_type=AuthType.BEARER.value,
    )
    estate.session.add(context)
    await estate.session.flush()
    key = _bearer(await _key(estate.session, admin))
    project = {"project_id": str(estate.project_id)}
    engine = {"name": "via key", "tool_options": {"nuclei": "-stats"}}

    by_key = await api.post(_url("/engines"), params=project, json=engine, headers=key)
    assert by_key.status_code == 403
    by_session = await api.post(
        _url("/engines"), params=project, json=engine, headers=_cookie(admin)
    )
    assert by_session.status_code == 201

    renamed = await api.patch(
        _url(f"/contexts/{context.id}"),
        params=project,
        json={"name": "Renamed"},
        headers=key,
    )
    assert renamed.status_code == 403
    me = await api.get(_url("/auth/me"), headers=key)
    assert me.json()["is_superuser"] is False

    plain = await api.post(
        _url("/engines"), params=project, json={"name": "plain"}, headers=_cookie(admin)
    )
    target = await estate.target("example.com")
    schedule = {
        "name": "nightly",
        "target_ids": [str(target)],
        "engine_id": plain.json()["id"],
        "context_id": str(context.id),
        "schedule_type": "interval",
        "interval_every": 1,
        "interval_unit": "days",
    }
    scheduled = await api.post(
        _url("/schedules"), params=project, json=schedule, headers=_cookie(admin)
    )
    assert scheduled.status_code == 201
    for path, body in (
        ("/schedules", schedule),
        (
            "/scans/batch",
            {
                "engine_id": plain.json()["id"],
                "context_id": str(context.id),
                "target_ids": [str(target)],
            },
        ),
    ):
        launched = await api.post(_url(path), params=project, json=body, headers=key)
        assert launched.status_code == 403, path
        assert "Signed in" in launched.json()["detail"]
    edited = await api.patch(
        _url(f"/schedules/{scheduled.json()['id']}"),
        params=project,
        json={"target_ids": [str(target)]},
        headers=key,
    )
    assert edited.status_code == 403

    other = await estate.sibling()
    listed = await api.get(
        _url("/targets"), params={"project_id": str(other.project_id)}, headers=key
    )
    assert listed.status_code == 200


async def test_a_schedule_made_through_an_administrators_key_fires_as_a_member(
    api, estate
):
    admin = await estate.session.get(User, estate.user_id)
    creator = await estate.member(estate.project_id)
    context = ScanContext(
        project_id=estate.project_id, created_by=creator.id, name="Later signed in"
    )
    estate.session.add(context)
    await estate.session.flush()
    project = {"project_id": str(estate.project_id)}
    engine = await api.post(
        _url("/engines"), params=project, json={"name": "plain"}, headers=_cookie(admin)
    )
    target = await estate.target("example.com")
    schedule = {
        "name": "nightly",
        "target_ids": [str(target)],
        "engine_id": engine.json()["id"],
        "context_id": str(context.id),
        "schedule_type": "interval",
        "interval_every": 1,
        "interval_unit": "days",
    }
    made = {}
    for label, headers in (
        ("key", _bearer(await _key(estate.session, admin))),
        ("session", _cookie(admin)),
    ):
        response = await api.post(
            _url("/schedules"), params=project, json=schedule, headers=headers
        )
        assert response.status_code == 201, response.text
        made[label] = response.json()["id"]

    hold_as_key(estate.session, None)
    context.auth_type = AuthType.BEARER.value
    await estate.session.flush()

    def fire(sync, schedule_id):
        sched = sync.get(ScanSchedule, uuid.UUID(schedule_id))
        return build_scan_for_target_sync(
            sync,
            project_id=sched.project_id,
            target_id=uuid.UUID(sched.target_ids[0]),
            engine_id=sched.engine_id,
            context_id=sched.context_id,
            created_by=sched.created_by,
            as_key=sched.created_with_key,
        )

    with pytest.raises(ScanFactoryError, match="Later signed in"):
        await estate.session.run_sync(fire, made["key"])
    assert (await estate.session.run_sync(fire, made["session"])).id is not None


# ---------- the key stops working ----------


async def test_an_expired_key_is_refused(api, flush_only):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    key = await flush_only.scalar(select(AccessKey).where(AccessKey.user_id == user.id))
    key.expires_at = utc_now() - timedelta(seconds=1)
    await flush_only.flush()
    response = await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert (response.status_code, response.json()["detail"]) == (401, INVALID_DETAIL)
    listed = await access_keys.list_keys(flush_only, user.id)
    assert listed[0].expired


async def test_a_disabled_or_deleted_owner_ends_the_key(api, flush_only):
    disabled = await _user(flush_only)
    deleted = await _user(flush_only)
    first = await _key(flush_only, disabled)
    second = await _key(flush_only, deleted)
    disabled.is_active = False
    await flush_only.delete(deleted)
    await flush_only.flush()
    for secret in (first, second):
        response = await api.get(_url("/auth/me"), headers=_bearer(secret))
        assert (response.status_code, response.json()["detail"]) == (
            401,
            INVALID_DETAIL,
        )


async def test_a_reenabled_owner_does_not_get_the_key_back(api, flush_only):
    admin = await _user(flush_only, superuser=True)
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    for active in (False, True):
        moved = await api.patch(
            _url(f"/users/{user.id}"),
            json={"is_active": active},
            headers=_cookie(admin),
        )
        assert moved.status_code == 200, moved.text
    response = await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert (response.status_code, response.json()["detail"]) == (401, INVALID_DETAIL)
    assert await _live(flush_only, user) == 0


@pytest.mark.parametrize(
    "secret",
    ["rngkey_" + "0" * 48, "rngkey_short", "rngkey_" + "z" * 48],
)
async def test_an_unknown_key_answers_the_same_body(api, secret):
    response = await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert (response.status_code, response.json()["detail"]) == (401, INVALID_DETAIL)


# ---------- credential changes ----------


async def _live(session, user: User) -> int:
    rows = await session.scalars(
        select(AccessKey).where(
            AccessKey.user_id == user.id, AccessKey.revoked_at.is_(None)
        )
    )
    return len(rows.all())


async def test_a_password_change_revokes_every_key(flush_only, redis):
    user = await _user(flush_only)
    await _key(flush_only, user)
    await _key(flush_only, user)
    await auth.change_password(
        auth.PasswordChangeRequest(current_password=OLD, new_password=NEW),
        response=Response(),
        current_user=user,
        session=flush_only,
    )
    assert await _live(flush_only, user) == 0


async def test_a_username_change_revokes_every_key(flush_only, redis):
    user = await _user(flush_only)
    await _key(flush_only, user)
    await auth.change_username(
        auth.UsernameChangeRequest(
            new_username=f"renamed{uuid.uuid4().hex[:6]}", current_password=OLD
        ),
        current_user=user,
        session=flush_only,
    )
    assert await _live(flush_only, user) == 0


async def test_two_factor_enrolment_and_removal_revoke_every_key(flush_only, redis):
    user = await _user(flush_only)
    service = TOTPService(flush_only)
    setup = await service.start_setup(user)
    await _key(flush_only, user)
    await totp.verify_2fa(
        totp.TwoFactorCodeRequest(code=pyotp.TOTP(setup["secret"]).now()),
        response=Response(),
        current_user=user,
        service=service,
    )
    assert await _live(flush_only, user) == 0

    await _key(flush_only, user)
    redis.store.clear()
    await totp.disable_2fa(
        totp.TwoFactorCodeRequest(code=pyotp.TOTP(setup["secret"]).now()),
        response=Response(),
        current_user=user,
        service=service,
    )
    assert await _live(flush_only, user) == 0


async def test_a_reset_password_revokes_every_key(flush_only, redis):
    user = await _user(flush_only)
    await _key(flush_only, user)
    account = await reset_password.find(flush_only, user.username)
    await reset_password.reset(flush_only, account, NEW, remove_2fa=False)
    assert await _live(flush_only, user) == 0


# ---------- use, limits and the cap ----------


async def test_last_use_is_written_once_a_minute(api, flush_only, redis):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    key = await flush_only.scalar(select(AccessKey).where(AccessKey.user_id == user.id))
    writes: list[int] = []
    original = flush_only.commit

    async def counted():
        writes.append(1)
        await original()

    flush_only.commit = counted
    for _ in range(3):
        assert (
            await api.get(_url("/auth/me"), headers=_bearer(secret))
        ).status_code == 200
    assert len(writes) == 1
    await flush_only.refresh(key)
    assert key.use_count == 1
    assert key.last_used_ip == ADDRESS
    assert key.last_used_at is not None
    assert redis.store[CALLS_KEY.format(key_id=key.id)] == "2"
    assert (await access_keys.list_keys(flush_only, user.id))[0].use_count == 3

    del redis.store[USED_KEY.format(key_id=key.id)]
    await api.get(_url("/auth/me"), headers=_bearer(secret))
    await flush_only.refresh(key)
    assert key.use_count == 4
    assert len(writes) == 2


async def test_the_throttle_charges_the_owner(api, flush_only):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    request = Request(
        {
            "type": "http",
            "headers": [(b"authorization", f"Bearer {secret}".encode())],
            "client": (ADDRESS, 1),
        }
    )
    assert await throttle.throttle_identity(request) == f"ip:{ADDRESS}"
    await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert await throttle.throttle_identity(request) == f"user:{user.id}"


async def test_the_owner_is_charged_no_longer_than_the_key_lives(
    api, flush_only, redis
):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    key = await flush_only.scalar(select(AccessKey).where(AccessKey.user_id == user.id))
    key.expires_at = utc_now() + timedelta(seconds=30)
    await flush_only.flush()
    assert (await api.get(_url("/auth/me"), headers=_bearer(secret))).status_code == 200
    owner = OWNER_KEY.format(token_hash=key.token_hash)
    assert redis.store[owner] == str(user.id)
    assert 1 <= redis.expiry[owner] <= 30


async def test_failed_attempts_spend_the_address_budget(api, redis):
    unknown = _bearer("rngkey_" + "0" * 48)
    await api.get(_url("/auth/me"), headers=unknown)
    assert redis.store[FAILURE_KEY.format(address=ADDRESS)] == "1"
    redis.store[FAILURE_KEY.format(address=ADDRESS)] = str(FAILURE_LIMIT)
    response = await api.get(_url("/auth/me"), headers=unknown)
    assert response.status_code == 429


async def test_the_key_check_fails_closed(api, flush_only, monkeypatch):
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    monkeypatch.setattr(ratelimit, "async_client", _Down)
    response = await api.get(_url("/auth/me"), headers=_bearer(secret))
    assert response.status_code == 503


async def test_an_account_holds_a_capped_number_of_keys(api, flush_only):
    user = await _user(flush_only)
    for _ in range(MAX_ACCESS_KEYS):
        await _key(flush_only, user)
    response = await api.post(
        _url("/access-keys"), json={"name": "one more"}, headers=_cookie(user)
    )
    assert (response.status_code, response.json()["detail"]) == (409, LIMIT_DETAIL)

    oldest = await flush_only.scalar(
        select(AccessKey).where(AccessKey.user_id == user.id).limit(1)
    )
    oldest.expires_at = utc_now() - timedelta(days=1)
    await flush_only.flush()
    again = await api.post(
        _url("/access-keys"), json={"name": "one more"}, headers=_cookie(user)
    )
    assert again.status_code == 201


# ---------- administration ----------


async def test_an_administrator_lists_and_revokes_anyones_keys(api, flush_only):
    admin = await _user(flush_only, superuser=True)
    user = await _user(flush_only)
    secret = await _key(flush_only, user)
    key_id = (await access_keys.list_keys(flush_only, user.id))[0].id

    listed = await api.get(
        _url(f"/users/{user.id}/access-keys"), headers=_cookie(admin)
    )
    assert [k["id"] for k in listed.json()] == [str(key_id)]
    refused = await api.get(
        _url(f"/users/{admin.id}/access-keys"), headers=_cookie(user)
    )
    assert refused.status_code == 403
    missing = await api.get(
        _url(f"/users/{uuid.uuid4()}/access-keys"), headers=_cookie(admin)
    )
    assert missing.status_code == 404

    revoked = await api.delete(
        _url(f"/users/{user.id}/access-keys/{key_id}"), headers=_cookie(admin)
    )
    assert revoked.status_code == 204
    assert (await api.get(_url("/auth/me"), headers=_bearer(secret))).status_code == 401
    again = await api.delete(
        _url(f"/users/{user.id}/access-keys/{key_id}"), headers=_cookie(admin)
    )
    assert again.status_code == 404


async def test_an_administrators_key_creates_projects_as_its_owner(api, flush_only):
    admin = await _user(flush_only, superuser=True)
    member = await _user(flush_only)
    for owner, expected in ((admin, 201), (member, 403)):
        made = await api.post(
            _url("/projects"),
            json={"name": f"via key {owner.username}"},
            headers=_bearer(await _key(flush_only, owner)),
        )
        assert made.status_code == expected, made.text


async def test_the_reference_answers_a_list(api, flush_only):
    user = await _user(flush_only)
    response = await api.get(_url("/reference"), headers=_cookie(user))
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Projects"
