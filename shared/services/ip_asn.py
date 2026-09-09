"""IP -> ASN / country ranges from ip-location-db (PDDL, no key, no attribution)."""

from __future__ import annotations

import shutil
import tempfile
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.logging import get_logger
from shared.models.ip_asn_range import IpAsnRange, IpCountryRange

logger = get_logger(__name__)

BASE_URL = "https://github.com/sapics/ip-location-db/releases/download/latest"
DOWNLOAD_TIMEOUT = 180
MAX_FEED_BYTES = 256 * 1024 * 1024


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


# the one definition of an address lookup: a LATERAL per range table, with the upper-bound
# test on the JOIN rather than inside the subquery (inside, a gap address scans backwards
# over the whole table). Postgres sorts every IPv4 inet below every IPv6 one, so one index
# on start_ip serves both families.
_ENRICH_SQL = """
UPDATE ip_addresses a SET
    asn     = coalesce(r.asn, a.asn),
    asn_org = coalesce(r.as_name, a.asn_org),
    country = coalesce(c.country, a.country)
FROM ip_addresses base
LEFT JOIN LATERAL (
    SELECT asn, as_name, end_ip FROM ip_asn_ranges
    WHERE start_ip <= base.ip::inet ORDER BY start_ip DESC LIMIT 1
) r ON r.end_ip >= base.ip::inet
LEFT JOIN LATERAL (
    SELECT country, end_ip FROM ip_country_ranges
    WHERE start_ip <= base.ip::inet ORDER BY start_ip DESC LIMIT 1
) c ON c.end_ip >= base.ip::inet
WHERE a.id = base.id AND base.scan_id = :sid{scope}{only}
"""
# a row the feeds could not place is retried, not skipped, so a later feed load fills it
_ONLY_MISSING = " AND (base.asn IS NULL OR base.country IS NULL)"
_SCOPED = " AND base.ip = ANY(:ips)"


def enrich_addresses(
    session: Session,
    *,
    scan_id,
    ips: list[str] | None = None,
    only_missing: bool = True,
) -> int:
    """Fill ASN, operator and country from the local range tables. Offline, keyless, idempotent.

    `ips` bounds the update to the addresses a caller just wrote, so a write path never takes
    row locks across the whole scan. Returns rows touched, and 0 when the feeds have never
    been loaded — a box with no egress keeps writing addresses, it just cannot name them yet.
    """
    if ips is not None and not ips:
        return 0
    if not ranges_ready(session):
        return 0
    sql = _ENRICH_SQL.format(
        scope=_SCOPED if ips is not None else "",
        only=_ONLY_MISSING if only_missing else "",
    )
    statement = text(sql).bindparams(sid=scan_id)
    if ips is not None:
        statement = statement.bindparams(ips=list(ips))
    return int(session.execute(statement).rowcount or 0)


@contextmanager
def _downloaded(feed: Feed) -> Iterator[list[Path]]:
    workdir = Path(tempfile.mkdtemp(prefix="ip_asn_"))
    try:
        paths = []
        for name in feed.files:
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
    """Refresh both range tables. A feed that fails to download is left untouched."""
    counts: dict[str, int] = {}
    for feed in FEEDS:
        try:
            with _downloaded(feed) as paths:
                counts[feed.table] = _load(session, feed, paths)
            session.commit()
        except Exception:
            session.rollback()
            logger.warning(
                "ip range feed refresh failed", table=feed.table, exc_info=True
            )
    return counts


# the same LATERAL shape as the bulk enrich, for one address, on either session flavour
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
