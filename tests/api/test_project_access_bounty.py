"""Project access on Bounty Hub, watches, connectors and issue trackers."""

from __future__ import annotations

import uuid
from datetime import timedelta

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import get_current_user
from app.config import API_V1_PREFIX
from app.core.database import get_session
from app.main import app
from app.services.connector import ConnectorService
from app.services.dashboard_activity import DashboardActivityService
from app.services.issue_tracking import IssueFilingService
from app.services.watch import WatchService
from shared.definitions.issue_trackers import FilingState, TrackerKind
from shared.definitions.watch import WatchStatus
from shared.models.connector import ConnectorCreate, HandoffRequest
from shared.models.issue_tracker import IssueTracker, TrackedIssue
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.models.watch import ProgramWatch, StreamStatus
from shared.services.issue_trackers import seal_config
from shared.services.project_access import EVERY_PROJECT

pytestmark = pytest.mark.api


@pytest.fixture
async def as_member(estate):
    member = await estate.member(estate.project_id)

    async def session():
        yield estate.session

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_current_user] = lambda: member
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test" + API_V1_PREFIX
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def test_bounty_hub_routes_refuse_another_project(estate, as_member):
    other = await estate.sibling()
    mine, theirs = str(estate.project_id), str(other.project_id)
    missing = {"detail": "Project not found."}

    assert (
        await as_member.get("/bounty-programs", params={"project_id": mine})
    ).status_code == 200
    for path in (
        "/bounty-programs",
        "/bounty-programs/watches",
        "/issue-trackers/issues",
        "/connectors",
    ):
        refused = await as_member.get(path, params={"project_id": theirs})
        assert (refused.status_code, refused.json()) == (404, missing), path

    imported = await as_member.post(
        "/bounty-programs/hackerone/acme/import", json={"project_id": theirs}
    )
    watched = await as_member.post(
        "/bounty-programs/hackerone/acme/watch", json={"project_id": theirs}
    )
    assert (imported.status_code, imported.json()) == (404, missing)
    assert (watched.status_code, watched.json()) == (404, missing)


async def test_a_handoff_naming_a_row_of_another_project_is_refused(estate, now):
    other = await estate.sibling()
    await estate.scan("example.com", "mine", at=now)
    await other.scan("example.org", "theirs", at=now)
    await estate.vulns("mine", [("cve-x", "high")], at=now, host="a.example.com")
    await other.vulns("theirs", [("cve-y", "high")], at=now, host="b.example.org")
    await other.hosts("theirs", ["b.example.org"], at=now)
    own = await estate.session.scalar(
        select(Vulnerability.id).where(Vulnerability.project_id == estate.project_id)
    )
    foreign = await estate.session.scalar(
        select(Vulnerability.id).where(Vulnerability.project_id == other.project_id)
    )
    host = await estate.session.scalar(
        select(Subdomain.id).where(Subdomain.project_id == other.project_id)
    )
    service = ConnectorService(estate.session)
    created = await service.create(
        ConnectorCreate(name="Burp", project_id=estate.project_id), estate.user_id
    )
    connector_id = created.connector.id

    for body, noun in (
        (HandoffRequest(finding_ids=[foreign]), "Finding"),
        (HandoffRequest(finding_ids=[own, foreign]), "Finding"),
        (HandoffRequest(host_ids=[host]), "Web asset"),
    ):
        with pytest.raises(HTTPException) as refused:
            await service.handoff(connector_id, estate.project_id, body)
        assert (refused.value.status_code, refused.value.detail) == (
            404,
            f"{noun} not found.",
        )


async def test_an_issue_of_another_project_is_not_found(estate, now):
    other = await estate.sibling()
    target = await other.target("example.org")
    tracker = IssueTracker(
        name="Jira",
        kind=TrackerKind.JIRA_CLOUD.value,
        url="https://acme.atlassian.net",
        config_encrypted=seal_config({"email": "a@acme.com", "token": "tok"}),
        destination="SEC",
    )
    estate.session.add(tracker)
    await estate.session.flush()
    issue = TrackedIssue(
        tracker_id=tracker.id,
        project_id=other.project_id,
        target_id=target,
        template_id="cve-x",
        severity="high",
        destination="SEC",
        title="cve-x on example.org",
        state=FilingState.FAILED.value,
    )
    estate.session.add(issue)
    await estate.session.flush()

    member = IssueFilingService(estate.session, access=frozenset({estate.project_id}))
    for call in (member.retry, member.refresh, member.unlink):
        for issue_id in (issue.id, uuid.uuid4()):
            with pytest.raises(HTTPException) as refused:
                await call(issue_id)
            assert (refused.value.status_code, refused.value.detail) == (
                404,
                "Issue not found.",
            )
    with pytest.raises(HTTPException) as refused:
        await member.list(other.project_id)
    assert refused.value.status_code == 404
    assert await member.list(estate.project_id) == []

    admin = IssueFilingService(estate.session, access=EVERY_PROJECT)
    assert [r.id for r in await admin.list(other.project_id)] == [issue.id]
    assert await estate.session.get(TrackedIssue, issue.id) is not None


async def test_the_certificate_stream_reads_idle_without_an_open_watch(
    estate, now, monkeypatch
):
    other = await estate.sibling(name="Theirs")
    mine = await estate.canary("mine", now)
    theirs = await other.canary("theirs", now)
    session = estate.session
    for ids, item in ((mine, ".mine.test"), (theirs, ".theirs.test")):
        watch = await session.get(ProgramWatch, ids["watch_id"])
        watch.watch_items = [{"item": item}]
        watch.status = WatchStatus.ACTIVE.value
    (
        await session.get(ProgramWatch, mine["watch_id"])
    ).status = WatchStatus.PAUSED.value
    await session.flush()

    async def supervisor():
        return StreamStatus(running=True, reachable=True, items=1, started_at=now)

    monkeypatch.setattr(WatchService, "stream_status", staticmethod(supervisor))
    access = frozenset({estate.project_id})
    seen = await WatchService(session).stream_status_for(access)
    assert (seen.running, seen.items, seen.started_at) == (False, 0, None)
    cell = await DashboardActivityService(session)._watches(
        estate.project_id, [], now - timedelta(days=7), access
    )
    assert cell.total == 1
    assert cell.stream_running is False

    (
        await session.get(ProgramWatch, mine["watch_id"])
    ).status = WatchStatus.ACTIVE.value
    await session.flush()
    seen = await WatchService(session).stream_status_for(access)
    assert (seen.running, seen.items, seen.started_at) == (True, 1, None)
    cell = await DashboardActivityService(session)._watches(
        estate.project_id, [], now - timedelta(days=7), access
    )
    assert cell.stream_running is True
    every = await WatchService(session).stream_status_for(EVERY_PROJECT)
    assert every.started_at == now
