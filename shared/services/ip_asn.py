"""IP -> ASN / country ranges from ip-location-db (PDDL, no key, no attribution)."""

from __future__ import annotations

import shutil
import tempfile
import time
import urllib.request
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models.ip_asn_range import IpAsnRange, IpCountryRange
from shared.services.locks import IP_RANGES, sync_lock

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
    """Existence, not a count — this is checked on the write path, and the tables are ~1.1M rows."""
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
_SCOPED = " AND base.ip = ANY(:ips)"
_PENDING_SQL = """
SELECT id, ip FROM ip_addresses
WHERE asn IS NULL OR country IS NULL
ORDER BY discovered_at DESC LIMIT :lim
"""
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
    only_missing: bool = True,
) -> int:
    """Fill ASN, operator and country from the local range tables."""
    if ips is not None and not ips:
        return 0
    if not ranges_ready(session):
        return 0
    where = " AND base.scan_id = :sid"
    where += _SCOPED if ips is not None else ""
    where += _ONLY_MISSING if only_missing else ""
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


def backfill_addresses(session: Session, limit: int = BACKFILL_LIMIT) -> Backfilled:
    """Fill addresses left blank by a scan that ran before the ranges were loaded."""
    if not ranges_ready(session):
        return Backfilled()
    sql = _ENRICH_SQL.format(source=f"({_PENDING_SQL})", filter="")
    sql += " RETURNING a.scan_id"
    filled = session.execute(text(sql).bindparams(lim=limit)).fetchall()
    scans = sorted({row[0] for row in filled})
    hosts = fold_onto_hosts(session, scans)
    session.commit()
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
            request = urllib.request.Request(  # noqa: S310
                f"{BASE_URL}/{name}", headers={"User-Agent": "reNgine"}
            )
            with (
                urllib.request.urlopen(  # noqa: S310
                    request, timeout=DOWNLOAD_TIMEOUT
                ) as response,
                target.open("wb") as handle,
            ):
                copied = 0
                while chunk := response.read(1 << 20):
                    copied += len(chunk)
                    if copied > MAX_FEED_BYTES:
                        msg = f"{name} exceeded {MAX_FEED_BYTES} bytes"
                        raise ValueError(msg)
                    handle.write(chunk)
                    _check_deadline(deadline, name)
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
    with sync_lock(session, IP_RANGES) as held:
        if not held:
            logger.info("ip range refresh already running, skipped")
            return counts
        deadline = time.monotonic() + SYNC_BUDGET
        for feed in FEEDS:
            try:
                with _downloaded(feed, deadline) as paths:
                    counts[feed.table] = _load(session, feed, paths)
                session.commit()
            except Exception:
                session.rollback()
                logger.warning(
                    "ip range feed refresh failed", table=feed.table, exc_info=True
                )
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
