"""EPSS + CISA KEV: download, store, and re-rank every finding without rescanning."""

from __future__ import annotations

import gzip
import json
import shutil
import tempfile
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from shared.definitions.threat_intel import (
    FEEDS_BY_KIND,
    STALE_AFTER_HOURS,
    FeedKind,
    FeedStatus,
)
from shared.logging import get_logger
from shared.models.threat_intel import EpssScore, KevEntry, ThreatFeed
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

DOWNLOAD_TIMEOUT = 180
MAX_FEED_BYTES = 128 * 1024 * 1024
USER_AGENT = "reNgine"


@contextmanager
def _download(url: str, name: str) -> Iterator[tuple[Path, int]]:
    workdir = Path(tempfile.mkdtemp(prefix="threat_intel_"))
    target = workdir / name
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
        with (
            urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response,  # noqa: S310
            target.open("wb") as handle,
        ):
            copied = 0
            while chunk := response.read(1 << 20):
                copied += len(chunk)
                if copied > MAX_FEED_BYTES:
                    msg = f"{name} exceeded {MAX_FEED_BYTES} bytes"
                    raise ValueError(msg)
                handle.write(chunk)
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


def _mark(
    session: Session,
    kind: str,
    *,
    status: str,
    rows: int = 0,
    version: str | None = None,
    size: int = 0,
    duration_ms: int = 0,
    error: str | None = None,
    synced: bool = False,
) -> None:
    now = utc_now()
    values = {
        "kind": kind,
        "status": status,
        "rows": rows,
        "version": version,
        "bytes": size,
        "duration_ms": duration_ms,
        "error": error,
        "last_attempt_at": now,
        "updated_at": now,
    }
    if synced:
        values["last_synced_at"] = now
    update = {k: v for k, v in values.items() if k != "kind"}
    if not synced:
        update.pop("last_synced_at", None)
    session.execute(
        pg_insert(ThreatFeed)
        .values(**values)
        .on_conflict_do_update(index_elements=[ThreatFeed.kind], set_=update)
    )


def sync_feed(session: Session, kind: str) -> int:
    """Refresh one feed."""
    spec = FEEDS_BY_KIND[kind]
    started = time.monotonic()
    _mark(session, kind, status=FeedStatus.SYNCING.value)
    session.commit()
    try:
        with _download(spec.url, f"{kind}.data") as (path, size):
            rows, version = _LOADERS[kind](session, path)
        elapsed = int((time.monotonic() - started) * 1000)
        _mark(
            session,
            kind,
            status=FeedStatus.READY.value,
            rows=rows,
            version=version,
            size=size,
            duration_ms=elapsed,
            synced=True,
        )
        session.commit()
        logger.info("threat feed refreshed", feed=kind, rows=rows, version=version)
        return rows
    except Exception as exc:
        session.rollback()
        elapsed = int((time.monotonic() - started) * 1000)
        _mark(
            session,
            kind,
            status=FeedStatus.FAILED.value,
            duration_ms=elapsed,
            error=str(exc)[:500],
        )
        session.commit()
        logger.warning("threat feed refresh failed", feed=kind, exc_info=True)
        return 0


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


def set_auto_sync(session: Session, enabled: bool) -> bool:
    session.execute(
        text(
            "UPDATE instance_settings SET threat_intel_auto_sync = :v, updated_at = now()"
        ),
        {"v": enabled},
    )
    session.commit()
    return enabled


def feeds_ready(session: Session) -> bool:
    return bool(
        session.scalar(select(func.count()).select_from(EpssScore).limit(1))
    ) and bool(session.scalar(select(func.count()).select_from(KevEntry).limit(1)))


def feed_rows(session: Session) -> dict[str, int]:
    return {
        FeedKind.EPSS.value: int(
            session.scalar(select(func.count()).select_from(EpssScore)) or 0
        ),
        FeedKind.KEV.value: int(
            session.scalar(select(func.count()).select_from(KevEntry)) or 0
        ),
    }


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


def apply_intel(session: Session, *, scan_id=None, project_id=None) -> dict[str, int]:
    """Re-score findings from the feeds."""
    scope = ""
    params: dict = {"now": utc_now()}
    if scan_id is not None:
        scope = "WHERE v.scan_id = :scan_id"
        params["scan_id"] = scan_id
    elif project_id is not None:
        scope = "WHERE v.project_id = :project_id"
        params["project_id"] = project_id

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


def lookup(session: Session, cves: list[str]) -> dict[str, dict]:
    """Local feed data for a set of CVEs."""
    keys = [c.strip().upper() for c in cves if c and c.strip()]
    if not keys:
        return {}
    out: dict[str, dict] = {k: {"cve": k} for k in keys}
    for row in session.execute(
        select(EpssScore).where(EpssScore.cve.in_(keys))
    ).scalars():
        out[row.cve]["epss_score"] = row.score
        out[row.cve]["epss_percentile"] = row.percentile
    for row in session.execute(
        select(KevEntry).where(KevEntry.cve.in_(keys))
    ).scalars():
        out[row.cve]["kev"] = row
    return out
