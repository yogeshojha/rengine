"""MCP agent tokens and Ask: secrets, scope, limits and the call log."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.v1 import mcp as mcp_route
from app.core.security import hash_password
from app.services.ask import budget, tools
from mcp import auth, server, telemetry
from mcp import settings as server_settings
from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext, Transport
from mcp.errors import UNAUTHORIZED, AuthError, ScopeError, ToolError
from mcp.models import McpToken
from mcp.protocol import Request as RpcRequest
from mcp.registry import get as tool_spec
from mcp.result import ToolResult
from mcp.service import McpService
from mcp.tools import _scope
from shared.definitions.ask import ASK_CLIENT
from shared.models.user import User
from shared.services.ai import AIError
from shared.services.ai.agent import CALL, DONE, TEXT, AgentEvent
from shared.services.scan_resolve import MASK
from tests.api.test_ask_service import (
    _cfg,
    _cfg_loader,
    _collect,
    _fake_converse,
    _finding,
    _fp,
    _never,
    _not_over,
    flush_only,  # noqa: F401
)

pytestmark = pytest.mark.api

AWS_KEY = "AKIA" + "Q3WK9ZL2MX7VP4NR"
PLAIN = "Vq7#mT9!pLx2@wRz"


@pytest.fixture
def quiet(monkeypatch):
    calls: list[telemetry.CallRecord] = []

    async def record(call):
        calls.append(call)

    async def touch(**_kwargs):
        return None

    monkeypatch.setattr(telemetry, "record", record)
    monkeypatch.setattr(telemetry, "touch", touch)
    return calls


def _identity(estate, **extra) -> TokenIdentity:
    return TokenIdentity(
        id=estate.user_id,
        name="agent",
        project_id=estate.project_id,
        capabilities=frozenset({Capability.READ.value}),
        issued_by=estate.user_id,
        **extra,
    )


# ---------- C1 ----------


def test_explain_finding_hides_values_a_credential_check_extracted():
    payload = {
        "data": {
            "check": {"template_id": "github-token-exposure", "tags": ["exposure"]},
            "evidence": {"extracted": ["opaque-token-value", "second"]},
        }
    }
    out = tools.hide_extracted("explain_finding", payload)
    assert out["data"]["evidence"]["extracted"] == [MASK, MASK]


def test_explain_finding_keeps_values_of_other_checks():
    payload = {
        "data": {
            "check": {"template_id": "apache-detect", "tags": ["tech"]},
            "evidence": {"extracted": ["Apache/2.4.1"]},
        }
    }
    out = tools.hide_extracted("explain_finding", payload)
    assert out["data"]["evidence"]["extracted"] == ["Apache/2.4.1"]


def test_compare_runs_masks_extracted_changes():
    payload = {
        "data": {
            "changes": [
                {
                    "fields": [
                        {"field": "Extracted", "was": "old-secret", "now": "new"},
                        {"field": "Severity", "was": "low", "now": "high"},
                        {"field": "Extracted", "was": None, "now": "x"},
                    ]
                }
            ]
        }
    }
    fields = tools.hide_extracted("compare_runs", payload)["data"]["changes"][0][
        "fields"
    ]
    assert fields[0] == {"field": "Extracted", "was": MASK, "now": MASK}
    assert fields[1] == {"field": "Severity", "was": "low", "now": "high"}
    assert fields[2] == {"field": "Extracted", "was": None, "now": MASK}


async def test_the_text_handed_to_the_provider_carries_no_extracted_value(
    monkeypatch, estate
):
    await estate.target("example.com")
    secret = "zq9c1opaquevalue"

    async def invoke(_ctx, _name, _args):
        return ToolResult(
            summary="one",
            data={
                "check": {"template_id": "slack-token", "tags": ["token"]},
                "evidence": {"extracted": [secret]},
            },
        )

    monkeypatch.setattr(tools.server, "invoke", invoke)
    ctx = ToolContext(
        session=estate.session,
        token=_identity(estate, targets=frozenset({estate.targets["example.com"]})),
        ui_base_url="",
    )
    text, step = await tools.call(ctx, "explain_finding", {"target": "example.com"})
    assert step.status == "done"
    assert secret not in text
    assert json.loads(text)["data"]["evidence"]["extracted"] == [MASK]


# ---------- C2 ----------


@pytest.mark.parametrize("name", ["add_target", "start_scan", "list_projects", "nope"])
async def test_ask_refuses_a_tool_it_did_not_offer(monkeypatch, name):
    async def boom(*_args, **_kwargs):
        msg = "invoked"
        raise AssertionError(msg)

    monkeypatch.setattr(tools.server, "invoke", boom)
    text, step = await tools.call(None, name, {})
    assert text == tools.NOT_OFFERED
    assert step.status == "failed"


async def test_ask_identity_is_pinned_to_its_target(estate):
    target = await estate.target("example.com")
    user = await estate.session.get(User, estate.user_id)
    identity = tools.identity_for(user, estate.project_id, target)
    assert identity.targets == frozenset({target})


async def test_ask_refuses_a_call_with_no_thread(monkeypatch, estate):
    async def boom(*_args, **_kwargs):
        msg = "invoked"
        raise AssertionError(msg)

    monkeypatch.setattr(tools.server, "invoke", boom)
    ctx = ToolContext(
        session=estate.session,
        token=_identity(estate),
        ui_base_url="",
        client=ASK_CLIENT,
    )
    text, _ = await tools.call(ctx, "list_targets", {})
    assert text == tools.NO_THREAD


async def test_a_target_scope_hides_every_other_target(estate, quiet):
    own = await estate.target("example.com")
    await estate.target("other.com")
    ctx = ToolContext(
        session=estate.session,
        token=_identity(estate, targets=frozenset({own})),
        ui_base_url="",
    )
    listed = await server.invoke(ctx, "list_targets", {})
    assert [t["value"] for t in listed.data["targets"]] == ["example.com"]
    with pytest.raises(ToolError, match="No target matches"):
        await _scope.find_target(ctx, "other.com")
    assert (await _scope.find_target(ctx, "example.com")).id == own


async def test_a_target_scope_refuses_another_targets_run(estate, now):
    await estate.target("example.com")
    other = await estate.scan("other.com", "other", at=now)
    ctx = ToolContext(
        session=estate.session,
        token=_identity(estate, targets=frozenset({estate.targets["example.com"]})),
        ui_base_url="",
    )
    from shared.models.scan import Scan  # noqa: PLC0415

    with pytest.raises(ScopeError):
        await _scope.scan_in_scope(ctx, await estate.session.get(Scan, other))


# ---------- C3 ----------


async def test_the_daily_cap_fails_closed(monkeypatch):
    def down():
        msg = "redis down"
        raise ConnectionError(msg)

    monkeypatch.setattr(budget, "async_client", down)
    with pytest.raises(AIError, match="question counter is unavailable"):
        await budget.over_daily(uuid.uuid4())


# ---------- C4 ----------


async def _user(session, *, superuser: bool, active: bool = True) -> User:
    tag = uuid.uuid4().hex[:8]
    user = User(
        username=f"mcp{tag}",
        email=f"mcp{tag}@test.local",
        hashed_password=hash_password(PLAIN),
        is_superuser=superuser,
        is_active=active,
    )
    session.add(user)
    await session.flush()
    return user


async def _token(session, issuer: uuid.UUID | None) -> str:
    secret, digest, prefix = auth.mint()
    session.add(
        McpToken(
            name=f"t{uuid.uuid4().hex[:6]}",
            capabilities=[Capability.READ.value],
            token_hash=digest,
            token_prefix=prefix,
            created_by=issuer,
        )
    )
    await session.flush()
    return secret


@pytest.fixture
def config(monkeypatch):
    async def read(_self):
        return server_settings.ServerSettings(enabled=True)

    monkeypatch.setattr(McpService, "config", read)


@pytest.mark.parametrize(
    ("superuser", "active", "works"),
    [(True, True, True), (False, True, False), (True, False, False)],
)
async def test_a_token_needs_an_active_superuser_issuer(
    session, config, superuser, active, works
):
    issuer = await _user(session, superuser=superuser, active=active)
    secret = await _token(session, issuer.id)
    service = McpService(session)
    if works:
        identity, _ = await service.authenticate(secret)
        assert identity.issued_by == issuer.id
    else:
        with pytest.raises(AuthError, match="not an active administrator"):
            await service.authenticate(secret)


async def test_a_token_with_no_issuer_is_refused(session, config):
    secret = await _token(session, None)
    with pytest.raises(AuthError):
        await McpService(session).authenticate(secret)


async def test_token_reads_name_the_issuer(session, config):
    admin = await _user(session, superuser=True)
    demoted = await _user(session, superuser=False)
    await _token(session, admin.id)
    await _token(session, demoted.id)
    rows = {t.issuer: t.issuer_valid for t in await McpService(session).tokens()}
    assert rows[admin.username] is True
    assert rows[demoted.username] is False


# ---------- C5 ----------


async def test_a_declared_name_never_becomes_the_transport_tag(quiet):
    token = TokenIdentity(
        id=uuid.uuid4(), name="agent", project_id=None, capabilities=frozenset()
    )
    ctx = ToolContext(
        session=None, token=token, ui_base_url="", client=Transport.HTTP.value
    )
    request = RpcRequest(
        id=1, method="initialize", params={"clientInfo": {"name": ASK_CLIENT}}
    )
    await server.handle(request, ctx)
    with pytest.raises(ToolError):
        await server.invoke(ctx, "nope", {})
    assert ctx.client == Transport.HTTP.value
    assert ctx.agent == ASK_CLIENT
    assert quiet[0].client == Transport.HTTP.value
    assert quiet[0].agent == ASK_CLIENT


async def test_the_call_log_filters_on_the_tag(monkeypatch):
    entries = [
        {"client": "http", "agent": "telegram", "tool": "a"},
        {"client": "telegram", "agent": None, "tool": "b"},
        {"client": "ask", "agent": None, "tool": "c"},
        {"client": "http", "agent": "ask", "tool": "d"},
    ]

    class Redis:
        async def lrange(self, *_args):
            return [json.dumps(e) for e in entries]

    monkeypatch.setattr(telemetry, "async_client", Redis)
    telegram = await telemetry.recent(10, client="telegram")
    assert [e["tool"] for e in telegram] == ["b"]
    shown = await telemetry.recent(10, without=("telegram", "ask"))
    assert [e["tool"] for e in shown] == ["a", "d"]


async def test_status_leaves_sessions_out_for_a_non_admin(monkeypatch, session):
    async def live():
        return [{"token_id": str(uuid.uuid4()), "client": "http", "last_seen": "x"}]

    async def config(_self):
        return server_settings.ServerSettings()

    monkeypatch.setattr(telemetry, "sessions", live)
    monkeypatch.setattr(McpService, "config", config)
    status = await McpService(session).status("http://ui", sessions=False)
    assert status.sessions == []


def test_the_call_log_route_is_superuser_only():
    route = next(r for r in mcp_route.router.routes if r.path == "/mcp/calls")
    names = {d.call.__name__ for d in route.dependant.dependencies}
    assert "get_current_superuser" in names


# ---------- C6 ----------


def test_call_arguments_lose_url_queries_and_secrets():
    line = telemetry.phrase_args(
        {
            "query": f"host:x and body:{AWS_KEY}",
            "url": "https://example.com/a?api_key=abc123secret",
            "targets": [f"https://x.test/?t={AWS_KEY}", "plain.example"],
        }
    )
    assert AWS_KEY not in line
    assert "abc123secret" not in line
    assert "plain.example" in line


async def test_an_unexpected_tool_error_keeps_its_text_out(monkeypatch, quiet):
    class BrokenError(Exception):
        pass

    spec = tool_spec("list_targets")

    async def run(_self, _ctx, _args):
        msg = "[parameters: ('s3cr3t-value',)]"
        raise BrokenError(msg)

    monkeypatch.setattr(spec.tool_cls, "run", run)
    token = TokenIdentity(
        id=uuid.uuid4(),
        name="agent",
        project_id=None,
        capabilities=frozenset({Capability.READ.value}),
    )
    ctx = ToolContext(session=None, token=token, ui_base_url="")
    with pytest.raises(ToolError) as raised:
        await server.invoke(ctx, "list_targets", {})
    assert "s3cr3t" not in raised.value.message
    assert "BrokenError" in raised.value.message
    assert "s3cr3t" not in (quiet[-1].detail or "")


def test_a_service_refusal_keeps_its_wording():
    exc = HTTPException(status_code=422, detail="The runs are not comparable.")
    assert server.failed("Compare runs", exc) == "The runs are not comparable."


# ---------- C7 ----------


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/mcp",
            "headers": [],
            "client": ("203.0.113.9", 1234),
        }
    )


@pytest.mark.parametrize("valid", [True, False])
async def test_the_limiter_reads_only_rejected_tokens(monkeypatch, valid):
    checked: list[str] = []
    failed: list[str] = []

    async def handle(*_args, **_kwargs):
        if valid:
            return {"jsonrpc": "2.0", "id": 1, "result": {}}
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": UNAUTHORIZED, "message": "The token is not valid."},
        }

    async def over(key, *, limit):
        checked.append(key)
        raise HTTPException(status_code=429, detail="Too many attempts.")

    async def record(key, *, window_seconds):
        failed.append(key)

    monkeypatch.setattr(mcp_route, "handle_request", handle)
    monkeypatch.setattr(mcp_route, "too_many_attempts", over)
    monkeypatch.setattr(mcp_route, "record_failure", record)
    if valid:
        answer = await mcp_route.mcp_endpoint(None, _request(), {"method": "ping"})
        assert answer["result"] == {}
        assert checked == []
    else:
        with pytest.raises(HTTPException) as raised:
            await mcp_route.mcp_endpoint(None, _request(), {"method": "ping"})
        assert raised.value.status_code == 429
        assert checked == ["mcp:token:203.0.113.9"]


# ---------- C8 ----------


async def test_start_scan_refuses_a_new_target_without_write(estate, quiet):
    token = TokenIdentity(
        id=uuid.uuid4(),
        name="agent",
        project_id=estate.project_id,
        capabilities=frozenset({Capability.READ.value, Capability.LAUNCH.value}),
        issued_by=estate.user_id,
    )
    ctx = ToolContext(session=estate.session, token=token, ui_base_url="")
    with pytest.raises(ToolError, match="needs the write capability"):
        await server.invoke(ctx, "start_scan", {"target": "brand-new.example"})


async def test_start_scan_names_an_existing_target_by_id(estate):
    from mcp.tools.start_scan import _target_of  # noqa: PLC0415

    target = await estate.target("example.com")
    token = TokenIdentity(
        id=uuid.uuid4(),
        name="agent",
        project_id=estate.project_id,
        capabilities=frozenset({Capability.READ.value, Capability.LAUNCH.value}),
        issued_by=estate.user_id,
    )
    ctx = ToolContext(session=estate.session, token=token, ui_base_url="")
    assert await _target_of(ctx, " Example.COM ", estate.project_id) == {
        "target_id": target
    }
    writer = ToolContext(
        session=estate.session,
        token=TokenIdentity(
            id=token.id,
            name="agent",
            project_id=estate.project_id,
            capabilities=frozenset({Capability.WRITE.value, Capability.LAUNCH.value}),
            issued_by=estate.user_id,
        ),
        ui_base_url="",
    )
    assert await _target_of(writer, "new.example", estate.project_id) == {
        "target_value": "new.example"
    }


# ---------- through the reply ----------


@pytest.fixture
async def asked(estate, now, monkeypatch, flush_only):  # noqa: F811
    from app.services.ask import service as ask_service  # noqa: PLC0415
    from app.services.ask.service import AskService  # noqa: PLC0415
    from shared.models.ask import AskThreadCreate  # noqa: PLC0415

    await estate.scan("example.com", "run", at=now)
    await estate.scan("other.com", "other", at=now)
    fp = _fp()
    await _finding(estate, at=now, fp=fp)
    monkeypatch.setattr(ask_service, "load_config_async", _cfg_loader(_cfg()))
    monkeypatch.setattr(ask_service.limits, "exceeded", _never)
    thread = await AskService(estate.session).create(
        estate.user_id,
        estate.project_id,
        AskThreadCreate(target_id=estate.targets["example.com"], asset_key=fp),
    )
    user = await estate.session.get(User, estate.user_id)
    return {"thread": thread, "user": user, "service": ask_service}


async def _reply(estate, asked, events, seen, monkeypatch):
    from app.services.ask.service import reply  # noqa: PLC0415
    from shared.models.ask import AskQuestion  # noqa: PLC0415

    monkeypatch.setattr(asked["service"], "converse", _fake_converse(events, seen))
    return await _collect(
        reply(
            estate.session,
            thread_id=asked["thread"].id,
            user=asked["user"],
            question=AskQuestion(text="Where else?", scan_id=estate.scans["run"]),
        )
    )


async def test_a_reply_reads_its_own_target_only(estate, asked, monkeypatch):
    monkeypatch.setattr(asked["service"].budget, "over_daily", _not_over)
    seen: dict = {}
    events = [
        AgentEvent(CALL, name="list_targets", args={}),
        AgentEvent(CALL, name="resolve_target", args={"target": "other.com"}),
        AgentEvent(CALL, name="add_target", args={"targets": ["x.example"]}),
        AgentEvent(TEXT, text="Only example.com."),
        AgentEvent(DONE, model="m"),
    ]
    await _reply(estate, asked, events, seen, monkeypatch)
    listed, other, added = seen["tool_text"]
    assert "example.com" in listed
    assert "other.com" not in listed
    assert "No target matches" in other
    assert tools.NOT_OFFERED in added


async def test_a_reply_is_refused_when_the_counter_is_down(estate, asked, monkeypatch):
    def down():
        msg = "redis down"
        raise ConnectionError(msg)

    monkeypatch.setattr(budget, "async_client", down)
    frames = await _reply(estate, asked, [], {}, monkeypatch)
    assert frames == [("error", {"message": budget.COUNTER_DOWN})]
