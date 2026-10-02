"""Worker side: file pending issues, send queued comments, read status, record rescans."""

from __future__ import annotations

import dataclasses
import json
import time
import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy import exists, select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from shared.definitions.issue_trackers import (
    MAX_COMMENT_ATTEMPTS,
    MAX_ERROR,
    PENDING_GRACE_SECONDS,
    STATUS_REFRESH_SECONDS,
    TRACKERS_BY_KIND,
    CommentKind,
    CommentState,
    FilingState,
    RemoteCategory,
    secret_fields,
)
from shared.definitions.oast import OAST_COVERAGE_GROUP
from shared.definitions.scan_surface import SurfaceState
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import CoverageStatus, Scanner
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.scan import ScanActivityStatus, ScanScope, ScanStatus
from shared.logging import get_logger
from shared.models.issue_tracker import (
    IssueTracker,
    TrackedIssue,
    TrackedIssueComment,
    TrackedIssueFinding,
)
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.scan_surface import ScanSurfaceItem
from shared.models.target import Target
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import Vulnerability, VulnerabilityCoverage
from shared.services import locks
from shared.services.activity_log import ActivityLogService
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.issue_trackers import (
    RateLimitedError,
    RemoteNotFoundError,
    Tracker,
    TrackerError,
    open_config,
    tracker_client,
)
from shared.services.issue_trackers.base import UNREADABLE
from shared.services.issue_trackers.document import Block, Doc
from shared.services.issue_tracking import body as bodies
from shared.services.scan_resolve import MASK
from shared.services.scan_scope import covering_stages, producing_stages
from shared.services.scan_surface import wants_callback
from shared.services.vuln_templates import dast_predicate, selection_predicate
from shared.utils.datetime import utc_now
from shared.utils.text import counted

logger = get_logger(__name__)

MAX_STATUS_READS = 300
NOT_FOUND = "Not found"
VULN_STAGE = "vulnerability_scan"
DAST_STAGE = "dast_scan"
DAST_TAG = "dast"
SCANNED_STATES = (SurfaceState.SCANNED.value, SurfaceState.COVERED.value)
_UNRECORDED = "Filed as {key}. Link not saved."
_NOT_FOUND = (
    "{label} did not find {destination}. Check the {noun} and the token's access."
)


def dump_doc(doc: Doc) -> dict:
    return dataclasses.asdict(doc)


def load_doc(raw: dict) -> Doc:
    blocks = []
    for item in raw.get("blocks") or []:
        block = Block(**{k: v for k, v in item.items() if k in Block.__annotations__})
        block.items = [tuple(pair) for pair in block.items]
        blocks.append(block)
    return Doc(blocks=blocks)


def latest_vulns(
    session: Session, pairs: Iterable[tuple[uuid.UUID, str]]
) -> dict[tuple[uuid.UUID, str], Vulnerability]:
    """The newest observation of each (target, fingerprint)."""
    wanted = set(pairs)
    if not wanted:
        return {}
    rows = session.execute(
        select(Vulnerability)
        .where(
            Vulnerability.target_id.in_({t for t, _ in wanted}),
            Vulnerability.fingerprint.in_({f for _, f in wanted}),
        )
        .order_by(Vulnerability.discovered_at.desc())
    ).scalars()
    out: dict[tuple[uuid.UUID, str], Vulnerability] = {}
    for row in rows:
        key = (row.target_id, row.fingerprint)
        if key in wanted and key not in out:
            out[key] = row
    return out


def _error(exc: Exception, tracker: IssueTracker | None = None) -> str:
    message = str(exc) or type(exc).__name__
    if tracker is not None:
        config = open_config(tracker)
        for key in secret_fields(tracker.kind):
            value = config.get(key)
            if isinstance(value, str) and value:
                message = message.replace(value, MASK)
    return message[:MAX_ERROR]


class _Clients:
    """One client per tracker for the length of a pass."""

    def __init__(self) -> None:
        self._open: dict[uuid.UUID, Tracker] = {}

    def of(self, tracker: IssueTracker) -> Tracker:
        if tracker.id not in self._open:
            self._open[tracker.id] = tracker_client(tracker)
        return self._open[tracker.id]

    def close(self) -> None:
        for client in self._open.values():
            client.close()
        self._open.clear()


# ---------- filing ----------


def _is_public(client: Tracker, destination: str) -> bool:
    try:
        return client.public_destination(destination)
    except TrackerError:
        return True


def _body_for(
    session: Session,
    issue: TrackedIssue,
    tracker: IssueTracker,
    client: Tracker,
    reference: str,
) -> tuple[Doc | None, list[TrackedIssueFinding]]:
    links = list(
        session.execute(
            select(TrackedIssueFinding).where(TrackedIssueFinding.issue_id == issue.id)
        ).scalars()
    )
    found = latest_vulns(session, [(lk.target_id, lk.fingerprint) for lk in links])
    vulns = sorted(found.values(), key=lambda v: v.matched_at or "")
    if not vulns:
        return None, links
    target_value = session.scalar(
        select(Target.target_value).where(Target.id == issue.target_id)
    )
    doc = bodies.issue_body(
        vulns,
        target_value or "",
        TRACKERS_BY_KIND[tracker.kind],
        grouped=issue.grouped,
        public=_is_public(client, issue.destination),
        reference=reference,
    )
    return doc, links


def _claim(
    session: Session,
    issue_ids: list[uuid.UUID] | None,
    skip_trackers: set[uuid.UUID],
    older_than: timedelta | None,
) -> TrackedIssue | None:
    stmt = (
        select(TrackedIssue)
        .where(TrackedIssue.state == FilingState.PENDING.value)
        .order_by(TrackedIssue.created_at)
        .limit(1)
        .with_for_update(skip_locked=True, key_share=True)
    )
    if issue_ids is not None:
        stmt = stmt.where(TrackedIssue.id.in_(issue_ids))
    if skip_trackers:
        stmt = stmt.where(TrackedIssue.tracker_id.not_in(skip_trackers))
    if older_than is not None:
        stmt = stmt.where(TrackedIssue.updated_at < utc_now() - older_than)
    return session.execute(stmt).scalar_one_or_none()


def _fail(issue: TrackedIssue, message: str) -> None:
    issue.state = FilingState.FAILED.value
    issue.error = message[:MAX_ERROR]
    issue.updated_at = utc_now()


def _record(
    issue: TrackedIssue, made, links: list[TrackedIssueFinding], status: str | None
) -> None:
    now = utc_now()
    issue.state = FilingState.FILED.value
    issue.external_key = made.key
    issue.external_id = made.external_id
    issue.url = made.url if made.url.startswith(("https://", "http://")) else None
    issue.remote_category = RemoteCategory.TODO.value
    issue.remote_status = status
    issue.error = None
    issue.filed_at = now
    issue.updated_at = now
    for link in links:
        link.announced = True


def _create(
    session: Session, issue: TrackedIssue, tracker: IssueTracker, client: Tracker
):
    """The remote issue for a claimed row, or the reason it was not filed."""
    marker = bodies.marker(issue.id)
    doc, links = _body_for(session, issue, tracker, client, marker)
    if doc is None:
        return None, links, "Findings for this issue were deleted."
    if issue.attempts > 1:
        found = client.find_marker(issue.destination, marker)
        if found is not None:
            return found, links, None
    made = client.create(
        issue.destination,
        issue.issue_type,
        issue.title,
        doc,
        bodies.labels_for(issue.severity),
    )
    return made, links, None


def _serialize(session: Session, tracker: IssueTracker) -> None:
    """Hold the tracker's lock until the transaction ends."""
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": locks.issue_tracker(tracker.id)},
    )


def _pace(tracker: IssueTracker) -> None:
    time.sleep(TRACKERS_BY_KIND[tracker.kind].create_interval)


FILED = "filed"
FAILED = "failed"
LIMITED = "limited"


def _file_claimed(
    session: Session,
    issue: TrackedIssue,
    tracker: IssueTracker | None,
    clients: _Clients,
) -> str:
    """File one claimed row and commit its outcome."""
    issue.attempts += 1
    if tracker is None or not tracker.is_active:
        _fail(issue, "Tracker is disabled.")
        session.commit()
        return FAILED
    _serialize(session, tracker)
    try:
        made, links, refusal = _create(session, issue, tracker, clients.of(tracker))
    except RateLimitedError as exc:
        issue.error = _error(exc, tracker)
        issue.updated_at = utc_now()
        session.commit()
        return LIMITED
    except RemoteNotFoundError:
        spec = TRACKERS_BY_KIND[tracker.kind]
        made, links, refusal = (
            None,
            [],
            _NOT_FOUND.format(
                label=spec.label,
                destination=issue.destination,
                noun=spec.destination_label.lower(),
            ),
        )
    except TrackerError as exc:
        made, links, refusal = None, [], _error(exc, tracker)
    except Exception:
        logger.warning("issue filing failed", issue=str(issue.id), exc_info=True)
        made, links, refusal = None, [], None
    _pace(tracker)
    if made is None:
        _fail(issue, refusal or "Issue not filed.")
        session.commit()
        return FAILED
    _record(issue, made, links, clients.of(tracker).initial_status)
    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.warning("issue record failed", issue=str(issue.id), exc_info=True)
        fresh = session.get(TrackedIssue, issue.id)
        if fresh is not None:
            _fail(fresh, _UNRECORDED.format(key=made.key))
            session.commit()
        return FAILED
    return FILED


def file_pending(
    session: Session,
    issue_ids: list[uuid.UUID] | None = None,
    *,
    older_than: timedelta | None = None,
) -> int:
    """File pending issues one at a time, paced per tracker kind."""
    clients = _Clients()
    trackers: dict[uuid.UUID, IssueTracker | None] = {}
    filed: dict[tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
    failed: dict[tuple[uuid.UUID, uuid.UUID], list[str]] = defaultdict(list)
    limited: set[uuid.UUID] = set()
    touched: set[uuid.UUID] = set()
    try:
        while (issue := _claim(session, issue_ids, limited, older_than)) is not None:
            if issue.tracker_id not in trackers:
                trackers[issue.tracker_id] = session.get(IssueTracker, issue.tracker_id)
            tracker = trackers[issue.tracker_id]
            key = (issue.project_id, issue.tracker_id)
            title = issue.title
            touched.add(issue.target_id)
            outcome = _file_claimed(session, issue, tracker, clients)
            if outcome == LIMITED:
                limited.add(issue.tracker_id)
                continue
            if outcome == FILED:
                filed[key] += 1
            else:
                failed[key].append(title)
    finally:
        clients.close()
    _log_filing(session, trackers, filed, failed)
    if touched:
        bump_sync(touched)
    return sum(filed.values())


def _named(text: str, tracker: IssueTracker | None) -> str:
    return f"{text} · {tracker.name}" if tracker else text


def _log_filing(
    session: Session,
    trackers: dict[uuid.UUID, IssueTracker | None],
    filed: dict[tuple[uuid.UUID, uuid.UUID], int],
    failed: dict[tuple[uuid.UUID, uuid.UUID], list[str]],
) -> None:
    log = ActivityLogService(session)
    for (project_id, tracker_id), count in filed.items():
        log.log(
            event=ActivityEvent.ISSUE_FILED,
            title=_named(f"{counted(count, 'issue')} filed", trackers.get(tracker_id)),
            level=ActivityLevel.SUCCESS,
            project_id=project_id,
        )
    for (project_id, tracker_id), titles in failed.items():
        log.log(
            event=ActivityEvent.ISSUE_FAILED,
            title=_named(
                f"{counted(len(titles), 'issue')} not filed", trackers.get(tracker_id)
            ),
            description="\n".join(titles[:10]),
            level=ActivityLevel.ERROR,
            project_id=project_id,
        )
    session.commit()


def sweep_pending(session: Session) -> int:
    """File issues pending past the grace period."""
    return file_pending(session, older_than=timedelta(seconds=PENDING_GRACE_SECONDS))


# ---------- comments ----------


def comment_row(
    issue_id: uuid.UUID,
    kind: CommentKind,
    doc: Doc,
    scan_id: uuid.UUID | None = None,
) -> TrackedIssueComment:
    return TrackedIssueComment(
        issue_id=issue_id,
        kind=kind.value,
        body=json.dumps(dump_doc(doc)),
        scan_id=scan_id,
    )


def queue_comment(
    session: Session,
    issue: TrackedIssue,
    kind: CommentKind,
    doc: Doc,
    scan_id: uuid.UUID | None = None,
) -> None:
    session.add(comment_row(issue.id, kind, doc, scan_id))


def announce(session: Session, issue_ids: Iterable[uuid.UUID] | None = None) -> int:
    """Queue one comment per filed issue for its unannounced locations."""
    stmt = (
        select(TrackedIssueFinding)
        .join(TrackedIssue, TrackedIssue.id == TrackedIssueFinding.issue_id)
        .where(
            TrackedIssueFinding.announced.is_(False),
            TrackedIssue.state == FilingState.FILED.value,
        )
        .order_by(TrackedIssueFinding.added_at)
        .with_for_update(of=TrackedIssueFinding, skip_locked=True, key_share=True)
    )
    if issue_ids is not None:
        stmt = stmt.where(TrackedIssueFinding.issue_id.in_(list(issue_ids)))
    links = list(session.execute(stmt).scalars())
    if not links:
        session.commit()
        return 0
    found = latest_vulns(session, [(lk.target_id, lk.fingerprint) for lk in links])
    per_issue: dict[uuid.UUID, list[TrackedIssueFinding]] = defaultdict(list)
    for link in links:
        per_issue[link.issue_id].append(link)
        link.announced = True
    for issue_id, members in per_issue.items():
        lead = next(
            (
                found[(lk.target_id, lk.fingerprint)]
                for lk in members
                if (lk.target_id, lk.fingerprint) in found
            ),
            None,
        )
        link = bodies.finding_link(lead.scan_id, lead.id) if lead else ""
        session.add(
            comment_row(
                issue_id,
                CommentKind.ADDED,
                bodies.added_comment([lk.matched_at for lk in members], link),
            )
        )
    session.commit()
    return len(per_issue)


def _claim_comment(session: Session, comment_id: uuid.UUID):
    return session.execute(
        select(TrackedIssueComment, TrackedIssue, IssueTracker)
        .join(TrackedIssue, TrackedIssue.id == TrackedIssueComment.issue_id)
        .join(IssueTracker, IssueTracker.id == TrackedIssue.tracker_id)
        .where(
            TrackedIssueComment.id == comment_id,
            TrackedIssueComment.state == CommentState.PENDING.value,
        )
        .with_for_update(of=TrackedIssueComment, skip_locked=True)
    ).first()


def send_comments(
    session: Session, issue_ids: Iterable[uuid.UUID] | None = None
) -> int:
    """Send queued comments on filed issues, one claim per comment."""
    stmt = (
        select(TrackedIssueComment.id)
        .join(TrackedIssue, TrackedIssue.id == TrackedIssueComment.issue_id)
        .join(IssueTracker, IssueTracker.id == TrackedIssue.tracker_id)
        .where(
            TrackedIssueComment.state == CommentState.PENDING.value,
            TrackedIssue.state == FilingState.FILED.value,
            IssueTracker.is_active.is_(True),
        )
        .order_by(TrackedIssueComment.created_at)
    )
    if issue_ids is not None:
        stmt = stmt.where(TrackedIssueComment.issue_id.in_(list(issue_ids)))
    ids = list(session.execute(stmt).scalars())
    session.commit()
    clients = _Clients()
    sent = 0
    try:
        for comment_id in ids:
            row = _claim_comment(session, comment_id)
            if row is None:
                session.commit()
                continue
            comment, issue, tracker = row
            comment.attempts += 1
            _serialize(session, tracker)
            try:
                clients.of(tracker).comment(
                    issue.destination,
                    issue.external_id or "",
                    load_doc(json.loads(comment.body)),
                )
            except TrackerError as exc:
                comment.error = _error(exc, tracker)
                if comment.attempts >= MAX_COMMENT_ATTEMPTS:
                    comment.state = CommentState.FAILED.value
            else:
                comment.state = CommentState.SENT.value
                comment.error = None
                comment.sent_at = utc_now()
                sent += 1
            _pace(tracker)
            session.commit()
    finally:
        clients.close()
    return sent


# ---------- status ----------


def refresh_statuses(session: Session, *, force: bool = False) -> int:
    """Read each filed issue's status from its tracker."""
    stmt = (
        select(TrackedIssue)
        .join(IssueTracker, IssueTracker.id == TrackedIssue.tracker_id)
        .where(
            TrackedIssue.state == FilingState.FILED.value,
            TrackedIssue.external_id.is_not(None),
            IssueTracker.is_active.is_(True),
        )
        .order_by(TrackedIssue.status_read_at.asc().nulls_first())
        .limit(MAX_STATUS_READS)
    )
    if not force:
        cutoff = utc_now() - timedelta(seconds=STATUS_REFRESH_SECONDS)
        stmt = stmt.where(
            (TrackedIssue.status_read_at.is_(None))
            | (TrackedIssue.status_read_at < cutoff)
        )
    issues = session.execute(stmt).scalars().all()
    groups: dict[tuple[uuid.UUID, str], list[TrackedIssue]] = defaultdict(list)
    for issue in issues:
        groups[(issue.tracker_id, issue.destination)].append(issue)
    read = 0
    moved: set[uuid.UUID] = set()
    for (tracker_id, destination), members in groups.items():
        tracker = session.get(IssueTracker, tracker_id)
        if tracker is None:
            continue
        now = utc_now()
        try:
            client = tracker_client(tracker)
            try:
                found = client.statuses(
                    destination, [m.external_id or "" for m in members]
                )
            finally:
                client.close()
        except TrackerError as exc:
            logger.warning(
                "issue status read failed",
                tracker=str(tracker_id),
                error=_error(exc, tracker),
            )
            for issue in members:
                issue.status_read_at = now
            _commit(session)
            continue
        for issue in members:
            status = found.get(issue.external_id or "")
            name = status.name if status else NOT_FOUND
            category = status.category if status else None
            if name == UNREADABLE:
                category = issue.remote_category
            if (name, category) != (issue.remote_status, issue.remote_category):
                moved.add(issue.target_id)
            issue.remote_status = name
            issue.remote_category = category
            if category != RemoteCategory.DONE.value:
                issue.done_noted = False
            issue.status_read_at = now
            read += 1
        _commit(session)
    if moved:
        bump_sync(moved)
    return read


def _commit(session: Session) -> None:
    try:
        session.commit()
    except StaleDataError:
        session.rollback()


# ---------- rescans ----------


def _stages_ran(session: Session, scan: Scan) -> dict[str, str] | None:
    """Vulnerability stages the run started, or None unless all succeeded."""
    dimension = SurfaceDimension.VULNERABILITIES.value
    rows = session.execute(
        select(ScanActivity.name, ScanActivity.status).where(
            ScanActivity.scan_id == scan.id,
            ScanActivity.name.in_(producing_stages()[dimension]),
        )
    ).all()
    ran = {
        name: status
        for name, status in rows
        if status != ScanActivityStatus.SKIPPED.value
    }
    if not ran or not set(ran) & covering_stages()[dimension]:
        return None
    if any(status != ScanActivityStatus.SUCCESS.value for status in ran.values()):
        return None
    return ran


def _scanned_hosts(session: Session, scan: Scan) -> set[tuple[str, int | None]]:
    """Each scanned (host, port), and (host, None) for every scanned host."""
    out: set[tuple[str, int | None]] = set()
    for host, port in session.execute(
        select(ScanSurfaceItem.host, ScanSurfaceItem.port).where(
            ScanSurfaceItem.scan_id == scan.id,
            ScanSurfaceItem.state.in_(SCANNED_STATES),
        )
    ).all():
        if host:
            out.add((host.lower(), port))
            out.add((host.lower(), None))
    return out


def _stage_config(model, configs: dict, name: str, ran: dict[str, str]):
    if name not in ran:
        return None
    try:
        return model.model_validate(configs.get(name) or {})
    except ValidationError:
        return None


def _selected_checks(
    session: Session,
    scan: Scan,
    ran: dict[str, str],
    vulns: Iterable[Vulnerability],
) -> set[str]:
    """Check ids among these findings that the run selected and could send."""
    from stages.dast_scan.config import DastScanConfig  # noqa: PLC0415
    from stages.vulnerability_scan.config import (  # noqa: PLC0415
        VulnerabilityScanConfig,
    )

    configs = (scan.execution_config or {}).get("stages") or {}
    fuzzed: set[str] = set()
    plain: set[str] = set()
    for vuln in vulns:
        if vuln.template_id:
            (fuzzed if DAST_TAG in (vuln.tags or []) else plain).add(vuln.template_id)
    columns = (VulnTemplate.template_id, VulnTemplate.needs_oast, VulnTemplate.tags)
    rows: list = []
    cfg = _stage_config(VulnerabilityScanConfig, configs, VULN_STAGE, ran)
    if plain and cfg is not None and Scanner.NUCLEI.value in cfg.scanners:
        selection = cfg.selection()
        wanted = VulnTemplate.template_id.in_(sorted(plain))
        rows += session.execute(
            select(*columns).where(selection_predicate(selection), wanted)
        ).all()
        if selection.custom_templates:
            rows += session.execute(
                select(*columns).where(
                    VulnTemplate.id.in_(list(selection.custom_templates)),
                    VulnTemplate.enabled.is_(True),
                    wanted,
                )
            ).all()
    dast = _stage_config(DastScanConfig, configs, DAST_STAGE, ran)
    if fuzzed and dast is not None and Scanner.NUCLEI.value in dast.scanners:
        rows += session.execute(
            select(*columns).where(
                dast_predicate(dast.severities, headless=dast.headless),
                VulnTemplate.template_id.in_(sorted(fuzzed)),
            )
        ).all()
    if not rows:
        return set()
    unheard = session.scalar(
        select(
            exists(
                select(VulnerabilityCoverage.id).where(
                    VulnerabilityCoverage.scan_id == scan.id,
                    VulnerabilityCoverage.group == OAST_COVERAGE_GROUP,
                    VulnerabilityCoverage.status == CoverageStatus.SKIPPED.value,
                )
            )
        )
    )
    return {row.template_id for row in rows if not (unheard and wants_callback(row))}


def _checked_again(
    vuln: Vulnerability | None,
    hosts: set[tuple[str, int | None]],
    selected: set[str],
) -> bool:
    """The run selected this finding's check and tested this finding's host."""
    if vuln is None or vuln.scanner != Scanner.NUCLEI.value or not vuln.host:
        return False
    return (
        vuln.template_id in selected and (vuln.host.lower(), vuln.port or None) in hosts
    )


def _superseded(session: Session, scan: Scan) -> bool:
    later = select(Scan.id).where(
        Scan.target_id == scan.target_id,
        Scan.scope == ScanScope.FULL.value,
        Scan.status == ScanStatus.COMPLETED.value,
        Scan.completed_at > scan.completed_at,
    )
    return bool(session.scalar(select(exists(later))))


def observe_scan(session: Session, scan_id: uuid.UUID) -> int:
    """Record which linked findings a completed census run observes and queue comments."""
    scan = session.get(Scan, scan_id)
    if (
        scan is None
        or scan.scope != ScanScope.FULL.value
        or scan.status != ScanStatus.COMPLETED.value
    ):
        return 0
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": locks.issue_observe(scan.target_id)},
    )
    if scan.completed_at is not None and _superseded(session, scan):
        session.commit()
        return 0
    rows = session.execute(
        select(TrackedIssueFinding, TrackedIssue)
        .join(TrackedIssue, TrackedIssue.id == TrackedIssueFinding.issue_id)
        .where(
            TrackedIssueFinding.target_id == scan.target_id,
            TrackedIssue.state == FilingState.FILED.value,
        )
    ).all()
    if not rows:
        session.commit()
        return 0
    seen = set(
        session.execute(
            select(Vulnerability.fingerprint).where(Vulnerability.scan_id == scan.id)
        ).scalars()
    )
    ran = _stages_ran(session, scan)
    missing = [lk for lk, _ in rows if lk.present and lk.fingerprint not in seen]
    earlier = latest_vulns(session, [(lk.target_id, lk.fingerprint) for lk in missing])
    hosts = _scanned_hosts(session, scan) if ran and missing else set()
    selected = (
        _selected_checks(session, scan, ran, earlier.values())
        if ran and missing
        else set()
    )
    per_issue: dict[uuid.UUID, tuple[TrackedIssue, list[TrackedIssueFinding]]] = {}
    for link, issue in rows:
        per_issue.setdefault(issue.id, (issue, []))[1].append(link)
    queued = 0
    for issue, links in per_issue.values():
        gone = [
            lk
            for lk in links
            if lk.present
            and lk.fingerprint not in seen
            and ran is not None
            and _checked_again(
                earlier.get((lk.target_id, lk.fingerprint)), hosts, selected
            )
        ]
        back = [lk for lk in links if not lk.present and lk.fingerprint in seen]
        still = [lk for lk in links if lk.fingerprint in seen]
        for link in gone:
            link.present = False
        for link in back:
            link.present = True
        done = issue.remote_category == RemoteCategory.DONE.value
        comments: list[tuple[CommentKind, list[TrackedIssueFinding]]] = []
        if done and still and not issue.done_noted:
            issue.done_noted = True
            comments.append((CommentKind.STILL_OBSERVED, still))
        elif back:
            comments.append((CommentKind.OBSERVED_AGAIN, back))
        if gone:
            comments.append((CommentKind.NOT_OBSERVED, gone))
        for kind, locations in comments:
            queue_comment(
                session,
                issue,
                kind,
                bodies.presence_comment(
                    kind,
                    [lk.matched_at for lk in locations],
                    scan.id,
                    scan.completed_at,
                    issue.remote_status,
                ),
                scan.id,
            )
            queued += 1
    session.commit()
    if queued:
        send_comments(session, per_issue.keys())
    bump_sync([scan.target_id])
    return queued
