from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.dependencies.utils import get_flat_dependant
from sqlalchemy import select
from starlette.requests import Request

from app.api import scope as scope_module
from app.api.deps import get_current_superuser
from app.api.v1 import connectors as router_module
from app.core import ratelimit
from app.services.connector import ConnectorError, ConnectorService
from connectors import auth
from shared.definitions.connectors import CandidateState
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import Protocol
from shared.enums.scan import ScanActivityStatus
from shared.enums.target import TargetType
from shared.models.connector import (
    ConnectorAction,
    ConnectorCandidate,
    ConnectorCreate,
    HandoffRequest,
    IngestItem,
    IngestRequest,
)
from shared.models.endpoint import Endpoint
from shared.models.project import Project
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.user import User
from shared.models.vulnerability import Vulnerability
from shared.services import proxy_sync
from shared.services.scan_resolve import MASK, seal_headers

pytestmark = pytest.mark.api

HOST = "app.example.com"


class _Redis:
    def __init__(self):
        self.store: dict[str, int] = {}

    async def get(self, key):
        return self.store.get(key)

    async def ttl(self, _key):
        return 600

    async def set(self, key, value, ex=None):  # noqa: ARG002
        self.store[key] = value

    async def exists(self, key):
        return int(key in self.store)

    async def delete(self, key):
        self.store.pop(key, None)

    def pipeline(self, transaction=True):  # noqa: ARG002
        return _Pipeline(self)


class _Pipeline:
    def __init__(self, redis: _Redis):
        self.redis, self.keys = redis, []

    def incr(self, key):
        self.keys.append(key)

    def expire(self, *_args, **_kwargs):
        return None

    async def execute(self):
        for key in self.keys:
            self.redis.store[key] = int(self.redis.store.get(key) or 0) + 1


@pytest.fixture
def redis(monkeypatch):
    fake = _Redis()
    monkeypatch.setattr(ratelimit, "async_client", lambda: fake)
    monkeypatch.setattr("app.services.connector.async_client", lambda: fake)
    return fake


def _request(address: str = "203.0.113.7") -> Request:
    return Request({"type": "http", "headers": [], "client": (address, 5000)})


async def _connector(estate):
    service = ConnectorService(estate.session)
    created = await service.create(
        ConnectorCreate(name="Burp", project_id=estate.project_id), estate.user_id
    )
    return (
        service,
        await service.get(created.connector.id, estate.project_id),
        created.secret,
    )


async def _finding(estate, now, request: str | None, config: dict | None = None):
    await estate.scan(
        "example.com", "census", at=now - timedelta(hours=1), config=config
    )
    await estate.vulns("census", [("cve-x", "high")], at=now, host=HOST)
    finding = await estate.session.scalar(
        select(Vulnerability).where(Vulnerability.scan_id == estate.scans["census"])
    )
    finding.protocol = Protocol.HTTP.value
    finding.request = request
    await estate.session.flush()
    return finding


# ---------- B1: management is superuser only ----------


def _route(path: str, method: str):
    return next(
        r for r in router_module.router.routes if r.path == path and method in r.methods
    )


def _needs_superuser(route) -> bool:
    return any(
        dep.call is get_current_superuser
        for dep in get_flat_dependant(route.dependant).dependencies
    )


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/connectors", "POST"),
        ("/connectors/{connector_id}", "PATCH"),
        ("/connectors/{connector_id}/rotate", "POST"),
        ("/connectors/{connector_id}", "DELETE"),
    ],
)
def test_connector_management_needs_a_superuser(path, method):
    assert _needs_superuser(_route(path, method))


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/connectors", "GET"),
        ("/connectors/{connector_id}/handoff", "POST"),
        ("/connectors/{connector_id}/candidates", "GET"),
    ],
)
def test_reads_and_handoff_stay_open_to_every_user(path, method):
    assert not _needs_superuser(_route(path, method))


# ---------- B2: restored credentials ----------


async def test_a_handoff_restores_the_run_credentials(estate, now):
    finding = await _finding(
        estate,
        now,
        f"GET / HTTP/1.1\r\nHost: {HOST}\r\nAuthorization: Bearer {MASK}\r\n\r\n",
        {"headers": seal_headers({"Authorization": "Bearer real-token"})},
    )
    service, row, _ = await _connector(estate)
    row.restore_credentials = True
    await service.handoff(
        row.id, estate.project_id, HandoffRequest(finding_ids=[finding.id])
    )
    (sent,) = await service.take_actions(row)
    assert "Authorization: Bearer real-token" in sent.request
    stored = await estate.session.scalar(select(ConnectorAction.request))
    assert "real-token" not in stored


# ---------- B3: a scan of another project ----------


async def test_a_scan_of_another_project_is_not_found(estate, now):
    sid = await estate.scan("example.com", "census", at=now)
    other = uuid.uuid4()
    estate.session.add(
        Project(
            id=other, name="Other", slug=f"o-{other.hex[:8]}", created_by=estate.user_id
        )
    )
    await estate.session.flush()
    dimension = SurfaceDimension.ENDPOINTS.value

    with pytest.raises(HTTPException) as exc:
        await scope_module.resolve_scope(estate.session, dimension, sid, other)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException):
        await scope_module.resolve_scope(
            estate.session, dimension, uuid.uuid4(), estate.project_id
        )

    own = await scope_module.resolve_scope(
        estate.session, dimension, sid, estate.project_id
    )
    assert own.ids == (sid,)
    bare = await scope_module.resolve_scope(estate.session, dimension, sid, None)
    assert bare.ids == (sid,)


# ---------- B4: pause refuses the proxy ----------


async def test_a_paused_connector_is_refused_and_not_marked_online(estate, redis):
    service, row, secret = await _connector(estate)
    row.paused = True
    await estate.session.flush()

    with pytest.raises(HTTPException) as exc:
        await router_module._authenticate(service, _request(), f"Bearer {secret}")
    assert exc.value.status_code == 403
    assert not await service._online(row.id)
    assert not redis.store.get("connector:token:203.0.113.7")

    row.paused = False
    await estate.session.flush()
    assert (
        await router_module._authenticate(service, _request(), f"Bearer {secret}")
    ).id == row.id
    assert await service._online(row.id)


# ---------- B5: a picked target claims its own hosts ----------


async def test_a_picked_target_keeps_only_the_hosts_it_holds(estate):
    picked = await estate.target("example.com")
    other = await estate.target("other.test")
    service, row, _ = await _connector(estate)
    await service.ingest(
        row,
        IngestRequest(
            target_id=picked,
            items=[
                IngestItem(url=f"https://{HOST}/a", status_code=200),
                IngestItem(url="https://cdn.other.test/b", status_code=200),
                IngestItem(url="https://tracker.example.net/c", status_code=200),
            ],
        ),
    )
    rows = {
        c.host: c.target_id
        for c in (
            await estate.session.execute(
                select(ConnectorCandidate).where(
                    ConnectorCandidate.connector_id == row.id
                )
            )
        ).scalars()
    }
    assert rows == {
        HOST: picked,
        "cdn.other.test": other,
        "tracker.example.net": None,
    }


async def test_scan_seeds_only_the_hosts_a_target_holds(estate, monkeypatch):
    target = await estate.target("example.com")
    service, row, _ = await _connector(estate)
    await service.ingest(
        row,
        IngestRequest(items=[IngestItem(url=f"https://{HOST}/a", status_code=200)]),
    )
    stray = ConnectorCandidate(
        connector_id=row.id,
        project_id=estate.project_id,
        target_id=target,
        signature="stray",
        url="https://evil.test/x",
        scheme="https",
        host="evil.test",
        path="/x",
        dir_path="/",
        source_tool="proxy",
        state=CandidateState.NEW.value,
    )
    estate.session.add(stray)
    await estate.session.flush()
    seeded: list[str] = []

    class _FakeScanService:
        def __init__(self, session):
            pass

        async def create(self, data, project_id, created_by):
            scan = Scan(
                project_id=project_id,
                target_id=data.target_id,
                engine_name="Rescan",
                execution_config={},
                created_by=created_by,
            )
            estate.session.add(scan)
            await estate.session.flush()
            seeded.extend(s.value for s in data.seed_assets)
            return scan

    monkeypatch.setattr("app.services.scan.ScanService", _FakeScanService)
    await service.scan(row.id, estate.project_id, estate.user_id)
    assert seeded == [f"https://{HOST}/a"]

    with pytest.raises(ConnectorError):
        await service.scan(row.id, estate.project_id, estate.user_id, [stray.id])


async def test_replay_writes_only_the_hosts_the_target_holds(estate, now):
    scan_id = await estate.scan("example.com", "live", at=now, status="running")
    service, row, _ = await _connector(estate)
    await service.ingest(
        row,
        IngestRequest(items=[IngestItem(url=f"https://{HOST}/x", status_code=200)]),
    )
    estate.session.add(
        ConnectorCandidate(
            connector_id=row.id,
            project_id=estate.project_id,
            target_id=estate.targets["example.com"],
            signature="stray",
            url="https://evil.test/y",
            scheme="https",
            host="evil.test",
            path="/y",
            dir_path="/",
            source_tool="proxy",
        )
    )
    await estate.activity("live", {"url_discovery": ScanActivityStatus.SUCCESS.value})
    scan = await estate.session.get(Scan, scan_id)
    replayed = await estate.session.run_sync(proxy_sync.replay, scan)

    assert replayed is not None
    assert replayed.created == 1
    hosts = {
        h
        for (h,) in await estate.session.execute(
            select(Endpoint.host).where(Endpoint.scan_id == scan_id)
        )
    }
    assert hosts == {HOST}


@pytest.mark.parametrize(
    ("kind", "value", "host", "held"),
    [
        (TargetType.DOMAIN, "example.com", "example.com", True),
        (TargetType.DOMAIN, "example.com", "a.b.example.com", True),
        (TargetType.DOMAIN, "example.com", "badexample.com", False),
        (TargetType.URL, "https://app.example.com/x", "app.example.com", True),
        (TargetType.URL, "https://app.example.com/x", "www.example.com", False),
        (TargetType.IP, "192.0.2.10", "192.0.2.10", True),
        (TargetType.IP, "192.0.2.10", "192.0.2.11", False),
        (TargetType.IP_RANGE, "192.0.2.0/24", "192.0.2.77", True),
        (TargetType.IP_RANGE, "2001:db8::/32", "2001:db8::1", True),
        (TargetType.IP_RANGE, "192.0.2.0/24", "app.example.com", False),
        (TargetType.ASN, "AS13335", "1.1.1.1", False),
    ],
)
def test_holds(kind, value, host, held):
    target = Target(
        project_id=uuid.uuid4(), target_value=value, target_type=kind, created_by=None
    )
    assert proxy_sync.holds(target, host) is held


# ---------- B6: the token limiter never refuses a valid token ----------


async def test_bad_tokens_from_an_address_do_not_lock_out_a_valid_one(estate, redis):
    service, row, secret = await _connector(estate)
    bad = f"Bearer {auth.mint()[0]}"
    for _ in range(router_module.TOKEN_ATTEMPT_LIMIT):
        with pytest.raises(HTTPException) as exc:
            await router_module._authenticate(service, _request(), bad)
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        await router_module._authenticate(service, _request(), bad)
    assert exc.value.status_code == 429

    good = await router_module._authenticate(service, _request(), f"Bearer {secret}")
    assert good.id == row.id
    with pytest.raises(HTTPException) as exc:
        await router_module._authenticate(service, _request(), bad)
    assert exc.value.status_code == 429, "a valid token does not reset the budget"


# ---------- B7: the issuer must still be a superuser ----------


async def test_a_token_stops_working_when_its_issuer_loses_admin(estate, redis):
    service, row, secret = await _connector(estate)
    assert await service.authenticate(secret) is not None

    issuer = await estate.session.get(User, estate.user_id)
    issuer.is_superuser = False
    await estate.session.flush()
    assert await service.authenticate(secret) is None

    issuer.is_superuser = True
    row.created_by = None
    await estate.session.flush()
    assert await service.authenticate(secret) is None
