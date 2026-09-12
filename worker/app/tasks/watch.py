"""Program watches: certificates in, probed in-scope hosts out."""

from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.watch import (
    MAX_HOST_NAME,
    MAX_NAMES_PER_CERT,
    RECHECK_BATCH,
    WatchEventKind,
    WatchHostState,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES, Intensity
from shared.logging import get_logger
from shared.models.bounty_program import BountyProgram
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.watch import ProgramWatch, WatchHost
from shared.services import watch_sync
from shared.services.watch_sync import set_state
from shared.utils.datetime import utc_now
from tools.dnsx.client import DnsxClient, DnsxError

logger = get_logger(__name__)

_RESOLVE_BASE_TIMEOUT = 30
_RESOLVE_PER_NAME = 2
_RECORD_TYPES = ["a", "aaaa", "cname"]
_OPEN_STATES = (
    WatchHostState.NEW.value,
    WatchHostState.UNRESOLVED.value,
    WatchHostState.OUT_OF_SCOPE.value,
)

Resolution = tuple[list[str], str | None, bool]
_UNRESOLVED: Resolution = ([], None, False)


def _clean_names(raw) -> list[str]:
    seen: list[str] = []
    for value in raw or []:
        name = str(value).strip().lower().rstrip(".")
        if not name or "*" in name or len(name) > MAX_HOST_NAME or name in seen:
            continue
        seen.append(name)
    return seen[:MAX_NAMES_PER_CERT]


def _sibling(name: str) -> str:
    parent = name.split(".", 1)[1] if "." in name else name
    return f"rengine-{secrets.token_hex(4)}.{parent}"


def resolve_many(names: list[str]) -> dict[str, Resolution] | None:
    """One dnsx run for every name and a random sibling of each. None when dnsx is down."""
    if not names:
        return {}
    siblings = {name: _sibling(name) for name in names}
    answers: dict[str, tuple[list[str], str | None]] = {}
    timeout = _RESOLVE_BASE_TIMEOUT + _RESOLVE_PER_NAME * len(names)
    try:
        client = DnsxClient(timeout=timeout)
        with client.stream_query(
            [*names, *siblings.values()], record_types=_RECORD_TYPES, timeout=timeout
        ) as stream:
            for rec in stream.records:
                host = (rec.get("host") or "").strip().lower().rstrip(".")
                ips = [
                    str(x) for x in [*(rec.get("a") or []), *(rec.get("aaaa") or [])]
                ]
                cnames = rec.get("cname") or []
                answers[host] = (ips, str(cnames[0]) if cnames else None)
    except DnsxError as exc:
        logger.warning("watch resolve unavailable", error=str(exc))
        return None
    out: dict[str, Resolution] = {}
    for name in names:
        ips, cname = answers.get(name, ([], None))
        sibling_ips, _ = answers.get(siblings[name], ([], None))
        wildcard = bool(ips) and bool(sibling_ips) and set(ips) <= set(sibling_ips)
        out[name] = (ips, cname, wildcard)
    return out


def _advance(
    session,
    watch: ProgramWatch,
    program: BountyProgram,
    host: WatchHost,
    resolution: Resolution,
) -> str:
    """Place and probe a resolved host; schedule a retry for one without an answer."""
    target = session.get(Target, host.target_id)
    if target is None:
        set_state(host, WatchHostState.KNOWN.value, "target removed")
        session.commit()
        return host.state
    ips, cname, wildcard = resolution
    host.resolved_ips = ips
    host.cname = cname
    host.is_wildcard = wildcard
    if not ips and not cname:
        retry = watch_sync.next_retry(host)
        set_state(
            host,
            WatchHostState.UNRESOLVED.value,
            "no DNS answer" if retry else "no DNS answer within 48 hours",
        )
        host.next_check_at = retry
        session.commit()
        if retry is None and watch.alert_unresolved:
            watch_sync.alert_without_probe(
                session, watch=watch, program=program, host=host
            )
        return host.state
    host.resolved_at = utc_now()
    if wildcard:
        set_state(host, host.state, "wildcard DNS")
    scan = watch_sync.place_host(
        session, watch=watch, program_name=program.name, target=target, host=host
    )
    if scan is None:
        host.next_check_at = utc_now() + timedelta(minutes=10)
        set_state(host, WatchHostState.NEW.value, "census scan running")
        session.commit()
        return host.state
    host.next_check_at = None
    session.commit()
    passive = watch.intensity == Intensity.PASSIVE.value
    if watch.probe_on_resolve and not passive:
        watch_sync.dispatch_probe(session, watch=watch, target=target, host=host)
        return host.state
    set_state(host, WatchHostState.QUIET.value, "passive only" if passive else None)
    watch_sync.alert_without_probe(session, watch=watch, program=program, host=host)
    return host.state


def _prepare(session, watch: ProgramWatch, item, name: str, cert: dict):
    """Record the sighting and decide whether the name needs resolving."""
    program = session.get(BountyProgram, watch.program_id)
    if program is None:
        return None
    target = watch_sync.target_for(session, watch, item)
    if target is None:
        watch.last_error = (
            f"Target {item.target_value} is missing. Add it again or wait for "
            "the next scope sync."
        )
        session.commit()
        return None
    host, created = watch_sync.record_sighting(
        session, watch=watch, target=target, item=item, name=name, cert=cert
    )
    if not created and host.state not in _OPEN_STATES:
        session.commit()
        return None
    if watch_sync.out_of_scope(session, watch, name):
        if host.state != WatchHostState.OUT_OF_SCOPE.value:
            set_state(host, WatchHostState.OUT_OF_SCOPE.value, "matches an exclusion")
            watch_sync.log_event(
                session,
                watch,
                WatchEventKind.HOST_OUT_OF_SCOPE.value,
                name=name,
                detail="Not probed. The program lists it out of scope.",
            )
        session.commit()
        return None
    if host.state == WatchHostState.OUT_OF_SCOPE.value:
        set_state(host, WatchHostState.NEW.value, "back in scope")
    if created and watch_sync.known_host(session, watch.project_id, name):
        set_state(host, WatchHostState.KNOWN.value, "in the inventory")
        session.commit()
        return None
    session.commit()
    return program, target, host


def _resolver_down(session, pending) -> None:
    """Leave the ledger untouched and retry soon; the resolver, not DNS, failed."""
    retry = utc_now() + timedelta(minutes=10)
    for watch, _program, host in pending:
        host.next_check_at = retry
        watch.last_error = (
            "DNS resolution is unavailable. Check that dnsx is installed in the worker."
        )
    session.commit()


@shared_task(name="app.tasks.watch.certificate", max_retries=0)
def certificate(cert: dict) -> dict:
    names = _clean_names(cert.get("names"))
    if not names:
        return {"names": 0}
    handled: dict[str, str] = {}
    pending: list[tuple[ProgramWatch, BountyProgram, WatchHost]] = []
    with get_sync_session() as session:
        watches = watch_sync.active_watches(session)
        if not watches:
            return {"names": len(names), "watches": 0}
        for name in names:
            for watch, item in watch_sync.match(name, watches):
                try:
                    prepared = _prepare(session, watch, item, name, cert)
                except Exception as exc:
                    session.rollback()
                    logger.warning("watch sighting failed", host=name, error=str(exc))
                    handled[f"{watch.id}:{name}"] = "error"
                    continue
                if prepared is None:
                    continue
                program, _target, host = prepared
                pending.append((watch, program, host))
        resolutions = resolve_many(sorted({h.name for _, _, h in pending}))
        if resolutions is None:
            _resolver_down(session, pending)
            return {"names": len(names), "handled": handled, "resolver": "down"}
        for watch, program, host in pending:
            try:
                state = _advance(
                    session,
                    watch,
                    program,
                    host,
                    resolutions.get(host.name, _UNRESOLVED),
                )
            except Exception as exc:
                session.rollback()
                logger.warning("watch host failed", host=host.name, error=str(exc))
                state = "error"
            handled[f"{watch.id}:{host.name}"] = state
    return {"names": len(names), "handled": handled}


@shared_task(name="app.tasks.watch.settle", max_retries=0)
def settle(scan_id: str) -> dict:
    with get_sync_session() as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return {"skipped": "scan missing"}
        state = watch_sync.settle_probe(session, scan)
    return {"scan": scan_id, "state": state}


@shared_task(name="app.tasks.watch.recheck", max_retries=0)
def recheck(limit: int = RECHECK_BATCH) -> dict:
    """Retry names without an answer; settle probes finalize did not report."""
    now = utc_now()
    advanced = 0
    settled = 0
    with get_sync_session() as session:
        active = {w.id: w for w in watch_sync.active_watches(session)}
        if not active:
            return {"advanced": 0, "settled": 0}
        due = (
            session.execute(
                select(WatchHost)
                .where(
                    WatchHost.watch_id.in_(list(active)),
                    WatchHost.state.in_(
                        (WatchHostState.NEW.value, WatchHostState.UNRESOLVED.value)
                    ),
                    WatchHost.next_check_at.isnot(None),
                    WatchHost.next_check_at <= now,
                )
                .order_by(WatchHost.next_check_at)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        resolutions = resolve_many(sorted({h.name for h in due}))
        if resolutions is None:
            _resolver_down(
                session,
                [(active[h.watch_id], None, h) for h in due if h.watch_id in active],
            )
            return {"advanced": 0, "settled": 0, "resolver": "down"}
        for host in due:
            watch = active.get(host.watch_id)
            program = session.get(BountyProgram, watch.program_id) if watch else None
            if watch is None or program is None:
                continue
            try:
                _advance(
                    session,
                    watch,
                    program,
                    host,
                    resolutions.get(host.name, _UNRESOLVED),
                )
                advanced += 1
            except Exception as exc:
                session.rollback()
                logger.warning("watch recheck failed", host=host.name, error=str(exc))

        stuck = session.execute(
            select(WatchHost, Scan)
            .join(Scan, Scan.id == WatchHost.scan_id)
            .where(
                WatchHost.watch_id.in_(list(active)),
                WatchHost.state == WatchHostState.PROBING.value,
                WatchHost.probed_at.is_(None),
                Scan.status.in_(SCAN_TERMINAL_STATUSES),
            )
            .limit(limit)
        ).all()
        for _host, scan in stuck:
            try:
                watch_sync.settle_probe(session, scan)
                settled += 1
            except Exception as exc:
                session.rollback()
                logger.warning("watch settle failed", scan=str(scan.id), error=str(exc))
        orphans = (
            session.execute(
                select(WatchHost)
                .outerjoin(Scan, Scan.id == WatchHost.scan_id)
                .where(
                    WatchHost.watch_id.in_(list(active)),
                    WatchHost.state == WatchHostState.PROBING.value,
                    WatchHost.probed_at.is_(None),
                    Scan.id.is_(None),
                )
                .limit(limit)
            )
            .scalars()
            .all()
        )
        for host in orphans:
            set_state(host, WatchHostState.QUIET.value, "probe removed")
            host.probed_at = now
        if orphans:
            session.commit()
    return {"advanced": advanced, "settled": settled}


@shared_task(name="app.tasks.watch.reconcile", max_retries=0)
def reconcile(program_id: str | None = None) -> dict:
    """Targets, exclusions and watch items follow the program scope."""
    out: dict[str, dict] = {}
    with get_sync_session() as session:
        pid = uuid.UUID(program_id) if program_id else None
        for watch in watch_sync.active_watches(session, pid):
            if not watch.follow_scope:
                continue
            try:
                out[str(watch.id)] = watch_sync.reconcile(session, watch)
            except Exception as exc:
                session.rollback()
                logger.warning(
                    "watch reconcile failed", watch=str(watch.id), error=str(exc)
                )
                out[str(watch.id)] = {"error": str(exc)[:200]}
    return out
