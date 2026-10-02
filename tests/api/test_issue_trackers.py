from __future__ import annotations

import dataclasses
import json
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.services.issue_tracking import IssueFilingService, ticket_refs
from app.services.vulnerability import VulnerabilityService
from shared.definitions.evidence import Evidence
from shared.definitions.issue_trackers import (
    MAX_GROUP_LOCATIONS,
    TRACKERS_BY_KIND,
    CommentKind,
    CommentState,
    FilingState,
    Grouping,
    RemoteCategory,
    TrackerKind,
    valid_destination,
)
from shared.definitions.oast import OAST_COVERAGE_GROUP
from shared.definitions.scan_surface import SurfaceState
from shared.definitions.vulnerabilities import CoverageStatus, Protocol
from shared.models.issue_tracker import (
    FileSelection,
    IssueTracker,
    IssueTrackerRoute,
    TrackedIssue,
    TrackedIssueComment,
    TrackedIssueFinding,
)
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import (
    Vulnerability,
    VulnerabilityCoverage,
    VulnerabilityFilter,
    VulnerabilityTriage,
)
from shared.services.issue_trackers import (
    CredentialsError,
    RemoteIssue,
    RemoteStatus,
    TrackerError,
    seal_config,
)
from shared.services.issue_trackers.base import UNREADABLE
from shared.services.issue_trackers.document import (
    Doc,
    rendered_size,
    to_adf,
    to_markdown,
    to_wiki,
)
from shared.services.issue_trackers.github import GitHubIssues
from shared.services.issue_trackers.gitlab import GitLabIssues
from shared.services.issue_trackers.jira import JiraCloud, JiraDataCenter
from shared.services.issue_tracking import sync
from shared.services.issue_tracking.body import issue_body, mask_secrets, title_for
from shared.services.issue_tracking.plan import OpenIssue, plan_filing
from shared.services.scan_resolve import MASK

pytestmark = pytest.mark.api


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _doc() -> Doc:
    return (
        Doc()
        .paragraph("A *bold* claim_with [brackets]")
        .heading("Details")
        .facts([("Severity", "High"), ("CVE", None)])
        .code("GET / HTTP/1.1\n```")
        .link("Open in reNgine", "https://rengine.local/scans/1")
    )


# ---------- documents ----------


def test_markdown_escapes_prose_and_fences_past_the_body():
    text = to_markdown(_doc())
    assert "A \\*bold\\* claim\\_with \\[brackets\\]" in text
    assert "- **Severity:** High" in text
    assert "CVE" not in text
    assert "````\nGET / HTTP/1.1\n```\n````" in text
    assert "[Open in reNgine](https://rengine.local/scans/1)" in text


def test_wiki_escapes_markup_and_keeps_code_unformatted():
    text = to_wiki(_doc())
    assert "A \\*bold\\* claim\\_with \\[brackets\\]" in text
    assert "{noformat}\nGET / HTTP/1.1\n```\n{noformat}" in text
    assert "[Open in reNgine|https://rengine.local/scans/1]" in text


def test_adf_is_a_version_one_document_with_no_empty_text():
    adf = to_adf(_doc())
    assert adf["type"] == "doc"
    assert adf["version"] == 1
    kinds = [node["type"] for node in adf["content"]]
    assert kinds == ["paragraph", "heading", "bulletList", "codeBlock", "paragraph"]
    link = adf["content"][-1]["content"][0]
    assert link["marks"] == [
        {"type": "link", "attrs": {"href": "https://rengine.local/scans/1"}}
    ]
    for node in adf["content"]:
        for child in node.get("content", []):
            if child.get("type") == "text":
                assert child["text"]


# ---------- clients ----------


def test_jira_cloud_files_with_adf_labels_and_the_preferred_type():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/rest/api/3/project/SEC":
            return httpx.Response(
                200,
                json={
                    "issueTypes": [
                        {"name": "Epic", "subtask": False},
                        {"name": "Sub-task", "subtask": True},
                        {"name": "Task", "subtask": False},
                    ]
                },
            )
        if request.url.path == "/rest/api/3/issue":
            return httpx.Response(201, json={"id": "10042", "key": "SEC-7"})
        return httpx.Response(404)

    jira = JiraCloud(
        "https://acme.atlassian.net",
        {"email": "a@acme.com", "token": "tok"},
        client=_client(handler),
    )
    made = jira.create("SEC", None, "Title", _doc(), ["rengine", "severity-high"])
    assert made == RemoteIssue(
        key="SEC-7",
        external_id="10042",
        url="https://acme.atlassian.net/browse/SEC-7",
    )
    fields = json.loads(seen[-1].content)["fields"]
    assert fields["issuetype"] == {"name": "Task"}
    assert fields["labels"] == ["rengine", "severity-high"]
    assert fields["description"]["type"] == "doc"
    assert seen[-1].headers["Authorization"].startswith("Basic ")


def test_jira_statuses_map_categories_and_fall_back_per_issue_on_a_bad_query():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/rest/api/2/search":
            return httpx.Response(400, json={"errorMessages": ["bad id"]})
        if request.url.path == "/rest/api/2/issue/1":
            status = {"name": "In Review", "statusCategory": {"key": "indeterminate"}}
            return httpx.Response(200, json={"id": "1", "fields": {"status": status}})
        return httpx.Response(404)

    jira = JiraDataCenter(
        "https://jira.acme.com", {"token": "pat"}, client=_client(handler)
    )
    found = jira.statuses("SEC", ["1", "2"])
    assert found["1"] == RemoteStatus("In Review", RemoteCategory.IN_PROGRESS.value)
    assert found["2"] is None


def test_github_files_markdown_and_reads_closed_as_done():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "number": 12,
                    "html_url": "https://github.com/acme/sec/issues/12",
                },
            )
        return httpx.Response(
            200, json={"state": "closed", "state_reason": "completed"}
        )

    gh = GitHubIssues("https://api.github.com", {"token": "t"}, client=_client(handler))
    made = gh.create("acme/sec", None, "Title", _doc(), ["rengine"])
    assert made.key == "acme/sec#12"
    assert seen[0].url.path == "/repos/acme/sec/issues"
    assert "**Severity:** High" in json.loads(seen[0].content)["body"]
    assert gh.statuses("acme/sec", ["12"])["12"] == RemoteStatus(
        "Closed", RemoteCategory.DONE.value
    )


def test_gitlab_encodes_the_project_path():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={"iid": 3, "web_url": "https://gitlab.com/x"})

    gl = GitLabIssues("https://gitlab.com", {"token": "t"}, client=_client(handler))
    made = gl.create(
        "acme/team/sec", None, "Title", _doc(), ["rengine", "severity-low"]
    )
    assert made.key == "acme/team/sec#3"
    assert seen[0].url.raw_path == b"/api/v4/projects/acme%2Fteam%2Fsec/issues"
    assert json.loads(seen[0].content)["labels"] == "rengine,severity-low"
    assert seen[0].headers["PRIVATE-TOKEN"] == "t"


def test_a_refusal_names_the_tracker_and_its_reason_and_401_is_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/user":
            return httpx.Response(401)
        return httpx.Response(422, json={"message": "Validation Failed"})

    gh = GitHubIssues("https://api.github.com", {"token": "t"}, client=_client(handler))
    with pytest.raises(CredentialsError):
        gh.verify()
    with pytest.raises(TrackerError, match="GitHub Issues returned 422: Validation"):
        gh.create("acme/sec", None, "T", _doc(), [])


def test_destinations_are_shape_checked_per_family():
    assert valid_destination(TrackerKind.JIRA_CLOUD.value, "SEC")
    assert not valid_destination(TrackerKind.JIRA_CLOUD.value, "sec/../x")
    assert valid_destination(TrackerKind.GITHUB.value, "acme/sec-tracker")
    assert not valid_destination(TrackerKind.GITHUB.value, "acme/../../user")
    assert valid_destination(TrackerKind.GITLAB.value, "acme/team/sec")
    assert not valid_destination(TrackerKind.GITLAB.value, "acme")


# ---------- planning ----------


def _v(fp: str, template: str, severity: str, target=None, **over):
    return SimpleNamespace(
        target_id=target or TARGET,
        fingerprint=fp,
        template_id=template,
        severity=severity,
        is_kev=over.get("kev", False),
        evidence=over.get("evidence", Evidence.OBSERVED.value),
        matched_at=f"https://{fp}.example.com/",
    )


TARGET = uuid.uuid4()


def test_severe_known_exploited_or_proven_findings_file_alone():
    plan = plan_filing(
        [
            _v("a", "rce", "critical"),
            _v("b", "rce", "critical"),
            _v("c", "old", "medium", kev=True),
            _v("d", "ssrf", "medium", evidence=Evidence.PROVEN.value),
            _v("e", "csp", "low"),
            _v("f", "csp", "low"),
            _v("g", "hsts", "low"),
        ],
        grouping=Grouping.AUTO,
        filed=set(),
        open_groups={},
    )
    shapes = sorted((i.template_id, i.grouped, len(i.vulns)) for i in plan.new)
    assert shapes == [
        ("csp", True, 2),
        ("hsts", True, 1),
        ("old", False, 1),
        ("rce", False, 1),
        ("rce", False, 1),
        ("ssrf", False, 1),
    ]


def test_separate_grouping_files_one_issue_each():
    plan = plan_filing(
        [_v("e", "csp", "low"), _v("f", "csp", "low")],
        grouping=Grouping.SEPARATE,
        filed=set(),
        open_groups={},
    )
    assert [(i.grouped, len(i.vulns)) for i in plan.new] == [(False, 1), (False, 1)]


def test_an_open_grouped_issue_takes_new_locations_up_to_its_cap():
    rows = [_v(f"h{i}", "csp", "low") for i in range(MAX_GROUP_LOCATIONS + 3)]
    open_issue = OpenIssue(uuid.uuid4(), "SEC-1", MAX_GROUP_LOCATIONS - 2)
    plan = plan_filing(
        [*rows, _v("done", "csp", "low")],
        grouping=Grouping.AUTO,
        filed={(TARGET, "done")},
        open_groups={(TARGET, "csp"): open_issue},
    )
    assert plan.already_filed == 1
    assert [len(a.vulns) for a in plan.attach] == [2]
    assert [len(i.vulns) for i in plan.new] == [MAX_GROUP_LOCATIONS, 1]
    assert plan.findings == MAX_GROUP_LOCATIONS + 3


# ---------- filing end to end ----------


class FakeTracker:
    initial_status = "Open"

    def __init__(self) -> None:
        self.created: list[tuple[str, str, Doc, list[str]]] = []
        self.comments: list[tuple[str, Doc]] = []
        self.status = RemoteStatus("Open", RemoteCategory.TODO.value)
        self.markers: list[str] = []
        self.marked: RemoteIssue | None = None
        self.public = False

    def create(self, destination, _issue_type, title, body, labels):
        self.created.append((destination, title, body, labels))
        n = len(self.created)
        return RemoteIssue(key=f"SEC-{n}", external_id=str(n), url=f"https://t/{n}")

    def comment(self, _destination, external_id, body):
        self.comments.append((external_id, body))

    def statuses(self, _destination, external_ids):
        return dict.fromkeys(external_ids, self.status)

    def find_marker(self, _destination, marker):
        self.markers.append(marker)
        return self.marked

    def public_destination(self, _destination):
        return self.public

    def close(self):
        pass


@pytest.fixture
def fake(monkeypatch) -> FakeTracker:
    tracker = FakeTracker()
    monkeypatch.setattr(sync, "tracker_client", lambda _row: tracker)
    monkeypatch.setattr(sync.time, "sleep", lambda _s: None)
    monkeypatch.setattr(
        "app.services.issue_tracking.dispatch_issue_filing", lambda _ids: True
    )
    return tracker


async def _tracker(estate) -> IssueTracker:
    row = IssueTracker(
        name="Security Jira",
        kind=TrackerKind.JIRA_CLOUD.value,
        url="https://acme.atlassian.net",
        config_encrypted=seal_config({"email": "a@acme.com", "token": "tok"}),
        destination="SEC",
    )
    estate.session.add(row)
    await estate.session.flush()
    return row


async def _finding(estate, scan: str, fp: str, severity: str, at, template=None):
    sid = estate.scans[scan]
    target_id = await estate._target_of(sid)
    estate.session.add(
        Vulnerability(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=target_id,
            fingerprint=fp,
            template_id=template or fp,
            template_name=(template or fp).title(),
            severity=severity,
            matched_at=f"https://{fp}.example.com/",
            host=f"{fp}.example.com",
            curl_command="curl -H 'Authorization: Bearer secret' https://x",
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _scanned(estate, scan: str, host: str) -> None:
    sid = estate.scans[scan]
    estate.session.add(
        ScanSurfaceItem(
            scan_id=sid,
            target_id=await estate._target_of(sid),
            project_id=estate.project_id,
            value=f"https://{host}",
            host=host,
            state=SurfaceState.SCANNED.value,
        )
    )
    await estate.session.flush()


_LIBRARY_ROOT = "http/test-issue-trackers/"


@pytest_asyncio.fixture
async def library(durable_estate):
    yield
    session = durable_estate.session
    await session.rollback()
    await session.execute(
        delete(VulnTemplate).where(VulnTemplate.path.startswith(_LIBRARY_ROOT))
    )
    await session.commit()


async def _check(estate, template: str, *, needs_oast: bool = False) -> None:
    estate.session.add(
        VulnTemplate(
            template_id=template,
            path=f"{_LIBRARY_ROOT}{template}.yaml",
            name=template.title(),
            severity="critical",
            protocol=Protocol.HTTP.value,
            tags=["cve"],
            needs_oast=needs_oast,
        )
    )
    await estate.session.flush()


async def _file_now(estate) -> int:
    return await estate.session.run_sync(sync.file_pending)


async def test_filing_groups_by_check_files_and_reports_on_the_finding(
    durable_estate, fake, now
):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "critical", now)
    await _finding(estate, "run", "b", "low", now, template="csp")
    await _finding(estate, "run", "c", "low", now, template="csp")
    await _tracker(estate)
    await estate.session.commit()

    service = IssueFilingService(estate.session)
    selection = FileSelection(fingerprints=["a", "b", "c"])
    plan = await service.plan(estate.scans["run"], selection)
    assert plan.refusal is None
    assert (plan.new_issues, plan.findings) == (2, 3)
    assert plan.tracker_name == "Security Jira"

    result = await service.file(estate.scans["run"], selection, estate.user_id)
    assert result.new_issues == 2
    assert {i.state for i in result.issues} == {FilingState.PENDING.value}

    assert await _file_now(estate) == 2
    titles = sorted(t for _, t, _, _ in fake.created)
    assert titles == ["A on a.example.com", "Csp on example.com"]
    single = next(body for _, t, body, _ in fake.created if t.startswith("A "))
    assert "secret" not in to_markdown(single)

    again = await service.plan(estate.scans["run"], selection)
    assert (again.new_issues, again.already_filed) == (0, 3)

    vuln = await estate.session.scalar(
        select(Vulnerability).where(Vulnerability.fingerprint == "a")
    )
    refs = await ticket_refs(estate.session, [(vuln.target_id, "a")])
    [ref] = refs[(vuln.target_id, "a")]
    assert ref.state == FilingState.FILED.value
    assert ref.external_key.startswith("SEC-")


async def test_no_route_refuses_and_a_project_route_is_followed(
    durable_estate, fake, now
):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "high", now)
    await _tracker(estate)
    second = await _tracker(estate)
    await estate.session.commit()
    service = IssueFilingService(estate.session)
    selection = FileSelection(fingerprints=["a"])

    plan = await service.plan(estate.scans["run"], selection)
    assert plan.refusal is not None
    assert "No route for this project" in plan.refusal

    estate.session.add(
        IssueTrackerRoute(
            project_id=estate.project_id, tracker_id=second.id, destination="OPS"
        )
    )
    await estate.session.commit()
    plan = await service.plan(estate.scans["run"], selection)
    assert (plan.tracker_id, plan.destination) == (second.id, "OPS")
    assert plan.preview is not None
    headings = [b.text for b in plan.preview if b.kind == "heading"]
    assert "Reproduction" in headings
    assert {b.lang for b in plan.preview if b.kind == "code"} <= {"shell", "http"}


async def test_a_later_location_joins_the_open_grouped_issue_as_a_comment(
    durable_estate, fake, now
):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "b", "low", now, template="csp")
    await _finding(estate, "run", "c", "low", now, template="csp")
    await _tracker(estate)
    await estate.session.commit()
    service = IssueFilingService(estate.session)
    await service.file(
        estate.scans["run"], FileSelection(fingerprints=["b", "c"]), estate.user_id
    )
    await _file_now(estate)

    await _finding(estate, "run", "d", "low", now, template="csp")
    await estate.session.commit()
    result = await service.file(
        estate.scans["run"], FileSelection(fingerprints=["d"]), estate.user_id
    )
    assert (result.new_issues, result.attached) == (0, 1)
    await estate.session.run_sync(sync.announce)
    await estate.session.run_sync(sync.announce)
    await estate.session.run_sync(sync.send_comments)
    [(external_id, body)] = fake.comments
    assert external_id == "1"
    assert "d.example.com" in to_markdown(body)


async def test_a_clean_rescan_comments_on_what_it_no_longer_observes(
    durable_estate, fake, library, now
):
    estate = durable_estate
    await estate.scan("example.com", "first", at=now)
    await _finding(estate, "first", "a", "critical", now)
    await _check(estate, "a")
    await _tracker(estate)
    await estate.session.commit()
    service = IssueFilingService(estate.session)
    await service.file(
        estate.scans["first"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    await _file_now(estate)

    await estate.scan("example.com", "partial", at=now)
    await estate.activity("partial", {"vulnerability_scan": "partial"}, at=now)
    await estate.session.commit()
    await estate.session.run_sync(
        lambda s: sync.observe_scan(s, estate.scans["partial"])
    )
    assert fake.comments == []

    await estate.scan("example.com", "clean", at=now)
    await estate.activity("clean", {"vulnerability_scan": "success"}, at=now)
    await _scanned(estate, "clean", "a.example.com")
    await estate.session.commit()
    await estate.session.run_sync(lambda s: sync.observe_scan(s, estate.scans["clean"]))
    [(_, body)] = fake.comments
    assert to_markdown(body).startswith("Not observed in the scan of")
    link = await estate.session.scalar(
        select(TrackedIssueFinding).where(TrackedIssueFinding.fingerprint == "a")
    )
    assert link.present is False


async def test_done_in_the_tracker_but_still_observed_is_said_once(
    durable_estate, fake, now
):
    estate = durable_estate
    await estate.scan("example.com", "first", at=now)
    await _finding(estate, "first", "a", "critical", now)
    await _tracker(estate)
    await estate.session.commit()
    await IssueFilingService(estate.session).file(
        estate.scans["first"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    await _file_now(estate)
    fake.status = RemoteStatus("Done", RemoteCategory.DONE.value)
    await estate.session.run_sync(lambda s: sync.refresh_statuses(s, force=True))

    for name in ("second", "third"):
        await estate.scan("example.com", name, at=now)
        await _finding(estate, name, "a", "critical", now)
        await estate.session.commit()
        await estate.session.run_sync(
            lambda s, n=name: sync.observe_scan(s, estate.scans[n])
        )
    kinds = [
        row.kind
        for row in (await estate.session.execute(select(TrackedIssueComment))).scalars()
    ]
    assert kinds == [CommentKind.STILL_OBSERVED.value]
    [(_, still)] = fake.comments
    assert ". Issue status: Done." in to_markdown(still)

    page = await VulnerabilityService(estate.session).search(
        estate.scans["third"], VulnerabilityFilter(q="ticket:done", limit=10)
    )
    assert page.error is None
    assert [row.fingerprint for row in page.items] == ["a"]
    assert page.items[0].tickets[0].remote_category == RemoteCategory.DONE.value
    open_page = await VulnerabilityService(estate.session).search(
        estate.scans["third"], VulnerabilityFilter(q="ticket:todo", limit=10)
    )
    assert open_page.items == []
    sent = await estate.session.scalar(
        select(TrackedIssueComment).where(
            TrackedIssueComment.state == CommentState.SENT.value
        )
    )
    assert sent is not None
    issue = await estate.session.scalar(select(TrackedIssue))
    assert issue.done_noted is True


async def test_absence_is_claimed_only_where_the_run_tested_the_check(
    durable_estate, fake, library, now
):
    estate = durable_estate
    await estate.scan("example.com", "first", at=now)
    await _finding(estate, "first", "a", "critical", now)
    await _check(estate, "a")
    await _tracker(estate)
    await estate.session.commit()
    await IssueFilingService(estate.session).file(
        estate.scans["first"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    await _file_now(estate)

    skipped = {"stages": {"vulnerability_scan": {"severities": ["low"]}}}
    await estate.scan("example.com", "narrow", at=now, config=skipped)
    await estate.activity("narrow", {"vulnerability_scan": "success"}, at=now)
    await _scanned(estate, "narrow", "a.example.com")
    await estate.scan("example.com", "elsewhere", at=now)
    await estate.activity("elsewhere", {"vulnerability_scan": "success"}, at=now)
    await _scanned(estate, "elsewhere", "b.example.com")
    await estate.session.commit()
    for name in ("narrow", "elsewhere"):
        await estate.session.run_sync(
            lambda s, n=name: sync.observe_scan(s, estate.scans[n])
        )
    assert fake.comments == []


@pytest.mark.parametrize(
    ("config", "callback"),
    [
        ({"template_sets": ["panel"]}, False),
        ({"exclude_tags": ["cve"]}, False),
        ({}, True),
    ],
    ids=["narrower-sets", "excluded-tag", "callback-unheard"],
)
async def test_absence_is_not_claimed_for_a_check_the_run_did_not_select(
    durable_estate, fake, library, now, config, callback
):
    estate = durable_estate
    await estate.scan("example.com", "first", at=now)
    await _finding(estate, "first", "a", "critical", now)
    await _check(estate, "a", needs_oast=callback)
    await _tracker(estate)
    await estate.session.commit()
    await IssueFilingService(estate.session).file(
        estate.scans["first"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    await _file_now(estate)

    sid = await estate.scan(
        "example.com",
        "again",
        at=now,
        config={"stages": {"vulnerability_scan": config}},
    )
    await estate.activity("again", {"vulnerability_scan": "success"}, at=now)
    await _scanned(estate, "again", "a.example.com")
    if callback:
        estate.session.add(
            VulnerabilityCoverage(
                scan_id=sid,
                target_id=await estate._target_of(sid),
                project_id=estate.project_id,
                group=OAST_COVERAGE_GROUP,
                status=CoverageStatus.SKIPPED.value,
            )
        )
    await estate.session.commit()
    await estate.session.run_sync(lambda s: sync.observe_scan(s, sid))
    assert fake.comments == []
    link = await estate.session.scalar(
        select(TrackedIssueFinding).where(TrackedIssueFinding.fingerprint == "a")
    )
    assert link.present is True


async def test_a_later_run_is_not_overwritten_by_an_older_one(
    durable_estate, fake, now
):
    estate = durable_estate
    await estate.scan("example.com", "first", at=now)
    await _finding(estate, "first", "a", "critical", now)
    await _tracker(estate)
    await estate.session.commit()
    await IssueFilingService(estate.session).file(
        estate.scans["first"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    await _file_now(estate)
    await estate.scan("example.com", "old", at=now - timedelta(hours=2))
    await estate.activity("old", {"vulnerability_scan": "success"}, at=now)
    await _scanned(estate, "old", "a.example.com")
    await estate.scan("example.com", "new", at=now + timedelta(hours=1))
    await _finding(estate, "new", "a", "critical", now + timedelta(hours=1))
    await estate.session.commit()
    await estate.session.run_sync(lambda s: sync.observe_scan(s, estate.scans["old"]))
    assert fake.comments == []


async def test_non_admin_files_only_into_routed_destinations(durable_estate, fake, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "high", now)
    tracker = await _tracker(estate)
    await estate.session.commit()
    outside = FileSelection(
        fingerprints=["a"], tracker_id=tracker.id, destination="OPS"
    )
    member = IssueFilingService(estate.session)
    refused = await member.plan(estate.scans["run"], outside)
    assert refused.refusal is not None
    assert "OPS" in refused.refusal
    admin = IssueFilingService(estate.session, admin=True)
    allowed = await admin.plan(estate.scans["run"], outside)
    assert (allowed.refusal, allowed.destination) == (None, "OPS")
    default = await member.plan(
        estate.scans["run"], FileSelection(fingerprints=["a"], tracker_id=tracker.id)
    )
    assert (default.refusal, default.destination) == (None, "SEC")


async def test_a_route_to_a_switched_off_tracker_refuses(durable_estate, fake, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "high", now)
    off = await _tracker(estate)
    off.is_active = False
    await _tracker(estate)
    estate.session.add(
        IssueTrackerRoute(
            project_id=estate.project_id, tracker_id=off.id, destination="SEC"
        )
    )
    await estate.session.commit()
    plan = await IssueFilingService(estate.session).plan(
        estate.scans["run"], FileSelection(fingerprints=["a"])
    )
    assert plan.refusal == "Tracker for example.com is disabled."


async def test_set_aside_findings_are_not_filed_and_the_selection_is_capped(
    durable_estate, fake, now, monkeypatch
):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    for fp in ("a", "b", "c"):
        await _finding(estate, "run", fp, "low", now, template="csp")
    await _tracker(estate)
    estate.session.add(
        VulnerabilityTriage(
            project_id=estate.project_id,
            target_id=await estate._target_of(estate.scans["run"]),
            fingerprint="c",
            template_id="csp",
            matched_at="https://c.example.com/",
            state="false_positive",
        )
    )
    await estate.session.commit()
    service = IssueFilingService(estate.session)
    plan = await service.plan(estate.scans["run"], FileSelection(template_ids=["csp"]))
    assert plan.findings == 2
    monkeypatch.setattr("app.services.issue_tracking.MAX_FILE_SELECTION", 1)
    capped = await service.plan(
        estate.scans["run"], FileSelection(template_ids=["csp"])
    )
    assert capped.refusal == "Selection has 2 findings. The limit is 1."


async def test_a_retry_finds_the_issue_an_ambiguous_create_left_behind(
    durable_estate, fake, now
):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "high", now)
    await _tracker(estate)
    await estate.session.commit()
    service = IssueFilingService(estate.session)
    await service.file(
        estate.scans["run"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    issue = await estate.session.scalar(select(TrackedIssue))
    issue.attempts = 1
    await estate.session.commit()
    fake.marked = RemoteIssue(key="SEC-9", external_id="9", url="https://t/9")
    await _file_now(estate)
    await estate.session.refresh(issue)
    assert (issue.state, issue.external_key) == (FilingState.FILED.value, "SEC-9")
    assert fake.created == []
    assert fake.markers == [f"rengine-{issue.id.hex[:12]}"]


async def test_a_public_repository_gets_no_evidence(durable_estate, fake, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "high", now)
    await _tracker(estate)
    await estate.session.commit()
    fake.public = True
    await IssueFilingService(estate.session).file(
        estate.scans["run"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    await _file_now(estate)
    [(_, _, body, labels)] = fake.created
    assert "Reproduction" not in [b.text for b in body.blocks if b.kind == "heading"]
    assert labels == ["rengine", "severity-high"]
    reference = f"Reference: rengine-{(await estate.session.scalar(select(TrackedIssue.id))).hex[:12]}"
    assert reference in to_markdown(body)


async def test_a_pending_issue_whose_task_was_lost_is_swept(durable_estate, fake, now):
    estate = durable_estate
    await estate.scan("example.com", "run", at=now)
    await _finding(estate, "run", "a", "high", now)
    await _tracker(estate)
    await estate.session.commit()
    await IssueFilingService(estate.session).file(
        estate.scans["run"], FileSelection(fingerprints=["a"]), estate.user_id
    )
    assert await estate.session.run_sync(sync.sweep_pending) == 0
    issue = await estate.session.scalar(select(TrackedIssue))
    issue.updated_at = now - timedelta(hours=1)
    await estate.session.commit()
    assert await estate.session.run_sync(sync.sweep_pending) == 1


def test_a_grouped_body_fits_the_tracker_limit():
    rows = [
        SimpleNamespace(
            **{
                **vars(_v(f"h{i}", "csp", "low")),
                "matched_at": f"https://h{i}.example.com/{'x' * 1500}",
                "template_name": "Csp",
                "description": "d",
                "impact": None,
                "remediation": None,
                "references": [],
                "cve_ids": [],
                "cwe_ids": [],
                "cvss_score": None,
                "epss_score": None,
                "scan_id": uuid.uuid4(),
            }
        )
        for i in range(MAX_GROUP_LOCATIONS)
    ]
    spec = dataclasses.replace(
        TRACKERS_BY_KIND[TrackerKind.JIRA_CLOUD.value], body_limit=8000
    )
    doc = issue_body(rows, "example.com", spec, grouped=True)
    assert rendered_size(doc, spec.body_format.value) <= spec.body_limit
    assert "more locations." in to_markdown(doc)


def test_target_text_cannot_open_markup():
    doc = Doc().paragraph("\\[~admin] !https://x/p.png! @all ~label")
    wiki = to_wiki(doc)
    assert "\\[" not in wiki.replace("\\\\\\[", "")
    assert "\\!https" in wiki
    assert "\\@all \\~label" in to_markdown(doc)


def test_a_gone_issue_reads_not_found_and_a_broken_one_is_skipped():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/1"):
            return httpx.Response(410)
        if request.url.path.endswith("/2"):
            return httpx.Response(500)
        return httpx.Response(200, json={"state": "open"})

    gh = GitHubIssues("https://api.github.com", {"token": "t"}, client=_client(handler))
    found = gh.statuses("acme/sec", ["1", "2", "3"])
    assert found["1"] is None
    assert found["2"] == RemoteStatus(UNREADABLE, None)
    assert found["3"] == RemoteStatus("Open", RemoteCategory.TODO.value)


def test_a_list_where_an_object_was_expected_is_a_tracker_error():
    gh = GitHubIssues(
        "https://api.github.com",
        {"token": "t"},
        client=_client(lambda _r: httpx.Response(200, json=["x"])),
    )
    with pytest.raises(TrackerError, match="unexpected response"):
        gh.verify()


def test_a_single_title_names_a_non_default_port():
    base = {
        "template_name": "Git Configuration - Detect",
        "template_id": "git-config",
        "host": "172.19.0.12",
    }
    on_80 = SimpleNamespace(**base, matched_at="http://172.19.0.12/.git/config")
    on_8080 = SimpleNamespace(**base, matched_at="http://172.19.0.12:8080/.git/config")
    v6 = SimpleNamespace(
        **{**base, "host": "2001:db8::1"}, matched_at="https://[2001:db8::1]:8443/x"
    )
    assert title_for([on_80], "t", grouped=False).endswith("on 172.19.0.12")
    assert title_for([on_8080], "t", grouped=False).endswith("on 172.19.0.12:8080")
    assert title_for([v6], "t", grouped=False).endswith("on [2001:db8::1]:8443")


def test_github_validation_errors_read_as_text():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "message": "Validation Failed",
                "errors": [
                    {
                        "value": "x",
                        "resource": "Label",
                        "field": "name",
                        "code": "invalid",
                    }
                ],
            },
        )

    gh = GitHubIssues("https://api.github.com", {"token": "t"}, client=_client(handler))
    with pytest.raises(TrackerError) as caught:
        gh.create("acme/sec", None, "T", _doc(), [])
    assert (
        str(caught.value)
        == "GitHub Issues returned 422: Validation Failed; Label name invalid"
    )


def test_github_finds_a_marker_in_the_bodies_of_its_own_recent_issues():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/user":
            return httpx.Response(200, json={"login": "bot"})
        return httpx.Response(
            200,
            json=[
                {"number": 9, "body": "Reference: rengine-aaa", "pull_request": {}},
                {
                    "number": 7,
                    "body": "text\n\nReference: rengine-aaa",
                    "html_url": "u",
                },
            ],
        )

    gh = GitHubIssues("https://api.github.com", {"token": "t"}, client=_client(handler))
    found = gh.find_marker("acme/sec", "rengine-aaa")
    assert found is not None
    assert found.key == "acme/sec#7"
    assert seen[-1].url.params["creator"] == "bot"


def test_evidence_in_an_issue_masks_secret_values_and_keeps_their_names():
    vuln = SimpleNamespace(
        description="d",
        impact=None,
        remediation=None,
        references=[],
        cve_ids=[],
        cwe_ids=[],
        cvss_score=None,
        epss_score=None,
        is_kev=False,
        severity="high",
        template_id="env",
        template_name="Env",
        matched_at="http://h/.env",
        host="h",
        evidence="observed",
        discovered_at=None,
        scan_id=uuid.uuid4(),
        id=uuid.uuid4(),
        curl_command="curl -H 'Accept: */*' http://h/.env",
        request="GET /.env HTTP/1.1\r\nHost: h\r\n\r\n",
        response=(
            "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n"
            "APP_NAME=Shop\nDB_PASSWORD=hunter2hunter2\n"
            '{"api_key": "abc123abc123"}\n'
            "AWS=AKIAQYLPMN5HHHFPZAM2\n"
        ),
    )
    spec = TRACKERS_BY_KIND[TrackerKind.GITHUB.value]
    text = to_markdown(issue_body([vuln], "h", spec, grouped=False))
    assert "hunter2hunter2" not in text
    assert "abc123abc123" not in text
    assert "AKIAQYLPMN5HHHFPZAM2" not in text
    assert "DB_PASSWORD=••••••••" in text
    assert "APP_NAME=Shop" in text
    assert "Accept: */*" in text


@pytest.mark.parametrize(
    "text", [" " + "token." * 17000, "token" * 20000], ids=["dotted", "joined"]
)
def test_masking_a_long_run_of_credential_words_stays_linear(text):
    started = time.monotonic()
    mask_secrets(text)
    assert time.monotonic() - started < 1


def test_a_long_dotted_credential_name_is_masked():
    masked = mask_secrets(
        "spring.datasource.hikari.data-source-properties.oracle.jdbc.something.password=xyz"
    )
    assert masked.endswith("password=" + MASK)
