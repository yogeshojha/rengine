"""Certificates re-checked between scans, on their own freshness clock."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import case, select, text, update
from sqlalchemy.orm import Session

from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.scan_context import ScanContext
from shared.models.subdomain import Subdomain
from shared.services.asset_query.lead_cache import bump_sync
from shared.services.proxy_resolve import is_socks5, scan_proxy_url
from shared.services.scan_scope import census_only
from shared.utils.datetime import utc_now
from tools.tlsx.client import TlsxClient, TlsxError
from tools.tlsx.parser import parse_certificate

logger = get_logger(__name__)

STALE_AFTER = timedelta(hours=12)
URGENT_WITHIN = timedelta(days=30)
URGENT_AFTER = timedelta(hours=4)
MAX_PER_RUN = 500
PER_HOST_SECONDS = 5
CONCURRENCY = 50
MIN_RUN_SECONDS = 45
MAX_RUN_SECONDS = 600


def budget(hosts: int) -> int:
    rounds = max(1, -(-hosts // CONCURRENCY))
    return max(MIN_RUN_SECONDS, min(MAX_RUN_SECONDS, rounds * PER_HOST_SECONDS * 4))


@dataclass
class Freshness:
    picked: int = 0
    answered: int = 0
    renewed: int = 0
    changed: int = 0
    cut_short: bool = False
    skipped: str | None = None


def enabled(session: Session) -> bool:
    row = session.execute(
        text("SELECT cert_recheck_enabled FROM instance_settings LIMIT 1")
    ).first()
    return bool(row and row[0])


def due(session: Session, *, limit: int = MAX_PER_RUN) -> list[Subdomain]:
    """Hosts due a re-check, nearest expiry first, newest settled census run only."""
    now = utc_now()
    newest = Subdomain.scan_id == (
        select(Scan.id)
        .where(
            Scan.target_id == Subdomain.target_id,
            census_only(),
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
        )
        .order_by(Scan.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    urgent = Subdomain.tls_not_after <= now + URGENT_WITHIN
    cutoff = case((urgent, now - URGENT_AFTER), else_=now - STALE_AFTER)
    return list(
        session.scalars(
            select(Subdomain)
            .where(
                Subdomain.tls_not_after.isnot(None),
                Subdomain.is_excluded.is_(False),
                newest,
                (Subdomain.tls_checked_at.is_(None))
                | (Subdomain.tls_checked_at <= cutoff),
            )
            .order_by(urgent.desc(), Subdomain.tls_not_after.asc())
            .limit(limit)
        )
    )


def refresh(session: Session, *, limit: int = MAX_PER_RUN) -> Freshness:
    if not enabled(session):
        return Freshness(skipped="Certificate re-checking is off.")

    rows = due(session, limit=limit)
    if not rows:
        return Freshness()

    probed: list[Subdomain] = []
    refused: list[Subdomain] = []
    seen: dict[str, dict] = {}
    timed_out = False
    error: str | None = None
    for proxy_url, group in _by_proxy(session, rows).items():
        if proxy_url and not is_socks5(proxy_url):
            refused.extend(group)
            continue
        if error:
            continue
        try:
            client = TlsxClient(
                timeout=PER_HOST_SECONDS,
                concurrency=CONCURRENCY,
                extra_args=["-proxy", proxy_url] if proxy_url else None,
            )
        except TlsxError as e:
            error = str(e)
            continue
        probed.extend(group)
        hosts = sorted({row.name for row in group})
        result = client.certificates(hosts, timeout=budget(len(hosts)))
        timed_out = timed_out or bool(result.timed_out)
        for record in _records(result):
            parsed = parse_certificate(record)
            if parsed is not None:
                seen.setdefault(parsed["host"], parsed)

    state = _apply(session, probed, seen, refused)
    state.picked = len(rows)
    state.cut_short = timed_out
    if error:
        state.skipped = error
    elif refused:
        state.skipped = (
            f"tlsx takes a socks5 proxy. {len(refused)} hosts not re-checked."
        )
    return state


def _by_proxy(
    session: Session, rows: list[Subdomain]
) -> dict[str | None, list[Subdomain]]:
    contexts = dict(
        session.execute(
            select(Scan.id, Scan.context_id).where(
                Scan.id.in_({row.scan_id for row in rows})
            )
        ).all()
    )
    urls: dict = {}
    groups: dict[str | None, list[Subdomain]] = defaultdict(list)
    for row in rows:
        context_id = contexts.get(row.scan_id)
        if context_id not in urls:
            context = session.get(ScanContext, context_id) if context_id else None
            urls[context_id] = scan_proxy_url(session, context)
        groups[urls[context_id]].append(row)
    return groups


def _records(result) -> list[dict]:
    if result.json_records:
        return result.json_records
    out = []
    for line in result.output_lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _apply(
    session: Session,
    rows: list[Subdomain],
    seen: dict[str, dict],
    refused: Sequence[Subdomain] = (),
) -> Freshness:
    now = utc_now()
    state = Freshness(picked=len(rows), answered=len(seen))
    payload: list[dict] = [{"id": row.id, "tls_checked_at": now} for row in refused]
    touched = set()
    for row in rows:
        fresh = seen.get(row.name)
        if fresh is None:
            payload.append({"id": row.id, "tls_checked_at": now})
            continue
        moved = fresh["not_after"] != row.tls_not_after
        if moved:
            state.changed += 1
            if row.tls_not_after and fresh["not_after"] > row.tls_not_after:
                state.renewed += 1
        if (
            moved
            or fresh["expired"] != row.tls_expired
            or fresh["self_signed"] != row.tls_self_signed
        ):
            touched.add(row.target_id)
        payload.append(
            {
                "id": row.id,
                "tls_checked_at": now,
                "tls_not_after": fresh["not_after"],
                "tls_expired": fresh["expired"],
                "tls_self_signed": fresh["self_signed"],
            }
        )

    if payload:
        session.execute(update(Subdomain), payload)
        session.commit()
    if touched:
        bump_sync(touched)
    logger.info(
        "certificate re-check",
        picked=state.picked,
        answered=state.answered,
        moved=state.changed,
        renewed=state.renewed,
    )
    return state
