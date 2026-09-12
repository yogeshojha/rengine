"""Certificates for a watched program become hosts of the target's covering scan."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from shared.config import BaseAppSettings
from shared.definitions.mode_features import CAP_PROGRAM_WATCHES, has_capability
from shared.definitions.notifications import WatchAlert, watch_alert
from shared.definitions.rescan import ASSET_SEED_STAGE, SeedKind
from shared.definitions.schedule_constants import MAX_SCHEDULE_TARGETS
from shared.definitions.surface import SurfaceDimension
from shared.definitions.watch import (
    CT_SOURCE,
    MAX_SCOPE_EVENTS,
    PROBE_RUN_LABEL,
    PROBE_STAGES,
    UNRESOLVED_RETRY_HOURS,
    WATCH_HOST_KEY,
    WATCH_RUN_LABEL,
    ScopePlan,
    WatchEventKind,
    WatchHostState,
    WatchItem,
    WatchStatus,
    excluded_by,
    plan_scope,
)
from shared.enums.activity import ActivityEvent
from shared.enums.scan import SCAN_TERMINAL_STATUSES, Intensity, ScanScope, ScanStatus
from shared.enums.scan_schedule import ScheduleStatus
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.bounty_program import BountyProgram, BountyScope
from shared.models.http_asset import HttpAsset
from shared.models.instance_settings import InstanceSettings
from shared.models.notification_channel import NotificationChannel
from shared.models.organization import Organization
from shared.models.project import Project
from shared.models.scan import Scan
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.scan_schedule import ScanSchedule
from shared.models.subdomain import Subdomain
from shared.models.target import Target, TargetOrganization
from shared.models.watch import ProgramWatch, WatchEvent, WatchHost
from shared.services.asset_query import (
    QueryContext,
    QueryScope,
    QuerySyntaxError,
    compile_query,
    parse_query,
)
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.celery_dispatch import (
    dispatch_dns_lookups,
    dispatch_ripestat_enrichment,
    dispatch_scan_run,
    dispatch_whois_lookups,
)
from shared.services.focused import focused_overrides
from shared.services.launch_plan import AdHocEngine
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.notifier import dispatch_sync
from shared.services.proxy_resolve import resolve_proxy_url
from shared.services.proxy_sync import census_in_flight
from shared.services.scan_factory import build_scan_row
from shared.services.scan_resolve import merge_engine_context
from shared.services.scan_scope import census_only, covers
from shared.utils.datetime import utc_now
from shared.utils.validation import validate_target

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

_DIMENSION = SurfaceDimension.WEB_ASSETS.value
_MEDIA_ROOT = "/app/scan_media"
_RETRY_LADDER = ((1, 10), (6, 30), (24, 60))
_RETRY_LATE_MINUTES = 180
_MAX_TECH = 12
_ANSWERED = range(200, 400)


# ---------- lookups ----------


def items_of(watch: ProgramWatch) -> list[WatchItem]:
    return [WatchItem.from_dict(raw) for raw in (watch.watch_items or [])]


def watches_enabled(session: Session) -> bool:
    """Bug bounty mode only."""
    mode = session.scalar(select(InstanceSettings.mode).limit(1))
    return has_capability(mode, CAP_PROGRAM_WATCHES)


def active_watches(session: Session, program_id=None) -> list[ProgramWatch]:
    """Active watches in active projects, none outside bug bounty mode."""
    if not watches_enabled(session):
        return []
    stmt = (
        select(ProgramWatch)
        .join(Project, Project.id == ProgramWatch.project_id)
        .where(
            ProgramWatch.status == WatchStatus.ACTIVE.value,
            Project.is_active.is_(True),
        )
    )
    if program_id is not None:
        stmt = stmt.where(ProgramWatch.program_id == program_id)
    return list(session.execute(stmt).scalars().all())


def match(
    name: str, watches: list[ProgramWatch]
) -> list[tuple[ProgramWatch, WatchItem]]:
    """Every watch whose items cover the name, longest item first."""
    hits: list[tuple[ProgramWatch, WatchItem]] = []
    for watch in watches:
        best = None
        for item in items_of(watch):
            if item.matches(name) and (best is None or len(item.apex) > len(best.apex)):
                best = item
        if best is not None:
            hits.append((watch, best))
    return hits


def target_for(session: Session, watch: ProgramWatch, item: WatchItem) -> Target | None:
    return session.scalar(
        select(Target).where(
            Target.project_id == watch.project_id,
            Target.target_value == item.target_value,
        )
    )


def context_of(session: Session, watch: ProgramWatch) -> ScanContext | None:
    if watch.context_id is None:
        return None
    ctx = session.get(ScanContext, watch.context_id)
    if ctx is None or ctx.project_id != watch.project_id:
        return None
    return ctx


def known_host(session: Session, project_id, name: str) -> bool:
    """Any inventory of the project already holds the name."""
    return bool(
        session.scalar(
            select(func.count())
            .select_from(Subdomain)
            .where(
                Subdomain.project_id == project_id,
                Subdomain.name == name,
                Subdomain.is_excluded.is_(False),
            )
            .limit(1)
        )
    )


def log_event(
    session: Session,
    watch: ProgramWatch,
    kind: str,
    *,
    name: str | None = None,
    detail: str | None = None,
) -> WatchEvent:
    row = WatchEvent(
        watch_id=watch.id,
        project_id=watch.project_id,
        kind=kind,
        name=(name or None) and name[:500],
        detail=(detail or None) and detail[:500],
    )
    session.add(row)
    return row


# ---------- covering scan ----------


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def covering_scan(session: Session, project_id, target_id) -> Scan | None:
    """The settled census scan the target's Web Assets view reads."""
    return session.scalar(
        select(Scan)
        .where(
            Scan.project_id == project_id,
            Scan.target_id == target_id,
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
            census_only(),
            covers(Subdomain, _DIMENSION),
        )
        .order_by(_started().desc())
        .limit(1)
    )


def watching_run(
    session: Session, watch: ProgramWatch, program_name: str, target: Target
) -> Scan:
    """The run that holds certificate hosts for a target without a census scan."""
    label = f"{WATCH_RUN_LABEL} · {program_name}"[:200]
    existing = session.scalar(
        select(Scan)
        .where(
            Scan.project_id == watch.project_id,
            Scan.target_id == target.id,
            Scan.engine_name == label,
            Scan.scope == ScanScope.FULL.value,
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        return existing
    now = utc_now()
    run = Scan(
        project_id=watch.project_id,
        target_id=target.id,
        engine_id=None,
        engine_name=label,
        scope=ScanScope.FULL.value,
        status=ScanStatus.COMPLETED.value,
        execution_config={
            "manual": True,
            "watch": str(watch.id),
            "target_value": target.target_value,
        },
        started_at=now,
        completed_at=now,
        created_by=watch.created_by,
    )
    session.add(run)
    session.flush()
    return run


def write_host(
    session: Session,
    *,
    scan: Scan,
    name: str,
    ips: list[str],
    cname: str | None,
    is_wildcard: bool,
) -> Subdomain:
    """One host row in the scan, carrying the certificate log as a source."""
    row = session.scalar(
        select(Subdomain).where(Subdomain.scan_id == scan.id, Subdomain.name == name)
    )
    now = utc_now()
    if row is None:
        row = Subdomain(
            scan_id=scan.id,
            target_id=scan.target_id,
            project_id=scan.project_id,
            name=name,
            sources=[CT_SOURCE],
            resolved_ips=list(ips),
            cname=cname,
            is_active=bool(ips),
            is_wildcard=is_wildcard,
            discovered_at=now,
            created_at=now,
        )
        session.add(row)
    else:
        sources = list(row.sources or [])
        if CT_SOURCE not in sources:
            row.sources = [*sources, CT_SOURCE]
        if ips and not row.resolved_ips:
            row.resolved_ips = list(ips)
            row.cname = cname
            row.is_active = True
    session.flush()
    bump_sync([scan.target_id])
    return row


def place_host(
    session: Session,
    *,
    watch: ProgramWatch,
    program_name: str,
    target: Target,
    host: WatchHost,
) -> Scan | None:
    """Write the host into the covering scan. None while a census scan runs."""
    scan = covering_scan(session, watch.project_id, target.id)
    if scan is None:
        if census_in_flight(session, watch.project_id, target.id):
            return None
        scan = watching_run(session, watch, program_name, target)
    write_host(
        session,
        scan=scan,
        name=host.name,
        ips=list(host.resolved_ips or []),
        cname=host.cname,
        is_wildcard=host.is_wildcard,
    )
    return scan


# ---------- sightings ----------


def _parse_when(raw) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def record_sighting(
    session: Session,
    *,
    watch: ProgramWatch,
    target: Target,
    item: WatchItem,
    name: str,
    cert: dict,
) -> tuple[WatchHost, bool]:
    """Upsert the name in the watch ledger. Returns the row and whether it is new."""
    now = utc_now()
    row = session.scalar(
        select(WatchHost).where(WatchHost.watch_id == watch.id, WatchHost.name == name)
    )
    issuer = (cert.get("issuer") or None) and str(cert.get("issuer"))[:500]
    if row is not None:
        row.sightings += 1
        row.last_seen_at = now
        row.cert_sha256 = (cert.get("sha256") or row.cert_sha256 or None) and str(
            cert.get("sha256") or row.cert_sha256
        )[:64]
        row.issuer = issuer or row.issuer
        row.not_before = _parse_when(cert.get("not_before")) or row.not_before
        session.flush()
        return row, False
    row = WatchHost(
        watch_id=watch.id,
        project_id=watch.project_id,
        target_id=target.id,
        name=name,
        state=WatchHostState.NEW.value,
        matched_item=item.item,
        cert_sha256=(cert.get("sha256") or None) and str(cert.get("sha256"))[:64],
        issuer=issuer,
        not_before=_parse_when(cert.get("not_before")),
        first_seen_at=now,
        last_seen_at=now,
    )
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(WatchHost).where(
                WatchHost.watch_id == watch.id, WatchHost.name == name
            )
        )
        if existing is None:
            raise
        existing.sightings += 1
        existing.last_seen_at = now
        session.flush()
        return existing, False
    watch.hosts_seen += 1
    watch.last_certificate_at = now
    session.flush()
    return row, True


def next_retry(host: WatchHost) -> datetime | None:
    """Back off resolution attempts; give up after the retry window."""
    age = utc_now() - host.first_seen_at
    if age > timedelta(hours=UNRESOLVED_RETRY_HOURS):
        return None
    hours = age.total_seconds() / 3600
    minutes = next((m for h, m in _RETRY_LADDER if hours < h), _RETRY_LATE_MINUTES)
    return utc_now() + timedelta(minutes=minutes)


def set_state(host: WatchHost, state: str, reason: str | None = None) -> None:
    host.state = state
    host.reason = (reason or None) and reason[:200]


# ---------- probe ----------


def build_probe_scan(
    session: Session, *, watch: ProgramWatch, target: Target, host: WatchHost
) -> Scan:
    """A focused run that probes and screenshots one host with the watch's context."""
    engine = None
    if watch.probe_engine_id is not None:
        engine = session.get(ScanEngine, watch.probe_engine_id)
        if engine is not None and engine.project_id != watch.project_id:
            engine = None
    label = f"{PROBE_RUN_LABEL} · {host.name}"[:200]
    if engine is None:
        engine = AdHocEngine(name=label)
    context = context_of(session, watch)
    proxy_url = None
    if context is not None and context.proxy_id is not None:
        from shared.models.proxy import Proxy  # noqa: PLC0415

        proxy_url = resolve_proxy_url(session.get(Proxy, context.proxy_id))
    resolved = merge_engine_context(
        engine,
        context,
        target.target_value,
        target.target_type.value,
        proxy_url=proxy_url,
        overrides=focused_overrides(PROBE_STAGES),
        intensity=Intensity.NORMAL.value,
    )
    resolved.seed_assets = [{"kind": SeedKind.HOST.value, "value": host.name}]
    resolved.stages[ASSET_SEED_STAGE] = {
        **(resolved.stages.get(ASSET_SEED_STAGE) or {}),
        "enabled": True,
    }
    scan = build_scan_row(
        resolved=resolved,
        engine=engine,
        context=context,
        target=target,
        project_id=watch.project_id,
        created_by=watch.created_by,
        dimension=_DIMENSION,
    )
    scan.execution_config = {**scan.execution_config, WATCH_HOST_KEY: str(host.id)}
    session.add(scan)
    session.flush()
    return scan


def dispatch_probe(
    session: Session, *, watch: ProgramWatch, target: Target, host: WatchHost
) -> Scan | None:
    try:
        scan = build_probe_scan(session, watch=watch, target=target, host=host)
    except Exception as exc:
        logger.warning("watch probe not built", host=host.name, error=str(exc))
        watch.last_error = f"Probe not built for {host.name}: {exc}"[:500]
        return None
    claimed = session.execute(
        update(WatchHost)
        .where(WatchHost.id == host.id, WatchHost.state != WatchHostState.PROBING.value)
        .values(state=WatchHostState.PROBING.value, scan_id=scan.id, reason=host.reason)
    ).rowcount
    if not claimed:
        session.delete(scan)
        session.commit()
        session.refresh(host)
        return None
    session.commit()
    session.refresh(host)
    try:
        dispatch_scan_run(str(scan.id))
    except Exception as exc:
        logger.warning("watch probe not queued", scan=str(scan.id), error=str(exc))
        scan.status = ScanStatus.FAILED.value
        scan.error = "Not queued. Check that the worker is running."
        scan.completed_at = utc_now()
        watch.last_error = f"Probe not queued for {host.name}."
        session.commit()
    return scan


# ---------- settle ----------


def fingerprint(
    status_code: int | None, title: str | None, tech: list[str], ips: list[str]
) -> str:
    raw = "|".join(
        [
            str(status_code or ""),
            (title or "").strip().lower(),
            ",".join(sorted(t.lower() for t in tech)),
            ",".join(sorted(ips)),
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _best_asset(session: Session, scan_id, name: str) -> HttpAsset | None:
    rows = list(
        session.execute(
            select(HttpAsset).where(
                HttpAsset.scan_id == scan_id, HttpAsset.host == name
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return None

    def rank(row: HttpAsset) -> tuple:
        code = row.status_code or 999
        return (
            0 if row.screenshot_path else 1,
            0 if code in _ANSWERED else 1,
            0 if row.scheme == "https" else 1,
            code,
        )

    return sorted(rows, key=rank)[0]


def alert_matches(
    session: Session, watch: ProgramWatch, scan_id, name: str
) -> bool | None:
    """Evaluate the watch's alert query against the host in that scan."""
    query = (watch.alert_query or "").strip()
    if not query:
        return True
    try:
        predicate = compile_query(
            parse_query(query),
            QueryContext(scope=QueryScope((scan_id,)), now=utc_now()),
        )
    except QuerySyntaxError as exc:
        watch.last_error = f"Alert query rejected: {exc.message}"[:500]
        return None
    stmt = select(Subdomain.id).where(
        Subdomain.scan_id == scan_id, Subdomain.name == name
    )
    if predicate is not None:
        stmt = stmt.where(predicate)
    return session.scalar(stmt.limit(1)) is not None


def _screenshot_file(path: str | None) -> str | None:
    if not path:
        return None
    root = Path(_MEDIA_ROOT).resolve()
    full = (root / path).resolve()
    if not full.is_relative_to(root) or full.suffix.lower() != ".png":
        return None
    return str(full) if full.is_file() else None


def _live_channels(session: Session, watch: ProgramWatch) -> list[uuid.UUID]:
    """The chosen channels that still exist; type routing when none do."""
    chosen = [uuid.UUID(str(c)) for c in (watch.channel_ids or [])]
    if not chosen:
        return []
    live = list(
        session.execute(
            select(NotificationChannel.id).where(
                NotificationChannel.id.in_(chosen),
                NotificationChannel.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    if not live:
        watch.last_error = (
            "The chosen notification channels are gone. Alerts go to channels "
            "subscribed to Program watches."
        )
    return live


def send_alert(
    session: Session,
    *,
    watch: ProgramWatch,
    program: BountyProgram,
    host: WatchHost,
    repeat: bool,
) -> None:
    payload = watch_alert(
        WatchAlert(
            program=program.name,
            host=host.name,
            matched_item=host.matched_item,
            status_code=host.status_code,
            title=host.title,
            tech=tuple(host.tech or [])[:_MAX_TECH],
            ips=tuple(host.resolved_ips or []),
            issuer=host.issuer,
            not_before=host.not_before,
            scan_id=str(host.scan_id) if host.scan_id else None,
            target_id=str(host.target_id),
            wildcard=host.is_wildcard,
            repeat=repeat,
        )
    )
    channel_ids = _live_channels(session, watch)
    attach = _screenshot_file(host.screenshot_path)
    if watch.notify_in_app:
        SyncNotificationPublisher(BaseAppSettings().redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=watch.project_id,
            channel_ids=channel_ids,
            attach=attach,
        )
    else:
        dispatch_sync(
            session,
            payload["type"],
            payload["severity"],
            payload["title"],
            payload["message"],
            channel_ids=channel_ids,
            attach=attach,
        )
    now = utc_now()
    host.alerted_at = now
    host.alerts += 1
    watch.hosts_alerted += 1
    watch.last_alert_at = now
    set_state(host, WatchHostState.ALERTED.value, host.reason)
    log_event(
        session,
        watch,
        WatchEventKind.HOST_ALERTED.value,
        name=host.name,
        detail=payload["message"].split("\n", 1)[-1][:500],
    )


def settle_probe(session: Session, scan: Scan) -> str | None:
    """After the probe: read what it saw, evaluate the alert query, alert once."""
    host_id = (scan.execution_config or {}).get(WATCH_HOST_KEY)
    if not host_id:
        return None
    host = session.get(WatchHost, uuid.UUID(str(host_id)))
    if host is None:
        return None
    watch = session.get(ProgramWatch, host.watch_id)
    program = session.get(BountyProgram, watch.program_id) if watch else None
    if watch is None or program is None:
        return None
    asset = _best_asset(session, scan.id, host.name)
    row = session.scalar(
        select(Subdomain).where(
            Subdomain.scan_id == scan.id, Subdomain.name == host.name
        )
    )
    if asset is not None:
        host.status_code = asset.status_code
        host.title = (asset.title or None) and asset.title[:1000]
        host.tech = list(asset.tech or [])[:_MAX_TECH]
        host.screenshot_path = asset.screenshot_path
        if asset.ip and asset.ip not in (host.resolved_ips or []):
            host.resolved_ips = [*(host.resolved_ips or []), asset.ip]
    if row is not None and row.resolved_ips and not host.resolved_ips:
        host.resolved_ips = list(row.resolved_ips)
    host.probed_at = utc_now()
    probe_failed = asset is None and scan.status != ScanStatus.COMPLETED.value
    if probe_failed:
        set_state(host, host.state, "probe failed")
    watch.last_error = None
    held = None
    if not watches_enabled(session):
        held = "watches disabled"
    elif watch.status != WatchStatus.ACTIVE.value:
        held = "watch paused"
    if held or host.state == WatchHostState.MUTED.value:
        if held:
            set_state(host, WatchHostState.QUIET.value, held)
        session.commit()
        return host.state
    matched = (
        True if probe_failed else alert_matches(session, watch, scan.id, host.name)
    )
    if matched is False:
        set_state(host, WatchHostState.QUIET.value, "alert query did not match")
    else:
        new_fp = fingerprint(
            host.status_code, host.title, list(host.tech or []), list(host.resolved_ips)
        )
        if host.fingerprint == new_fp and host.alerts:
            set_state(host, WatchHostState.ALERTED.value, "unchanged")
        else:
            repeat = bool(host.alerts)
            host.fingerprint = new_fp
            send_alert(session, watch=watch, program=program, host=host, repeat=repeat)
    session.commit()
    return host.state


def alert_without_probe(
    session: Session, *, watch: ProgramWatch, program: BountyProgram, host: WatchHost
) -> None:
    new_fp = fingerprint(None, None, [], list(host.resolved_ips or []))
    if host.fingerprint == new_fp and host.alerts:
        return
    repeat = bool(host.alerts)
    host.fingerprint = new_fp
    send_alert(session, watch=watch, program=program, host=host, repeat=repeat)
    session.commit()


# ---------- reconcile ----------


def _ensure_targets(
    session: Session, plan: ScopePlan, watch: ProgramWatch
) -> tuple[list[Target], list[Target]]:
    """Targets for every in-scope value. Returns (all, created)."""
    values = [v for v, _ in plan.targets]
    if not values:
        return [], []
    existing = {
        t.target_value: t
        for t in session.execute(
            select(Target).where(
                Target.project_id == watch.project_id,
                Target.target_value.in_(values),
            )
        )
        .scalars()
        .all()
    }
    created: list[Target] = []
    for value, kind in plan.targets:
        if value in existing:
            continue
        if validate_target(value) is None:
            continue
        row = Target(
            project_id=watch.project_id,
            target_value=value,
            target_type=kind if isinstance(kind, TargetType) else TargetType(kind),
            created_by=watch.created_by,
        )
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            row = session.scalar(
                select(Target).where(
                    Target.project_id == watch.project_id,
                    Target.target_value == value,
                )
            )
            if row is None:
                continue
        else:
            created.append(row)
        existing[value] = row
    if watch.organization_id is not None:
        org = session.get(Organization, watch.organization_id)
        if org is not None and existing:
            session.execute(
                pg_insert(TargetOrganization)
                .values(
                    [
                        {"target_id": t.id, "organization_id": org.id}
                        for t in existing.values()
                    ]
                )
                .on_conflict_do_nothing()
            )
    return [existing[v] for v in values if v in existing], created


def _enrich(created: list[Target]) -> None:
    if not created:
        return
    ids = [str(t.id) for t in created]
    try:
        dispatch_whois_lookups(ids)
        domains = [str(t.id) for t in created if t.target_type is TargetType.DOMAIN]
        if domains:
            dispatch_dns_lookups(domains)
        dispatch_ripestat_enrichment(ids)
    except Exception:
        logger.warning("target enrichment not queued", exc_info=True)


def _log_targets(session: Session, created: list[Target]) -> None:
    if not created:
        return
    try:
        from shared.services.activity_log import ActivityLogService  # noqa: PLC0415

        log = ActivityLogService(session)
        for target in created:
            log.log(
                event=ActivityEvent.TARGET_CREATED,
                title=f"Target added · {target.target_value}",
                description="Added by a program watch.",
                project_id=target.project_id,
                target_id=target.id,
                target_value=target.target_value,
            )
    except Exception:
        logger.warning("target activity not logged", exc_info=True)


def _scope_events(session: Session, watch: ProgramWatch, kind: str, items, detail: str):
    for item in items[:MAX_SCOPE_EVENTS]:
        log_event(session, watch, kind, name=item.item.lstrip("."), detail=detail)
    rest = len(items) - MAX_SCOPE_EVENTS
    if rest > 0:
        log_event(session, watch, kind, detail=f"{rest} more.")


def scopes_of(session: Session, program_id) -> list[BountyScope]:
    return list(
        session.execute(select(BountyScope).where(BountyScope.program_id == program_id))
        .scalars()
        .all()
    )


def reconcile(session: Session, watch: ProgramWatch, *, initial: bool = False) -> dict:
    """Targets, exclusions, schedule and watch items follow the program's scope."""
    session.execute(
        select(ProgramWatch.id).where(ProgramWatch.id == watch.id).with_for_update()
    )
    session.refresh(watch)
    program = session.get(BountyProgram, watch.program_id)
    if program is None:
        return {"skipped": "program missing"}
    plan = plan_scope(scopes_of(session, program.id))
    if not plan.items and watch.watch_items and not initial:
        watch.last_error = "The program scope came back empty. Watch items kept."
        session.commit()
        return {"skipped": "empty scope"}
    targets, created = _ensure_targets(session, plan, watch)
    _log_targets(session, created)

    before = {i.item: i for i in items_of(watch)}
    after = {i.item: i for i in plan.items}
    added = [after[k] for k in after if k not in before]
    removed = [before[k] for k in before if k not in after]
    watch.watch_items = [i.to_dict() for i in plan.items]
    watch.unenforceable = list(plan.unenforceable)[:50]

    ctx = context_of(session, watch)
    if ctx is not None:
        ctx.excluded_subdomains = list(plan.excluded_subdomains)
        ctx.excluded_ips = list(plan.excluded_ips)
        if watch.rate_limit is not None:
            ctx.global_rate_limit_override = watch.rate_limit
        ctx.updated_at = utc_now()

    if watch.schedule_id is not None:
        sched = session.get(ScanSchedule, watch.schedule_id)
        if sched is not None and sched.project_id == watch.project_id:
            if len(targets) > MAX_SCHEDULE_TARGETS:
                watch.last_error = (
                    f"{len(targets)} targets exceed the schedule cap of "
                    f"{MAX_SCHEDULE_TARGETS}. The baseline covers the first "
                    f"{MAX_SCHEDULE_TARGETS}."
                )
            sched.target_ids = [str(t.id) for t in targets[:MAX_SCHEDULE_TARGETS]]
            sched.intensity = watch.intensity
            if not targets and sched.status == ScheduleStatus.ACTIVE.value:
                sched.status = ScheduleStatus.PAUSED.value
            sched.updated_at = utc_now()

    if not initial:
        _scope_events(
            session, watch, WatchEventKind.SCOPE_ADDED.value, added, "Watched."
        )
        _scope_events(
            session,
            watch,
            WatchEventKind.SCOPE_REMOVED.value,
            removed,
            "No longer watched.",
        )
    watch.updated_at = utc_now()
    session.commit()
    _enrich(created)
    return {
        "targets": len(targets),
        "created": len(created),
        "items": len(plan.items),
        "added": len(added),
        "removed": len(removed),
        "excluded": len(plan.excluded_subdomains) + len(plan.excluded_ips),
        "unenforceable": len(plan.unenforceable),
    }


def out_of_scope(session: Session, watch: ProgramWatch, name: str) -> bool:
    ctx = context_of(session, watch)
    patterns = list(ctx.excluded_subdomains or []) if ctx is not None else []
    if not patterns:
        program = session.get(BountyProgram, watch.program_id)
        if program is not None:
            patterns = plan_scope(scopes_of(session, program.id)).excluded_subdomains
    return excluded_by(name, patterns)
