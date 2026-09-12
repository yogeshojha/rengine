"""Nightly exploitation-intelligence refresh, and on-demand provider enrichment."""

from celery import shared_task
from sqlalchemy import text

from app.config import settings
from app.database import get_sync_session
from shared.definitions.notifications import IntelShift, intel_changed
from shared.logging import get_logger
from shared.services.exploitation import evaluate_all, evaluate_scan
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.software_match import rematch_latest
from shared.services.threat_intel import (
    apply_intel,
    auto_sync_enabled,
    feeds_ready,
    sync_feeds,
)
from shared.services.vulnx import enrich_scan
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


ALERT_KINDS = ("kev", "ransom_path", "fresh_exploit", "weaponised")
ALERT_LIMIT = 25

_NEW_SIGNALS_SQL = """
SELECT s.kind, v.template_name, v.scan_id, v.project_id,
       coalesce((v.cve_ids::jsonb ->> 0), '') AS cve, t.target_value
FROM intel_signals s
JOIN vulnerabilities v ON v.id = s.vulnerability_id
JOIN targets t ON t.id = v.target_id
WHERE s.kind = ANY(:kinds) AND s.created_at >= :since
ORDER BY array_position(:kinds, s.kind), v.exploit_score DESC
LIMIT :limit
"""


def _notify_changes(session, since) -> int:
    """Delta-only: only signals this refresh is the first to record reach a channel."""
    rows = session.execute(
        text(_NEW_SIGNALS_SQL),
        {"kinds": list(ALERT_KINDS), "since": since, "limit": ALERT_LIMIT},
    ).all()
    if not rows:
        return 0
    payload = intel_changed(
        [
            IntelShift(
                cve=r.cve or "",
                target=r.target_value or "",
                finding=r.template_name,
                kind=r.kind,
                scan_id=str(r.scan_id),
            )
            for r in rows
        ]
    )
    if payload is None:
        return 0
    try:
        SyncNotificationPublisher(settings.redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=rows[0].project_id,
        )
    except Exception:
        logger.warning("threat intel notification failed", exc_info=True)
        return 0
    return len(rows)


@shared_task(name="app.tasks.threat_intel.refresh")
def refresh(feeds: list[str] | None = None, force: bool = False) -> dict:
    """Download the feeds, re-score every finding, then re-rank."""
    started = utc_now()
    with get_sync_session() as session:
        if not force and not auto_sync_enabled(session):
            logger.info("automatic feed download is off, skipping")
            return {"skipped": "auto_sync_off"}
        counts = sync_feeds(session, feeds)
        applied = apply_intel(session)
        ranked = evaluate_all(session)
        inferred = rematch_latest(session)
        alerted = _notify_changes(session, started)
    logger.info("threat intel refreshed", **counts, **applied, alerted=alerted)
    return {
        "feeds": counts,
        "applied": applied,
        "ranked": ranked,
        "inferred": inferred,
        "alerted": alerted,
    }


@shared_task(name="app.tasks.threat_intel.apply_scan")
def apply_scan(scan_id: str) -> dict:
    """Score and rank one scan's findings from the feeds we already hold."""
    with get_sync_session() as session:
        if not feeds_ready(session):
            logger.info("threat feeds empty, skipping scan intel", scan_id=scan_id)
            return {"skipped": True}
        applied = apply_intel(session, scan_id=scan_id)
        ranked = evaluate_scan(session, scan_id)
    return {"applied": applied, "ranked": ranked}


@shared_task(name="app.tasks.threat_intel.enrich")
def enrich(scan_id: str, limit: int = 200) -> dict:
    """Fill the provider cache for one scan's CVEs, then re-rank on the richer data."""
    with get_sync_session() as session:
        result = enrich_scan(session, scan_id, limit=limit)
        ranked = evaluate_scan(session, scan_id) if result["cached"] else {}
    logger.info("vulnx enrichment finished", scan_id=scan_id, **result)
    return {"enrich": result, "ranked": ranked}
