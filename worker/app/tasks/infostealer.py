"""Infostealer lookups for domain and URL targets."""

import time

from sqlalchemy import select

from app.celery import celery_app
from app.database import get_sync_session
from shared.definitions.infostealer import (
    LOOKUPS_OFF_REASON,
    NOT_APPLICABLE_REASON,
    REQUEST_SPACING,
)
from shared.definitions.notifications import ENRICHMENT_FAILED
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.target import Target
from shared.services import infostealer
from shared.services.activity_log import ActivityLogService
from shared.services.asset_query.lead_cache import bump_sync
from tools.hudsonrock.client import HudsonRockClient, HudsonRockError

logger = get_logger(__name__)


def _failed(activity: ActivityLogService, targets: list[Target], error: str) -> None:
    for target in targets:
        infostealer.mark(target, TaskStatus.FAILED, error)
        activity.log(
            event=ActivityEvent.TARGET_ENRICHMENT_INFOSTEALER_FAILED,
            title=f"Infostealer lookup failed · {target.target_value}",
            description=error,
            level=ActivityLevel.ERROR,
            target_id=target.id,
            project_id=target.project_id,
        )


def _resolve(
    session,
    activity: ActivityLogService,
    client: HudsonRockClient,
    domain: str,
    targets: list[Target],
) -> bool:
    try:
        report = client.search_domain(domain)
    except HudsonRockError as exc:
        logger.warning("infostealer lookup failed", domain=domain, error=str(exc))
        _failed(activity, targets, str(exc))
        session.commit()
        return False
    except Exception:
        logger.exception("infostealer lookup failed", domain=domain)
        session.rollback()
        _failed(activity, targets, ENRICHMENT_FAILED)
        session.commit()
        return False
    for target in targets:
        infostealer.store(session, target.id, report)
        infostealer.mark(target, TaskStatus.SUCCESS)
        activity.log(
            event=ActivityEvent.TARGET_ENRICHMENT_INFOSTEALER_COMPLETED,
            title=f"Infostealer lookup completed · {target.target_value}",
            level=ActivityLevel.SUCCESS,
            target_id=target.id,
            project_id=target.project_id,
        )
    session.commit()
    return True


@celery_app.task(
    name="app.tasks.infostealer.perform_infostealer_lookups",
    max_retries=0,
    soft_time_limit=900,
    time_limit=1200,
)
def perform_infostealer_lookups(target_ids: list[str]) -> dict:
    """Look up a batch of targets, one request per registrable domain."""
    counts = {"success": 0, "failed": 0, "skipped": 0}
    if not target_ids:
        return counts

    with get_sync_session() as session:
        activity = ActivityLogService(session)
        targets = list(
            session.scalars(select(Target).where(Target.id.in_(target_ids))).all()
        )
        if not infostealer.lookups_enabled(session):
            for target in targets:
                infostealer.mark(target, TaskStatus.SKIPPED, LOOKUPS_OFF_REASON)
            session.commit()
            counts["skipped"] = len(targets)
            return counts

        groups, none = infostealer.group_by_domain(targets)
        for target in none:
            infostealer.mark(target, TaskStatus.NOT_APPLICABLE, NOT_APPLICABLE_REASON)
        for group in groups.values():
            for target in group:
                infostealer.mark(target, TaskStatus.QUERYING)
        session.commit()
        counts["skipped"] = len(none)

        client = HudsonRockClient()
        try:
            for index, (domain, group) in enumerate(groups.items()):
                if index:
                    time.sleep(REQUEST_SPACING)
                ok = _resolve(session, activity, client, domain, group)
                counts["success" if ok else "failed"] += len(group)
        finally:
            stuck = [
                t
                for g in groups.values()
                for t in g
                if t.infostealer_status == TaskStatus.QUERYING
            ]
            if stuck:
                session.rollback()
                _failed(activity, stuck, ENRICHMENT_FAILED)
                session.commit()
            bump_sync(t.id for g in groups.values() for t in g)
    return counts
