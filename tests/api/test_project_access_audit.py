"""Project access: answers that told a member about a project it cannot open."""

from __future__ import annotations

import asyncio
import re
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from shared.definitions.bounty_programs import ProgramState, SubmissionState
from shared.definitions.investigate import PlanState
from shared.models.ai import AiCall
from shared.models.bounty_program import BountyEventRow, BountyProgram
from shared.models.investigate import Investigation, InvestigationPlan
from shared.models.project import ProjectCreate
from shared.models.user import User
from shared.models.watch import ProgramWatch
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.api


async def _refused(call) -> HTTPException:
    with pytest.raises(HTTPException) as caught:
        await call
    return caught.value


# ---------- project slugs ----------


async def test_a_members_project_slug_says_nothing_of_other_projects(
    estate, flush_only, monkeypatch
):
    from app.api.v1 import projects as projects_api  # noqa: PLC0415

    async def builtin(*_args):
        return None

    monkeypatch.setattr(projects_api.ScanEngineService, "ensure_builtin", builtin)
    hidden = await estate.sibling(name="Acme Hidden")
    member = await estate.member(estate.project_id, can_create_projects=True)
    admin = await flush_only.get(User, estate.user_id)

    request = SimpleNamespace(state=SimpleNamespace())
    taken = await projects_api.create_project(
        ProjectCreate(name=hidden.slug), member, flush_only, request
    )
    free = await projects_api.create_project(
        ProjectCreate(name="nothing like it"), member, flush_only, request
    )
    assert re.fullmatch(rf"{re.escape(hidden.slug)}-[0-9a-f]{{8}}", taken.slug)
    assert re.fullmatch(r"nothing-like-it-[0-9a-f]{8}", free.slug)
    named = await projects_api.create_project(
        ProjectCreate(name="Admin Named"), admin, flush_only, request
    )
    assert named.slug == "admin-named"


# ---------- investigate ----------


async def test_another_projects_plan_reads_as_an_unknown_one(estate, flush_only):
    from app.services.investigate.service import InvestigateService  # noqa: PLC0415

    other = await estate.sibling()
    b = await other.canary("planrows", utc_now())
    inv = Investigation(
        project_id=other.project_id,
        target_id=b["target_id"],
        scan_id=b["scan_id"],
        fingerprint=b["fingerprint"],
    )
    flush_only.add(inv)
    await flush_only.flush()
    plan = InvestigationPlan(investigation_id=inv.id, template_id="t", host="h.test")
    flush_only.add(plan)
    await flush_only.flush()
    service = InvestigateService(flush_only)
    member = await estate.member(estate.project_id)

    for ids in ([plan.id], [uuid.uuid4()]):
        declined = await _refused(service.decline(estate.project_id, ids))
        approved = await _refused(service.approve(member, estate.project_id, ids))
        assert (declined.status_code, declined.detail) == (
            404,
            "Investigation not found.",
        )
        assert (approved.status_code, approved.detail) == (
            404,
            "Investigation not found.",
        )
    assert plan.state == PlanState.PROPOSED.value


# ---------- connector handoff ----------


async def test_another_projects_rows_hand_off_as_unknown_ones(estate, flush_only):
    from app.services.connector import ConnectorService  # noqa: PLC0415
    from shared.models.connector import HandoffRequest  # noqa: PLC0415

    a = await estate.canary("ownrows", utc_now())
    other = await estate.sibling()
    b = await other.canary("handrows", utc_now())
    service = ConnectorService(flush_only)
    fields = {
        "finding_ids": ("vulnerability_id", "Finding"),
        "asset_ids": ("asset_id", "Web asset"),
        "endpoint_ids": ("endpoint_id", "Endpoint"),
        "host_ids": ("subdomain_id", "Web asset"),
    }
    for field, (key, noun) in fields.items():
        for ids in ([b[key]], [uuid.uuid4()], [a[key], b[key]]):
            body = HandoffRequest(**{field: ids})
            refused = await _refused(
                service.handoff(a["connector_id"], estate.project_id, body)
            )
            assert (refused.status_code, refused.detail) == (404, f"{noun} not found.")


# ---------- event stream ----------


async def test_a_stream_ends_once_the_users_sessions_are_revoked(estate, monkeypatch):
    from app.api import deps  # noqa: PLC0415
    from app.api.v1 import events  # noqa: PLC0415
    from app.core.security import ISSUED_MS_CLAIM  # noqa: PLC0415

    member = await estate.member(estate.project_id)
    channel = f"project:{estate.project_id}"
    issued = 1_000
    cutoff: list[int | None] = [None]

    async def valid_after(_user_id):
        return cutoff[0]

    @asynccontextmanager
    async def stream(_channels, _owner, *, claimed=False):
        queue = asyncio.Queue()
        for n in range(3):
            queue.put_nowait(f"data: {n}\n\n")
        yield queue

    class Request:
        async def is_disconnected(self):
            return False

    monkeypatch.setattr(deps, "tokens_valid_after", valid_after)
    monkeypatch.setattr(events, "decode_token", lambda _t: {ISSUED_MS_CLAIM: issued})
    monkeypatch.setattr(events.sse_manager, "stream", stream)

    async def first_two():
        response = await events.event_stream(
            Request(), member, "token", frozenset({estate.project_id}), channel
        )
        frames = []
        async for frame in response.body_iterator:
            frames.append(frame)
            if len(frames) == 2:
                break
        await response.body_iterator.aclose()
        events.sse_manager.release(str(member.id))
        return frames

    assert await first_two() == ["data: 0\n\n", "data: 1\n\n"]
    cutoff[0] = issued + 1
    assert await first_two() == ["event: unauthorized\ndata: {}\n\n"]


# ---------- bounty change alerts ----------


async def test_a_watched_programs_changes_alert_its_project_alone(estate, flush_only):
    from shared.services.bounty_programs import alert_scopes  # noqa: PLC0415

    other = await estate.sibling()
    states = {
        "platform": "hackerone",
        "program_state": ProgramState.PUBLIC.value,
        "submission_state": SubmissionState.OPEN.value,
    }
    program = BountyProgram(handle="qzwatch", name="Qz Watch", **states)
    followed = BountyProgram(
        handle="qzfollow", name="Qz Follow", bookmarked=True, **states
    )
    flush_only.add_all([program, followed])
    await flush_only.flush()
    flush_only.add(
        ProgramWatch(
            project_id=other.project_id,
            program_id=program.id,
            created_by=estate.user_id,
        )
    )
    kind = "scope_added"
    events = [
        BountyEventRow(
            platform=p.platform,
            program_id=p.id,
            handle=p.handle,
            program_name=p.name,
            kind=kind,
        )
        for p in (program, followed)
    ]
    flush_only.add_all(events)
    await flush_only.flush()

    scopes = alert_scopes({kind}, [estate.project_id, other.project_id])
    matched = {
        project_id: set(
            (await flush_only.scalars(select(BountyEventRow.id).where(cond))).all()
        )
        for project_id, cond in scopes
    }
    assert matched == {
        None: {events[1].id},
        estate.project_id: set(),
        other.project_id: {events[0].id},
    }


# ---------- AI ledger ----------


async def test_a_member_reads_its_own_ai_calls(estate, flush_only):
    from app.api.v1.ai import ai_status, recent_calls  # noqa: PLC0415

    member = await estate.member(estate.project_id)
    admin = await flush_only.get(User, estate.user_id)

    def call(user_id):
        return AiCall(
            task="report",
            feature="reports",
            provider="anthropic",
            model="m",
            user_id=user_id,
            source_kind="report",
            source_id=uuid.uuid4(),
        )

    own, foreign, unowned = call(member.id), call(admin.id), call(None)
    flush_only.add_all([own, foreign, unowned])
    await flush_only.flush()

    mine = await recent_calls(member, flush_only, 50, None)
    every = await recent_calls(admin, flush_only, 50, None)
    assert [c.id for c in mine.items] == [own.id]
    assert {own.id, foreign.id, unowned.id} <= {c.id for c in every.items}
    assert (await ai_status(member, flush_only)).usage.calls == 1
    assert (await ai_status(admin, flush_only)).usage.calls >= 3


async def test_a_member_reads_no_count_of_cached_narratives(estate, flush_only):
    from app.api.v1.ai import ai_status  # noqa: PLC0415
    from shared.models.ai import AiNarrative  # noqa: PLC0415

    member = await estate.member(estate.project_id)
    admin = await flush_only.get(User, estate.user_id)
    before = (await ai_status(admin, flush_only)).cached_narratives
    flush_only.add(
        AiNarrative(
            task="report",
            cache_key=uuid.uuid4().hex,
            subject="theirs",
            provider="anthropic",
            model="m",
            content="prose",
        )
    )
    await flush_only.flush()

    assert (await ai_status(member, flush_only)).cached_narratives == 0
    assert (await ai_status(admin, flush_only)).cached_narratives == before + 1


async def test_a_crtsh_answer_is_reused_inside_its_own_project(monkeypatch):
    import httpx  # noqa: PLC0415

    from toolbox.base import ToolContext as LookupContext  # noqa: PLC0415
    from toolbox.tools import org_domains  # noqa: PLC0415
    from tools.crtsh import client as crtsh_client  # noqa: PLC0415

    held: dict[str, str] = {}
    fetches: list[str] = []

    class _Cache:
        async def get(self, key):
            return held.get(key)

        async def set(self, key, value, **_):
            held[key] = value

    def handler(request):
        fetches.append(request.url.params["O"])
        row = {
            "name_value": "Canary Holdings B.V.",
            "common_name": "canary-b.com",
            "not_before": "2025-01-01T00:00:00",
        }
        return httpx.Response(200, json=[row])

    def client(**_):
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def owner(_self, _ctx, _query):
        return org_domains.Owner(name="Canary Holdings B.V.", source="certificate")

    async def nothing(*_args, **_kwargs):
        return None

    async def classify(_session, _project, _names):
        return org_domains.estate.DomainEstate()

    monkeypatch.setattr(crtsh_client, "cache_client", _Cache)
    monkeypatch.setattr(crtsh_client, "get_async_client", client)
    monkeypatch.setattr(org_domains.OrgDomains, "_owner", owner)
    monkeypatch.setattr(org_domains.OrgDomains, "_networks", nothing)
    monkeypatch.setattr(org_domains.OrgDomains, "_registrations", nothing)
    monkeypatch.setattr(org_domains.estate, "classify_domains", classify)

    async def run(project_id):
        ctx = LookupContext(session=None, project_id=project_id)
        args = org_domains.OrgDomains.Input(organization="Canary Holdings B.V.")
        return await org_domains.OrgDomains().run(ctx, args)

    def stamped(outcome):
        return [c for c in outcome.caveats if "stored at" in c]

    theirs, mine = uuid.uuid4(), uuid.uuid4()
    assert stamped(await run(theirs)) == []
    per_run = len(fetches)
    assert stamped(await run(mine)) == []
    assert len(fetches) == 2 * per_run
    assert stamped(await run(mine))
    assert len(fetches) == 2 * per_run
    assert stamped(await run(None)) == []


# ---------- toolbox runs ----------


async def test_a_run_of_a_project_the_user_lost_is_gone(estate, monkeypatch):
    from app.api.v1 import toolbox as toolbox_api  # noqa: PLC0415
    from toolbox import store  # noqa: PLC0415

    member = await estate.member(estate.project_id)
    other = uuid.uuid4()

    def run(project_id):
        return store.new_run(
            tool="t",
            title="T",
            label="l",
            payload={},
            status="completed",
            project_id=project_id,
        )

    own, lost, plain = run(estate.project_id), run(other), run(None)
    held = {r.id: r for r in (own, lost, plain)}

    async def recent(_user_id):
        return list(held.values())

    async def get(_user_id, run_id):
        return held.get(run_id)

    monkeypatch.setattr(store, "recent", recent)
    monkeypatch.setattr(store, "get", get)
    access = frozenset({estate.project_id})

    listed = await toolbox_api.toolbox_runs(member, access)
    assert {r.id for r in listed} == {own.id, plain.id}
    refused = await _refused(toolbox_api.toolbox_run(member, access, lost.id))
    assert (refused.status_code, refused.detail) == (404, "Run expired.")
    assert (await toolbox_api.toolbox_run(member, access, own.id)).id == own.id
    every = await toolbox_api.toolbox_runs(member, None)
    assert len(every) == 3


# ---------- remote control ----------


async def test_pairing_names_a_project_the_account_is_not_a_member_of(
    estate, flush_only
):
    from channels.models import PairingApprove  # noqa: PLC0415
    from channels.service import (  # noqa: PLC0415
        NOT_A_MEMBER,
        ChannelConfigError,
        ChannelService,
    )

    other = await estate.sibling()
    member = await estate.member(estate.project_id)
    service = ChannelService(flush_only, "telegram")

    with pytest.raises(ChannelConfigError) as outside:
        await service.approve(
            "code",
            PairingApprove(user_id=member.id, project_id=other.project_id),
            estate.user_id,
        )
    assert str(outside.value) == NOT_A_MEMBER
    with pytest.raises(ChannelConfigError) as missing:
        await service.approve(
            "code",
            PairingApprove(user_id=member.id, project_id=uuid.uuid4()),
            estate.user_id,
        )
    assert str(missing.value) == "The project does not exist."


# ---------- shared lookup caches ----------


async def _held_record(estate, holder, value: str, **fields):
    from shared.enums.whois import WhoisLookupType  # noqa: PLC0415
    from shared.models.target import Target  # noqa: PLC0415
    from shared.models.whois import WhoisRecord  # noqa: PLC0415

    record = WhoisRecord(
        query_value=value,
        lookup_type=WhoisLookupType.DOMAIN,
        queried_at=utc_now(),
        **fields,
    )
    estate.session.add(record)
    await estate.session.flush()
    target = await estate.session.get(Target, await holder.target(value))
    target.whois_record_id = record.id
    await estate.session.flush()
    return record


def _parsed(value: str, registrant: str) -> dict:
    return {
        "query": value,
        "name": value,
        "nameservers": ["ns1.example.net"],
        "entities": {"registrant": [{"name": registrant}]},
    }


async def test_the_toolbox_whois_serves_and_writes_open_records_only(
    estate, flush_only, monkeypatch
):
    from toolbox.base import ToolContext as LookupContext  # noqa: PLC0415
    from toolbox.base import ToolError as LookupError_  # noqa: PLC0415
    from toolbox.tools.whois import Input, WhoisLookup  # noqa: PLC0415
    from tools.whois.models import WhoisDomainResponse  # noqa: PLC0415
    from tools.whois.service import WhoisService  # noqa: PLC0415

    fresh: list[str] = []

    def lookup(_self, query, _kind):
        fresh.append(query)
        return WhoisDomainResponse.model_validate(_parsed(query, "Fresh Answer"))

    monkeypatch.setattr(WhoisService, "_fresh_lookup", lookup)
    other = await estate.sibling(name="Theirs")
    theirs = await _held_record(
        estate,
        other,
        "theirs-tracked.example",
        registrant_name="Hidden Holder",
        parsed_data=_parsed("theirs-tracked.example", "Hidden Holder"),
    )
    stamp = theirs.queried_at
    mine = await _held_record(
        estate,
        estate,
        "mine-tracked.example",
        parsed_data=_parsed("mine-tracked.example", "Own Holder"),
    )
    ctx = LookupContext(session=flush_only, project_id=estate.project_id)

    outcome = await WhoisLookup().run(ctx, Input(query="theirs-tracked.example"))
    assert fresh == ["theirs-tracked.example"]
    assert outcome.caveats == []
    await flush_only.refresh(theirs)
    assert (theirs.registrant_name, theirs.queried_at) == ("Hidden Holder", stamp)

    served = await WhoisLookup().run(ctx, Input(query="mine-tracked.example"))
    assert fresh == ["theirs-tracked.example"]
    assert served.caveats == ["Served from the stored record, not a fresh query."]

    mine.parsed_data = {}
    await flush_only.flush()
    with pytest.raises(LookupError_) as empty:
        await WhoisLookup().run(ctx, Input(query="mine-tracked.example"))
    assert str(mine.id) not in str(empty.value)


async def test_whois_correlations_cap_inside_the_targets_project(
    estate, flush_only, monkeypatch
):
    from app.api.v1 import whois as whois_api  # noqa: PLC0415

    monkeypatch.setattr(whois_api, "MAX_CORRELATION_RECORDS", 2)
    member = await estate.member(estate.project_id)
    access = frozenset({estate.project_id})
    top = (1 << 128) - 1
    await _held_record(
        estate,
        estate,
        "a-one.example",
        id=uuid.UUID(int=top - 1),
        registrant_name="Acme Widgets Inc",
    )
    await _held_record(
        estate,
        estate,
        "a-two.example",
        id=uuid.UUID(int=top),
        registrant_name="Acme Widgets Inc",
    )
    other = await estate.sibling(name="Theirs")
    for n in range(2):
        await _held_record(
            estate,
            other,
            f"b-{n}.example",
            id=uuid.UUID(int=n + 1),
            registrant_name="Acme Widgets Inc",
        )

    found = await whois_api.get_target_correlations(
        str(estate.targets["a-one.example"]), member, access, flush_only
    )
    assert [
        (c.correlation_type, [r.query_value for r in c.records]) for c in found
    ] == [("registrant_name", ["a-two.example"])]


async def test_a_cached_reverse_lookup_of_a_closed_project_reads_as_a_miss(
    estate, flush_only
):
    from app.api.v1 import viewdns as viewdns_api  # noqa: PLC0415
    from shared.enums.target import TargetType  # noqa: PLC0415
    from shared.models.viewdns import ViewDNSCache  # noqa: PLC0415
    from tools.viewdns.models import (  # noqa: PLC0415
        CachedCountQuery,
        ViewDNSLookupType,
    )

    other = await estate.sibling(name="Theirs")
    await other.target("203.0.113.7", TargetType.IP)
    await estate.target("198.51.100.9", TargetType.IP)
    await _held_record(estate, other, "theirs.example", registrant_name="Hidden Holder")
    ip = ViewDNSLookupType.REVERSE_IP
    whois = ViewDNSLookupType.REVERSE_WHOIS
    for kind, value in (
        (ip, "203.0.113.7"),
        (ip, "198.51.100.9"),
        (whois, "Hidden Holder"),
    ):
        flush_only.add(
            ViewDNSCache(
                lookup_type=kind.value,
                query_value=value,
                result_count=1,
                response_data={"host": value, "domains": [{"name": "co.example"}]}
                if kind == ip
                else {"query": value, "matches": [{"domain": "co.example"}]},
            )
        )
    await flush_only.flush()
    member = viewdns_api.get_viewdns_service(flush_only, frozenset({estate.project_id}))
    admin = viewdns_api.get_viewdns_service(flush_only, None)

    assert await member.reverse_ip("203.0.113.7", cached_only=True) is None
    assert await member.reverse_whois("Hidden Holder", cached_only=True) is None
    assert (await member.reverse_ip("198.51.100.9", cached_only=True)).cached
    assert (await admin.reverse_ip("203.0.113.7", cached_only=True)).cached
    queries = [
        CachedCountQuery(source=ip, query="203.0.113.7"),
        CachedCountQuery(source=whois, query="Hidden Holder"),
        CachedCountQuery(source=ip, query="198.51.100.9"),
    ]
    assert [c.count for c in await member.cached_counts(queries)] == [None, None, 1]
    assert [c.count for c in await admin.cached_counts(queries)] == [1, 1, 1]


async def test_a_tool_reads_another_projects_run_as_an_unknown_one(estate):
    from datetime import UTC, datetime  # noqa: PLC0415

    from mcp import server  # noqa: PLC0415
    from mcp.capabilities import Capability  # noqa: PLC0415
    from mcp.context import TokenIdentity, ToolContext  # noqa: PLC0415
    from mcp.errors import McpError  # noqa: PLC0415

    other = await estate.sibling(name="Theirs")
    theirs = await other.scan("theirs.example", "their run", at=datetime.now(UTC))
    await estate.session.flush()
    ctx = ToolContext(
        session=estate.session,
        token=TokenIdentity(
            id=uuid.uuid4(),
            name="telegram:member",
            project_id=estate.project_id,
            capabilities=frozenset({Capability.READ.value}),
            projects=frozenset({estate.project_id}),
        ),
        ui_base_url="http://ui",
    )

    async def answer(tool: str, arg: str, scan_id: str) -> str:
        with pytest.raises(McpError) as refused:
            await server.invoke(ctx, tool, {arg: scan_id})
        return refused.value.message.replace(scan_id, "<id>")

    for tool, arg in (("scan_status", "scan"), ("compare_runs", "current")):
        assert await answer(tool, arg, str(theirs)) == await answer(
            tool, arg, str(uuid.uuid4())
        )


# ---------- threat intelligence ----------


async def test_the_cve_cache_answers_for_the_cves_a_project_found(estate, flush_only):
    from datetime import timedelta  # noqa: PLC0415

    from app.api.v1 import threat_intel as threat_api  # noqa: PLC0415
    from app.services.target_scope import TargetFilter  # noqa: PLC0415
    from app.services.threat_intel import ThreatIntelService  # noqa: PLC0415
    from shared.models.threat_intel import CveIntel  # noqa: PLC0415
    from shared.models.vulnerability import Vulnerability  # noqa: PLC0415
    from toolbox.base import ToolContext as LookupContext  # noqa: PLC0415
    from toolbox.tools.cve import CveLookup, Input  # noqa: PLC0415

    at = utc_now()
    other = await estate.sibling(name="Theirs")
    await other.scan("theirs.example", "their run", at=at)
    await other.vulns("their run", [("theirs-cve", "high")], at=at)
    await estate.scan("example.com", "my run", at=at)
    await estate.vulns("my run", [("mine-cve", "high")], at=at)
    for fingerprint, cve in (
        ("theirs-cve", "CVE-2099-0001"),
        ("mine-cve", "CVE-2099-0002"),
    ):
        row = await flush_only.scalar(
            select(Vulnerability).where(Vulnerability.fingerprint == fingerprint)
        )
        row.cve_ids = [cve]
    mine_at = at - timedelta(days=2)
    flush_only.add(CveIntel(cve="CVE-2099-0001", description="qzcanary", fetched_at=at))
    flush_only.add(CveIntel(cve="CVE-2099-0002", description="own", fetched_at=mine_at))
    await flush_only.flush()
    ctx = LookupContext(session=flush_only, project_id=estate.project_id)

    theirs = await CveLookup().run(ctx, Input(cve="CVE-2099-0001"))
    assert theirs.raw["intel"] is None
    assert "qzcanary" not in str(theirs.blocks)
    mine = await CveLookup().run(ctx, Input(cve="CVE-2099-0002"))
    assert mine.raw["intel"]["description"] == "own"
    bare = LookupContext(session=flush_only, project_id=None)
    assert (await CveLookup().run(bare, Input(cve="CVE-2099-0002"))).raw[
        "intel"
    ] is None

    member = await estate.member(estate.project_id)
    service = ThreatIntelService(flush_only)
    scoped = await threat_api.status(
        member,
        frozenset({estate.project_id}),
        service,
        TargetFilter(),
        estate.project_id,
    )
    assert (scoped.providers[0].rows, scoped.providers[0].last_fetched_at) == (
        1,
        mine_at,
    )
    admin = await flush_only.get(User, estate.user_id)
    every = await threat_api.status(admin, None, service, TargetFilter(), None)
    assert every.providers[0].rows >= 2
