"""IP to ASN and country ranges from ip-location-db."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.definitions.datasets import DatasetKind
from shared.http import download
from shared.logging import get_logger
from shared.models.ip_asn_range import IpAsnRange, IpCountryRange
from shared.models.threat_intel import ThreatFeed
from shared.redis import sync_client
from shared.services import feed_ledger
from shared.services.locks import dataset, sync_lock

logger = get_logger(__name__)

BASE_URL = "https://github.com/sapics/ip-location-db/releases/download/latest"
DOWNLOAD_TIMEOUT = 180
SYNC_BUDGET = 900
MAX_FEED_BYTES = 256 * 1024 * 1024
BACKFILL_LIMIT = 200_000


@dataclass(frozen=True)
class Feed:
    table: str
    columns: tuple[str, ...]
    files: tuple[str, ...]


FEEDS: tuple[Feed, ...] = (
    Feed(
        table="ip_asn_ranges",
        columns=("start_ip", "end_ip", "asn", "as_name"),
        files=("origin-asn-ipv4.csv", "origin-asn-ipv6.csv"),
    ),
    Feed(
        table="ip_country_ranges",
        columns=("start_ip", "end_ip", "country"),
        files=("server-country-ipv4.csv", "server-country-ipv6.csv"),
    ),
)


def ranges_ready(session: Session) -> bool:
    """Whether both range tables hold a row."""
    return bool(
        session.scalar(select(IpAsnRange.start_ip).limit(1)) is not None
        and session.scalar(select(IpCountryRange.start_ip).limit(1)) is not None
    )


_ENRICH_SQL = """
UPDATE ip_addresses a SET
    asn     = coalesce(r.asn, a.asn),
    asn_org = coalesce(r.as_name, a.asn_org),
    country = coalesce(c.country, a.country),
    prefix  = coalesce(r.prefix, a.prefix)
FROM {source} base
LEFT JOIN LATERAL (
    SELECT asn, as_name, end_ip,
           CASE
               WHEN host(network(inet_merge(start_ip, end_ip)))::inet = start_ip
                AND host(broadcast(inet_merge(start_ip, end_ip)))::inet = end_ip
               THEN text(inet_merge(start_ip, end_ip))
           END AS prefix
    FROM ip_asn_ranges
    WHERE start_ip <= base.ip::inet ORDER BY start_ip DESC LIMIT 1
) r ON r.end_ip >= base.ip::inet
LEFT JOIN LATERAL (
    SELECT country, end_ip FROM ip_country_ranges
    WHERE start_ip <= base.ip::inet ORDER BY start_ip DESC LIMIT 1
) c ON c.end_ip >= base.ip::inet
WHERE a.id = base.id AND (r.asn IS NOT NULL OR c.country IS NOT NULL){filter}
"""
_ONLY_MISSING = " AND (base.asn IS NULL OR base.country IS NULL)"
_FILLS = (
    " AND ((a.asn IS NULL AND r.asn IS NOT NULL)"
    " OR (a.country IS NULL AND c.country IS NOT NULL))"
)
_SCOPED = " AND base.ip = ANY(:ips)"
_PENDING_SQL = """
SELECT id, discovered_at FROM ip_addresses
WHERE (asn IS NULL OR country IS NULL){after}
ORDER BY discovered_at DESC, id DESC LIMIT :lim
"""
_AFTER = " AND (discovered_at, id) < (CAST(:at AS timestamptz), CAST(:id AS uuid))"
_CHUNK_SQL = "(SELECT id, ip FROM ip_addresses WHERE id = ANY(CAST(:ids AS uuid[])))"
SWEEP_KEY = "ip-ranges:backfill"
SWEEP_DONE = "done"
_FOLD_ASSETS_SQL = """
UPDATE http_assets h SET asn = a.asn, asn_org = a.asn_org
FROM ip_addresses a
WHERE a.scan_id = ANY(CAST(:sids AS uuid[]))
  AND h.scan_id = a.scan_id AND h.ip = a.ip
  AND a.asn IS NOT NULL AND h.asn IS NULL
"""
_FOLD_HOSTS_SQL = """
UPDATE subdomains s SET asn = a.asn, asn_org = a.asn_org
FROM ip_addresses a
WHERE a.scan_id = ANY(CAST(:sids AS uuid[]))
  AND s.scan_id = a.scan_id
  AND cast(s.resolved_ips AS jsonb) ->> 0 = a.ip
  AND a.asn IS NOT NULL AND s.asn IS NULL
"""


@dataclass(frozen=True)
class Backfilled:
    addresses: int = 0
    hosts: int = 0
    scans: tuple[UUID, ...] = field(default_factory=tuple)


def enrich_addresses(
    session: Session,
    *,
    scan_id,
    ips: list[str] | None = None,
) -> int:
    """Fill ASN, operator and country from the local range tables."""
    if ips is not None and not ips:
        return 0
    if not ranges_ready(session):
        return 0
    where = " AND base.scan_id = :sid"
    where += _SCOPED if ips is not None else ""
    where += _ONLY_MISSING
    sql = _ENRICH_SQL.format(source="ip_addresses", filter=where)
    statement = text(sql).bindparams(sid=scan_id)
    if ips is not None:
        statement = statement.bindparams(ips=list(ips))
    return int(session.execute(statement).rowcount or 0)


def fold_onto_hosts(session: Session, scan_ids: Sequence[UUID]) -> int:
    """Carry the address network onto the web assets and hosts of those scans."""
    if not scan_ids:
        return 0
    ids = [str(s) for s in scan_ids]
    return sum(
        int(session.execute(text(sql).bindparams(sids=ids)).rowcount or 0)
        for sql in (_FOLD_ASSETS_SQL, _FOLD_HOSTS_SQL)
    )


def _sweep_state(synced: str) -> list | str | None:
    try:
        raw = sync_client().get(SWEEP_KEY)
        state = json.loads(raw) if raw else None
    except Exception:
        logger.warning("ip range backfill cursor not read", exc_info=True)
        return None
    if not isinstance(state, dict) or state.get("synced") != synced:
        return None
    return state.get("cursor")


def _save_sweep(synced: str, cursor: list | str) -> None:
    try:
        sync_client().set(SWEEP_KEY, json.dumps({"synced": synced, "cursor": cursor}))
    except Exception:
        logger.warning("ip range backfill cursor not saved", exc_info=True)


def backfill_addresses(session: Session, limit: int = BACKFILL_LIMIT) -> Backfilled:
    """Try every blank address once against each range load, newest first."""
    if not ranges_ready(session):
        return Backfilled()
    stamp = session.scalar(
        select(ThreatFeed.last_synced_at).where(
            ThreatFeed.kind == DatasetKind.IP_RANGES.value
        )
    )
    synced = stamp.isoformat() if stamp else ""
    cursor = _sweep_state(synced)
    if cursor == SWEEP_DONE:
        return Backfilled()
    params: dict = {"lim": limit}
    after = ""
    if cursor:
        after = _AFTER
        params |= {"at": cursor[0], "id": cursor[1]}
    chunk = session.execute(text(_PENDING_SQL.format(after=after)), params).fetchall()
    filled = []
    if chunk:
        sql = _ENRICH_SQL.format(source=_CHUNK_SQL, filter=_FILLS)
        sql += " RETURNING a.scan_id"
        ids = [str(row.id) for row in chunk]
        filled = session.execute(text(sql).bindparams(ids=ids)).fetchall()
    scans = sorted({row[0] for row in filled})
    hosts = fold_onto_hosts(session, scans)
    session.commit()
    last = chunk[-1] if chunk else None
    _save_sweep(
        synced,
        [last.discovered_at.isoformat(), str(last.id)]
        if last is not None and len(chunk) >= limit
        else SWEEP_DONE,
    )
    return Backfilled(addresses=len(filled), hosts=hosts, scans=tuple(scans))


def _check_deadline(deadline: float, name: str) -> None:
    if time.monotonic() > deadline:
        msg = f"{name} exceeded the {SYNC_BUDGET}s range sync budget"
        raise TimeoutError(msg)


@contextmanager
def _downloaded(feed: Feed, deadline: float) -> Iterator[list[Path]]:
    workdir = Path(tempfile.mkdtemp(prefix="ip_asn_"))
    try:
        paths = []
        for name in feed.files:
            _check_deadline(deadline, name)
            target = workdir / name
            download(
                f"{BASE_URL}/{name}",
                target,
                timeout=DOWNLOAD_TIMEOUT,
                max_bytes=MAX_FEED_BYTES,
                on_chunk=lambda name=name: _check_deadline(deadline, name),
            )
            paths.append(target)
        yield paths
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _load(session: Session, feed: Feed, paths: list[Path]) -> int:
    columns = ", ".join(feed.columns)
    raw = session.connection().connection
    cursor = raw.cursor()
    cursor.execute(f"TRUNCATE TABLE {feed.table}")
    for path in paths:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            cursor.copy_expert(
                f"COPY {feed.table} ({columns}) FROM STDIN WITH (FORMAT csv)",
                handle,
            )
    cursor.execute(f"SELECT count(*) FROM {feed.table}")  # noqa: S608
    return int(cursor.fetchone()[0])


def sync_ranges(session: Session) -> dict[str, int]:
    """Refresh both range tables. One loader at a time across the instance."""
    counts: dict[str, int] = {}
    kind = DatasetKind.IP_RANGES.value
    with sync_lock(session, dataset(kind)) as held:
        if not held:
            logger.info("ip range refresh already running, skipped")
            return counts
        with feed_ledger.refreshing(session, kind) as refresh:
            deadline = time.monotonic() + SYNC_BUDGET
            failed: list[str] = []
            for feed in FEEDS:
                try:
                    with _downloaded(feed, deadline) as paths:
                        counts[feed.table] = _load(session, feed, paths)
                    session.commit()
                except Exception as exc:
                    session.rollback()
                    failed.append(f"{feed.table}: {exc}")
                    logger.warning(
                        "ip range feed refresh failed", table=feed.table, exc_info=True
                    )
            refresh.rows = counts.get(FEEDS[0].table, 0)
            refresh.error = "; ".join(failed) or None
    return counts


ADDRESS_LOOKUP_SQL = text("""
SELECT r.asn, r.as_name, c.country
FROM (SELECT CAST(:ip AS inet) AS ip) base
LEFT JOIN LATERAL (
    SELECT asn, as_name, end_ip FROM ip_asn_ranges
    WHERE start_ip <= base.ip ORDER BY start_ip DESC LIMIT 1
) r ON r.end_ip >= base.ip
LEFT JOIN LATERAL (
    SELECT country, end_ip FROM ip_country_ranges
    WHERE start_ip <= base.ip ORDER BY start_ip DESC LIMIT 1
) c ON c.end_ip >= base.ip
""")
