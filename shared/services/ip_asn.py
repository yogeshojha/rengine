"""IP -> ASN / country ranges from ip-location-db (PDDL, no key, no attribution)."""

from __future__ import annotations

import shutil
import tempfile
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select
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
    return bool(
        session.scalar(select(func.count()).select_from(IpAsnRange).limit(1))
    ) and bool(
        session.scalar(select(func.count()).select_from(IpCountryRange).limit(1))
    )


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
