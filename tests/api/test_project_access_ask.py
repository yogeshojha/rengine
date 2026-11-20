"""Project access in Ask, chat, MCP scope, the toolbox and WHOIS, below the route walk."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.api.v1 import toolbox as toolbox_api
from app.api.v1 import whois as whois_api
from app.services.ask.estate.service import EstateService
from app.services.ask.estate.service import reply as estate_reply
from app.services.ask.service import AskService
from app.services.ask.service import reply as asset_reply
from channels.dispatch import Dispatcher
from channels.identity import identity_for
from channels.models import ChannelChat
from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext
from mcp.errors import ScopeError
from mcp.tools._scope import find_target, project_for
from shared.definitions.toolbox import RunStatus, ToolRunRequest
from shared.enums.target import TargetType
from shared.enums.whois import WhoisLookupType
from shared.models.ask import AskQuestion, EstateQuestion
from shared.models.target import Target
from shared.models.whois import WhoisRecord, WhoisRecordRead
from shared.services.project_access import EVERY_PROJECT
from shared.utils.datetime import utc_now
from tests.conftest import ask_threads
from tools.whois.service import WhoisService

pytestmark = pytest.mark.api


@pytest.fixture
async def world(estate):
    other = await estate.sibling(name="Theirs")
    member = await estate.member(estate.project_id)
    mine = await estate.target("mine.example")
    theirs = await other.target("theirs.example")
    own = await ask_threads(estate, "own", member.id, mine)
    lost = await ask_threads(other, "lost", member.id, theirs)
    return {
        "estate": estate,
        "other": other,
        "member": member,
        "access": frozenset({estate.project_id}),
        "mine": mine,
        "theirs": theirs,
        "own": own,
        "lost": lost,
    }


async def _frames(stream) -> list[tuple[str, dict]]:
    out = []
    async for chunk in stream:
        head, data = chunk.strip().split("\n", 1)
        out.append((head.removeprefix("event: "), json.loads(data[len("data: ") :])))
    return out


# ---------- ask ----------


async def test_an_asset_thread_of_a_closed_project_is_not_found(world):
    service = AskService(world["estate"].session)
    member, access = world["member"], world["access"]
    lost, own = world["lost"]["thread_id"], world["own"]["thread_id"]

    assert await service.get(member.id, own, access) is not None
    assert await service.get(member.id, lost, access) is None
    assert await service.get(member.id, lost, EVERY_PROJECT) is not None
    assert await service.detail(member.id, lost, access) is None
    assert await service.delete(member.id, lost, access) is False
    assert await service.get(member.id, lost, EVERY_PROJECT) is not None


async def test_asset_threads_of_a_closed_project_are_not_listed_or_cleared(world):
    service = AskService(world["estate"].session)
    member, access = world["member"], world["access"]
    args = (world["theirs"], "vulnerabilities", "lost-fp")

    assert await service.threads(member.id, access, *args) == []
    assert len(await service.threads(member.id, EVERY_PROJECT, *args)) == 1
    assert await service.delete_all(member.id, access, *args) == 0
    assert len(await service.threads(member.id, EVERY_PROJECT, *args)) == 1


async def test_an_estate_thread_of_a_closed_project_is_not_found(world):
    service = EstateService(world["estate"].session)
    member, access = world["member"], world["access"]
    lost = world["lost"]["estate_thread_id"]

    assert await service.get(member.id, world["own"]["estate_thread_id"], access)
    assert await service.get(member.id, lost, access) is None
    assert await service.detail(member.id, lost, access) is None
    assert await service.blocks(member.id, lost, access) is None
    for call in (
        service.page(member.id, lost, access, "B1", 0),
        service.edit(member.id, lost, access, "B1", "tech:x"),
    ):
        with pytest.raises(HTTPException) as refused:
            await call
        assert refused.value.status_code == 404
    assert await service.delete(member.id, lost, access) is False
    assert await service.get(member.id, lost, EVERY_PROJECT) is not None


async def test_a_turn_rereads_the_access(world, monkeypatch):
    from app.services.ask.estate import service as estate_service  # noqa: PLC0415

    async def free(_thread_id):
        return "t"

    async def release(_thread_id, _token):
        return None

    monkeypatch.setattr(estate_service.busy, "claim", free)
    monkeypatch.setattr(estate_service.busy, "release", release)
    session, member = world["estate"].session, world["member"]

    asked = await _frames(
        asset_reply(
            session,
            thread_id=world["lost"]["thread_id"],
            user=member,
            question=AskQuestion(text="still?", scan_id=uuid.uuid4()),
        )
    )
    across = await _frames(
        estate_reply(
            session,
            thread_id=world["lost"]["estate_thread_id"],
            user=member,
            question=EstateQuestion(text="still?"),
        )
    )
    assert asked == [("error", {"message": "Thread not found."})]
    assert across == [("error", {"message": estate_service.THREAD_NOT_FOUND})]


# ---------- mcp scope ----------


def _ctx(session, project_id, projects) -> ToolContext:
    return ToolContext(
        session=session,
        token=TokenIdentity(
            id=uuid.uuid4(),
            name="chat",
            project_id=project_id,
            capabilities=frozenset({Capability.READ.value}),
            projects=projects,
        ),
        ui_base_url="http://ui",
    )


async def test_an_identity_reads_the_member_projects(world):
    estate, other = world["estate"], world["other"]
    session, access = estate.session, world["access"]

    free = _ctx(session, None, access)
    assert free.scoped_projects() == [estate.project_id]
    assert await project_for(free, None) == estate.project_id
    with pytest.raises(ScopeError):
        free.check_project(other.project_id)
    assert (await find_target(free, "mine.example")).id == world["mine"]
    with pytest.raises(Exception, match="No target matches"):
        await find_target(free, "theirs.example")

    pinned = _ctx(session, other.project_id, access)
    assert pinned.scoped_projects() == []
    with pytest.raises(ScopeError):
        await project_for(pinned, None)

    admin = _ctx(session, None, EVERY_PROJECT)
    assert admin.scoped_projects() is None
    assert (await find_target(admin, "theirs.example")).id == world["theirs"]


# ---------- chat ----------


class _Channel:
    kind = "telegram"

    def __init__(self):
        self.sent: list[str] = []

    async def reply(self, _external_id, lines):
        self.sent.append(" ".join(s.text for ln in lines for s in ln))


def _chat(user_id, project_id) -> ChannelChat:
    return ChannelChat(
        channel="telegram",
        external_id="1",
        user_id=user_id,
        project_id=project_id,
        capabilities=["read"],
    )


async def test_a_chat_bound_to_a_closed_project_has_none(world):
    member, access, other = world["member"], world["access"], world["other"]
    chat = _chat(member.id, other.project_id)

    identity = identity_for(chat, member, {"read": True}, access)
    assert identity.project_id is None
    assert identity.projects == access
    assert identity_for(chat, member, {"read": True}, EVERY_PROJECT).project_id == (
        other.project_id
    )


async def test_chat_lists_and_picks_member_projects_only(world):
    session, member, access = world["estate"].session, world["member"], world["access"]
    channel = _Channel()
    dispatcher = Dispatcher(channel, None, "http://ui")
    chat = _chat(member.id, world["other"].project_id)

    listed = " ".join(
        " ".join(s.text for s in ln)
        for ln in await dispatcher._projects(session, chat, access)
    )
    assert "Test" in listed
    assert "Theirs" not in listed

    whoami = " ".join(
        " ".join(s.text for s in ln)
        for ln in await dispatcher._whoami(session, _settings(), chat, member, access)
    )
    assert "none selected" in whoami

    parsed = type("Parsed", (), {"bare": ["Theirs"]})()
    await dispatcher._project(session, chat, parsed, access)
    assert chat.project_id == world["other"].project_id
    assert "No project matches Theirs" in channel.sent[-1]


async def test_a_queued_chat_run_is_not_delivered_once_its_project_closes(
    world, monkeypatch
):
    from contextlib import asynccontextmanager  # noqa: PLC0415

    from channels import dispatch  # noqa: PLC0415
    from toolbox import store  # noqa: PLC0415

    session, member = world["estate"].session, world["member"]
    runs = {}

    def queued(project_id):
        run = store.new_run(
            tool="subdomains",
            title="Subdomains",
            label="example.com",
            payload={},
            status=RunStatus.COMPLETED.value,
            project_id=project_id,
        )
        run.summary = "QZCANARY 3 of 4 in inventory"
        runs[run.id] = run
        return run.id

    async def get(_user_id, run_id):
        return runs.get(run_id)

    async def record(*_args, **_kwargs):
        return None

    @asynccontextmanager
    async def sessions():
        yield session

    monkeypatch.setattr(store, "get", get)
    monkeypatch.setattr(dispatch.telemetry, "record", record)
    monkeypatch.setattr(dispatch, "FOLLOW_POLL_SECONDS", 0)
    channel = _Channel()
    dispatcher = Dispatcher(channel, sessions, "http://ui")
    identity = identity_for(
        _chat(member.id, world["estate"].project_id),
        member,
        {"read": True},
        world["access"],
    )

    async def follow(run_id):
        await dispatcher._follow_run(member.id, run_id, "1", identity, "t", "/subs")
        return channel.sent[-1]

    assert "QZCANARY" in await follow(queued(world["estate"].project_id))
    assert await follow(queued(world["other"].project_id)) == "Run expired."
    member.is_active = False
    await session.flush()
    assert await follow(queued(world["estate"].project_id)) == "Run expired."


def _settings():
    from channels import settings  # noqa: PLC0415

    return settings.read(None)


# ---------- toolbox ----------


async def test_a_toolbox_run_on_a_closed_project_is_not_found(world):
    session, member = world["estate"].session, world["member"]
    body = ToolRunRequest(tool="nosuch", project_id=str(world["other"].project_id))
    with pytest.raises(HTTPException) as refused:
        await toolbox_api.run_tool(body, member, world["access"], session)
    assert (refused.value.status_code, refused.value.detail) == (
        404,
        "Project not found.",
    )
    own = ToolRunRequest(tool="nosuch", project_id=str(world["estate"].project_id))
    with pytest.raises(HTTPException) as missing:
        await toolbox_api.run_tool(own, member, world["access"], session)
    assert missing.value.detail == "No tool called 'nosuch'."


# ---------- whois ----------


async def _record(session, value: str, holder: uuid.UUID | None) -> WhoisRecord:
    row = WhoisRecord(
        query_value=value,
        lookup_type=WhoisLookupType.DOMAIN,
        registrant_name="Acme Holdings",
        network_cidr="192.0.2.0/24",
    )
    session.add(row)
    await session.flush()
    if holder is not None:
        target = await session.get(Target, holder)
        target.whois_record_id = row.id
        await session.flush()
    return row


async def test_a_whois_record_of_a_closed_project_is_not_found(world):
    session, member, access = world["estate"].session, world["member"], world["access"]
    theirs = await _record(session, "theirs.example", world["theirs"])
    mine = await _record(session, "mine.example", world["mine"])
    loose = await _record(session, "loose.example", None)

    read = await whois_api.get_whois_record(mine.id, member, access, session)
    assert read.query_value == "mine.example"
    for record_id in (theirs.id, loose.id, uuid.uuid4()):
        with pytest.raises(HTTPException) as refused:
            await whois_api.get_whois_record(record_id, member, access, session)
        assert refused.value.detail == "WHOIS record not found."
        with pytest.raises(HTTPException):
            await whois_api.refresh_whois_record(record_id, member, access, session)
    for row in (theirs, loose):
        admin = await whois_api.get_whois_record(row.id, member, EVERY_PROJECT, session)
        assert admin.query_value == row.query_value


async def test_whois_correlations_read_open_projects_only(world):
    session, member, access = world["estate"].session, world["member"], world["access"]
    estate = world["estate"]
    await _record(session, "theirs.example", world["theirs"])
    await _record(session, "mine.example", world["mine"])
    await _record(session, "loose.example", None)
    service = whois_api.get_whois_service()

    found = await whois_api.correlate_by_registrant(
        member, access, session, service, "Acme Holdings", estate.project_id
    )
    assert [(r.query_value, found[0].count) for r in found[0].records] == [
        ("mine.example", 1)
    ]
    network = await whois_api.correlate_by_network(
        member, access, session, service, "192.0.2.0/24", estate.project_id
    )
    assert [r.query_value for r in network[0].records] == ["mine.example"]
    every = await whois_api.correlate_by_registrant(
        member, EVERY_PROJECT, session, service, "Acme Holdings", estate.project_id
    )
    assert every[0].count == 3

    ids = f"{world['mine']},{world['theirs']}"
    by_target = await whois_api.get_targets_correlations(member, access, session, ids)
    assert set(by_target) == {str(world["mine"])}
    closed = await whois_api.get_target_correlations(
        str(world["theirs"]), member, access, session
    )
    assert closed == []


class _LookedUpError(Exception):
    pass


async def test_a_whois_record_another_project_holds_is_looked_up_again(
    world, monkeypatch
):
    session = world["estate"].session
    row = await _record(session, "theirs.example", world["theirs"])
    row.queried_at = utc_now() - timedelta(days=1)
    await session.flush()
    service = WhoisService()

    def looked(*_args, **_kwargs):
        raise _LookedUpError

    monkeypatch.setattr(service, "do_lookup", looked)

    def fetch(projects):
        return lambda sync: service.get_or_create_record_sync(
            sync, "theirs.example", TargetType.DOMAIN, projects=projects
        )

    held = await session.run_sync(fetch({world["other"].project_id}))
    assert held.id == row.id
    with pytest.raises(_LookedUpError):
        await session.run_sync(fetch({world["estate"].project_id}))
    with pytest.raises(_LookedUpError):
        await session.run_sync(
            fetch({world["estate"].project_id, world["other"].project_id})
        )
    assert "created_at" not in WhoisRecordRead.model_fields
    assert "updated_at" not in WhoisRecordRead.model_fields
