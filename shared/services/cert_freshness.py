"""Certificates re-checked between scans, on their own freshness clock."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import case, select, text, update
from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.asset_query.lead_cache import bump_sync
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
    """Hosts due a re-check, nearest expiry first, newest scan of each target only."""
    now = utc_now()
    newest = text(
        "subdomains.scan_id = ("
        " SELECT s.id FROM scans s"
        " WHERE s.target_id = subdomains.target_id"
        " ORDER BY s.created_at DESC LIMIT 1)"
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
        return Freshness(skipped="certificate re-checking is off for this instance")

    rows = due(session, limit=limit)
    if not rows:
        return Freshness()

    hosts = sorted({row.name for row in rows})
    try:
        client = TlsxClient(timeout=PER_HOST_SECONDS, concurrency=CONCURRENCY)
    except TlsxError as e:
        return Freshness(picked=len(rows), skipped=str(e))

    result = client.certificates(hosts, timeout=budget(len(hosts)))
    seen: dict[str, dict] = {}
    for record in _records(result):
        parsed = parse_certificate(record)
        if parsed is not None:
            seen.setdefault(parsed["host"], parsed)

    state = _apply(session, rows, seen)
    state.cut_short = bool(result.timed_out)
    return state


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


def _apply(session: Session, rows: list[Subdomain], seen: dict[str, dict]) -> Freshness:
    now = utc_now()
    state = Freshness(picked=len(rows), answered=len(seen))
    payload: list[dict] = []
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
        bump_sync({row.target_id for row in rows})
    logger.info(
        "certificate re-check",
        picked=state.picked,
        answered=state.answered,
        moved=state.changed,
        renewed=state.renewed,
    )
    return state
