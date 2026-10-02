"""EPSS and CISA KEV feeds and the finding re-rank."""

from __future__ import annotations

import gzip
import json
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from shared.definitions.threat_intel import (
    FEEDS,
    FEEDS_BY_KIND,
    STALE_AFTER_HOURS,
    FeedKind,
    FeedStatus,
)
from shared.http import download
from shared.logging import get_logger
from shared.models.threat_intel import EpssScore, KevEntry, ThreatFeed
from shared.services import feed_ledger, locks, nvd_corpus
from shared.services.locks import sync_lock
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

DOWNLOAD_TIMEOUT = 180
MAX_FEED_BYTES = 128 * 1024 * 1024


@contextmanager
def _download(url: str, name: str) -> Iterator[tuple[Path, int]]:
    workdir = Path(tempfile.mkdtemp(prefix="threat_intel_"))
    target = workdir / name
    try:
        copied = download(
            url, target, timeout=DOWNLOAD_TIMEOUT, max_bytes=MAX_FEED_BYTES
        )
        yield target, copied
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _load_epss(session: Session, path: Path) -> tuple[int, str | None]:
    """The published CSV leads with a '#model_version' comment."""
    clean = path.with_suffix(".clean.csv")
    version: str | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as src:
        first = src.readline()
        if first.startswith("#"):
            version = first.lstrip("#").strip()[:100]
        else:
            src.seek(0)
        with clean.open("w", encoding="utf-8") as dst:
            shutil.copyfileobj(src, dst)

    raw = session.connection().connection
    cursor = raw.cursor()
    cursor.execute("TRUNCATE TABLE epss_scores")
    with clean.open("r", encoding="utf-8") as handle:
        cursor.copy_expert(
            "COPY epss_scores (cve, score, percentile) FROM STDIN WITH (FORMAT csv, HEADER true)",
            handle,
        )
    cursor.execute("SELECT count(*) FROM epss_scores")
    return int(cursor.fetchone()[0]), version


def _as_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _load_kev(session: Session, path: Path) -> tuple[int, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    entries = payload.get("vulnerabilities") or []
    version = str(payload.get("catalogVersion") or "")[:100] or None

    session.execute(text("TRUNCATE TABLE kev_entries"))
    rows = []
    for item in entries:
        cve = (item.get("cveID") or "").strip().upper()
        if not cve:
            continue
        rows.append(
            {
                "cve": cve[:30],
                "vendor": strip_control(item.get("vendorProject") or "")[:200] or None,
                "product": strip_control(item.get("product") or "")[:200] or None,
                "name": strip_control(item.get("vulnerabilityName") or "")[:500]
                or None,
                "short_description": strip_control(item.get("shortDescription") or "")
                or None,
                "required_action": strip_control(item.get("requiredAction") or "")
                or None,
                "notes": strip_control(item.get("notes") or "") or None,
                "cwes": [str(c)[:40] for c in (item.get("cwes") or [])][:20],
                "known_ransomware": (
                    str(item.get("knownRansomwareCampaignUse") or "").lower() == "known"
                ),
                "date_added": _as_date(item.get("dateAdded")),
                "due_date": _as_date(item.get("dueDate")),
            }
        )
    if rows:
        session.execute(KevEntry.__table__.insert(), rows)
    return len(rows), version


_LOADERS = {FeedKind.EPSS.value: _load_epss, FeedKind.KEV.value: _load_kev}


def _sync_single(session: Session, kind: str, spec) -> tuple[int, str | None, int]:
    with _download(spec.url, f"{kind}.data") as (path, size):
        rows, version = _LOADERS[kind](session, path)
    return rows, version, size


def sync_feed(session: Session, kind: str) -> int:
    """Refresh one feed. One loader per feed across the instance."""
    spec = FEEDS_BY_KIND[kind]
    with sync_lock(session, locks.dataset(kind)) as held:
        if not held:
            logger.info("threat feed refresh already running", feed=kind)
            return 0
        try:
            with feed_ledger.refreshing(session, kind) as refresh:
                if kind == FeedKind.NVD.value:
                    stamp = session.execute(
                        select(ThreatFeed.version).where(ThreatFeed.kind == kind)
                    ).scalar()
                    refresh.rows, refresh.version, refresh.size = nvd_corpus.load(
                        session, current_version=stamp
                    )
                else:
                    refresh.rows, refresh.version, refresh.size = _sync_single(
                        session, kind, spec
                    )
        except Exception:
            logger.warning("threat feed refresh failed", feed=kind, exc_info=True)
            return 0
    logger.info(
        "threat feed refreshed", feed=kind, rows=refresh.rows, version=refresh.version
    )
    return refresh.rows


def sync_feeds(session: Session, kinds: list[str] | None = None) -> dict[str, int]:
    wanted = kinds or list(FEEDS_BY_KIND)
    return {kind: sync_feed(session, kind) for kind in wanted if kind in FEEDS_BY_KIND}


def auto_sync_enabled(session: Session) -> bool:
    """The nightly download is opt-out."""
    try:
        value = session.execute(
            text("SELECT threat_intel_auto_sync FROM instance_settings LIMIT 1")
        ).scalar()
    except Exception:
        logger.debug("auto-sync setting unreadable, assuming on", exc_info=True)
        return True
    return True if value is None else bool(value)


def feeds_ready(session: Session) -> bool:
    return bool(
        session.scalar(select(func.count()).select_from(EpssScore).limit(1))
    ) and bool(session.scalar(select(func.count()).select_from(KevEntry).limit(1)))


def missing_feeds(session: Session) -> list[str]:
    """Feeds whose table holds no rows."""
    return [
        spec.kind
        for spec in FEEDS
        if not session.execute(
            text(f"SELECT EXISTS (SELECT 1 FROM {spec.rows_table})")  # noqa: S608
        ).scalar()
    ]


def feed_status(feed: ThreatFeed | None, rows: int) -> str:
    if feed is None or rows == 0:
        return FeedStatus.EMPTY.value if feed is None else feed.status
    if feed.status == FeedStatus.SYNCING.value:
        return FeedStatus.SYNCING.value
    if feed.status == FeedStatus.FAILED.value:
        return FeedStatus.FAILED.value
    if feed.last_synced_at is None:
        return FeedStatus.EMPTY.value
    age = (utc_now() - feed.last_synced_at).total_seconds() / 3600
    return FeedStatus.STALE.value if age > STALE_AFTER_HOURS else FeedStatus.READY.value


def feed_age_hours(feed: ThreatFeed | None) -> float | None:
    if feed is None or feed.last_synced_at is None:
        return None
    return round((utc_now() - feed.last_synced_at).total_seconds() / 3600, 1)


_JOINED_SQL = """
WITH exploded AS (
    SELECT v.id, upper(btrim(c.cve)) AS cve
    FROM vulnerabilities v
    CROSS JOIN LATERAL jsonb_array_elements_text(v.cve_ids::jsonb) AS c(cve)
    {scope}
)
SELECT x.id,
       max(e.score)                                AS epss,
       max(e.percentile)                           AS pct,
       bool_or(k.cve IS NOT NULL)                  AS kev,
       bool_or(coalesce(k.known_ransomware,false)) AS ransomware,
       min(k.due_date)                             AS due_date
FROM exploded x
LEFT JOIN epss_scores e ON e.cve = x.cve
LEFT JOIN kev_entries k ON k.cve = x.cve
GROUP BY x.id
"""


def apply_intel(session: Session, *, scan_id=None) -> dict[str, int]:
    """Re-score findings from the feeds."""
    scope = ""
    params: dict = {"now": utc_now()}
    if scan_id is not None:
        scope = "WHERE v.scan_id = :scan_id"
        params["scan_id"] = scan_id

    joined = _JOINED_SQL.format(scope=scope)
    session.execute(
        text(f"CREATE TEMP TABLE _intel ON COMMIT DROP AS {joined}"), params
    )
    session.execute(text("CREATE INDEX ON _intel (id)"))

    moved = session.execute(
        text("""
        SELECT count(*) FILTER (WHERE j.kev AND NOT v.is_kev)                       AS became_kev,
               count(*) FILTER (WHERE v.epss_score IS DISTINCT FROM j.epss)         AS epss_moved,
               count(*)                                                            AS scanned
        FROM _intel j JOIN vulnerabilities v ON v.id = j.id
        """)
    ).one()

    changed = session.execute(
        text("""
        UPDATE vulnerabilities v
        SET epss_score = j.epss,
            epss_percentile = j.pct,
            is_kev = j.kev,
            kev_ransomware = j.ransomware,
            kev_due_date = j.due_date,
            intel_at = :now
        FROM _intel j
        WHERE v.id = j.id
          AND (v.epss_score      IS DISTINCT FROM j.epss
            OR v.epss_percentile IS DISTINCT FROM j.pct
            OR v.is_kev          IS DISTINCT FROM j.kev
            OR v.kev_ransomware  IS DISTINCT FROM j.ransomware
            OR v.kev_due_date    IS DISTINCT FROM j.due_date)
        """),
        {"now": params["now"]},
    ).rowcount
    session.commit()
    return {
        "scanned": int(moved.scanned or 0),
        "changed": int(changed or 0),
        "became_kev": int(moved.became_kev or 0),
        "epss_moved": int(moved.epss_moved or 0),
    }
