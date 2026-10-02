from sqlalchemy import select

from app.celery import celery_app
from app.database import get_sync_session
from shared.definitions.notifications import ENRICHMENT_FAILED
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.task_status import TaskStatus
from shared.http import egress_proxy
from shared.logging import get_logger
from shared.models.target import Target
from shared.services.activity_log import ActivityLogService
from shared.utils.datetime import utc_now
from tools.whois.service import WhoisError, WhoisNotApplicableError, WhoisService

logger = get_logger(__name__)


def _fail_group(
    session,
    activity: ActivityLogService,
    targets: list[Target],
    error: str,
) -> tuple[int, int]:
    """Stamp one failure on every target sharing the query."""
    session.rollback()
    for target in targets:
        target.whois_status = TaskStatus.FAILED
        target.whois_error = error
        target.updated_at = utc_now()
        activity.log(
            event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_FAILED,
            title=f"WHOIS lookup failed · {target.target_value}",
            description=error,
            level=ActivityLevel.ERROR,
            target_id=target.id,
            project_id=target.project_id,
        )
    session.commit()
    return 0, len(targets)


def _resolve_group(
    session,
    activity: ActivityLogService,
    service: WhoisService,
    normalized_query: str,
    targets: list[Target],
) -> tuple[int, int]:
    """Resolve one registry query and stamp its outcome on every target sharing it."""
    try:
        record = service.get_or_create_record_sync(
            session, normalized_query, targets[0].target_type
        )
    except WhoisNotApplicableError as exc:
        reason = str(exc)[:1000]
        logger.info("WHOIS not applicable for %s: %s", normalized_query, reason)
        for target in targets:
            target.whois_status = TaskStatus.NOT_APPLICABLE
            target.whois_error = reason
            target.updated_at = utc_now()
        session.commit()
        return 0, 0
    except WhoisError as exc:
        error = str(exc)[:1000]
        logger.warning("WHOIS lookup failed for %s: %s", normalized_query, error)
        return _fail_group(session, activity, targets, error)
    except Exception:
        logger.exception("WHOIS lookup failed for %s", normalized_query)
        return _fail_group(session, activity, targets, ENRICHMENT_FAILED)

    for target in targets:
        target.whois_record_id = record.id
        target.whois_status = TaskStatus.SUCCESS
        target.whois_error = None
        target.updated_at = utc_now()
        activity.log(
            event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_COMPLETED,
            title=f"WHOIS lookup completed · {target.target_value}",
            level=ActivityLevel.SUCCESS,
            target_id=target.id,
            project_id=target.project_id,
        )
    session.commit()
    return len(targets), 0


@celery_app.task(
    name="app.tasks.whois.perform_whois_lookups",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def perform_whois_lookups(target_ids: list[str]) -> dict:
    """WHOIS a batch of targets, deduped by normalized query value."""
    if not target_ids:
        return {"success": 0, "failed": 0, "total": 0}

    session = get_sync_session()
    activity = ActivityLogService(session)

    try:
        service = WhoisService(proxy_url=egress_proxy())
        service.ensure_ready()

        targets = (
            session.execute(select(Target).where(Target.id.in_(target_ids)))
            .scalars()
            .all()
        )

        if not targets:
            logger.warning("No targets found for IDs: %s", target_ids)
            return {"success": 0, "failed": 0, "total": 0}

        for target in targets:
            target.whois_status = TaskStatus.QUERYING
        session.commit()

        query_groups: dict[str, list[Target]] = {}
        for target in targets:
            normalized = service.lookup_key(target.target_value, target.target_type)
            query_groups.setdefault(normalized, []).append(target)

        success_count = 0
        failed_count = 0

        for normalized_query, group_targets in query_groups.items():
            ok, failed = _resolve_group(
                session, activity, service, normalized_query, group_targets
            )
            success_count += ok
            failed_count += failed

        total = success_count + failed_count
        return {"success": success_count, "failed": failed_count, "total": total}

    except Exception:
        logger.exception("WHOIS enrichment task failed entirely")
        try:
            session.rollback()
            remaining = (
                session.execute(
                    select(Target).where(
                        Target.id.in_(target_ids),
                        Target.whois_status == TaskStatus.QUERYING,
                    )
                )
                .scalars()
                .all()
            )

            for target in remaining:
                target.whois_status = TaskStatus.FAILED
                target.whois_error = ENRICHMENT_FAILED
                target.updated_at = utc_now()
                activity.log(
                    event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_FAILED,
                    title=f"WHOIS lookup failed · {target.target_value}",
                    description=ENRICHMENT_FAILED,
                    level=ActivityLevel.ERROR,
                    target_id=target.id,
                    project_id=target.project_id,
                )
            session.commit()
        except Exception:
            logger.exception("Failed to update target statuses after task failure")

        raise

    finally:
        session.close()
