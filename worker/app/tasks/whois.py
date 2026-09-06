from sqlalchemy import select

from app.celery import celery_app
from app.config import settings
from app.database import get_sync_session
from shared.definitions.notifications import (
    whois_enrichment_failed,
    whois_enrichment_incomplete,
)
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.target import Target
from shared.services.activity_log import ActivityLogService
from shared.services.notification_sync import (
    SyncNotificationPublisher,
    single_project,
)
from shared.utils.datetime import utc_now
from tools.whois.service import WhoisNotApplicableError, WhoisService

logger = get_logger(__name__)


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
        # no registry can hold this record; that is an answer, not a failure
        reason = str(exc)[:1000]
        logger.info("WHOIS not applicable for %s: %s", normalized_query, reason)
        for target in targets:
            target.whois_status = TaskStatus.NOT_APPLICABLE
            target.whois_error = reason
            target.updated_at = utc_now()
        session.commit()
        return 0, 0
    except Exception as exc:
        error = str(exc)[:1000]
        logger.warning("WHOIS lookup failed for %s: %s", normalized_query, error)
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
    queue="default",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def perform_whois_lookups(target_ids: list[str]) -> dict:
    """WHOIS a batch of targets, deduped by normalized query value."""
    if not target_ids:
        return {"success": 0, "failed": 0, "total": 0}

    session = get_sync_session()
    notifier = SyncNotificationPublisher(settings.celery_broker_url)
    activity = ActivityLogService(session)

    try:
        service = WhoisService()
        service.ensure_ready()

        # load all targets
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
        template = whois_enrichment_incomplete(
            success=success_count, failed=failed_count, total=total
        )
        if template:
            notifier.publish(
                session=session,
                type=template["type"],
                severity=template["severity"],
                title=template["title"],
                message=template["message"],
                project_id=single_project(targets),
            )

        return {"success": success_count, "failed": failed_count, "total": total}

    except Exception as e:
        logger.exception("WHOIS enrichment task failed entirely")
        try:
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
                target.whois_error = str(e)[:1000]
                target.updated_at = utc_now()
                activity.log(
                    event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_FAILED,
                    title=f"WHOIS lookup failed · {target.target_value}",
                    description=str(e)[:1000],
                    level=ActivityLevel.ERROR,
                    target_id=target.id,
                    project_id=target.project_id,
                )
            session.commit()
        except Exception:
            logger.exception("Failed to update target statuses after task failure")

        template = whois_enrichment_failed(str(e)[:500])
        try:
            notifier.publish(
                session=session,
                type=template["type"],
                severity=template["severity"],
                title=template["title"],
                message=template["message"],
            )
        except Exception:
            logger.exception("Failed to send failure notification")

        raise

    finally:
        session.close()
