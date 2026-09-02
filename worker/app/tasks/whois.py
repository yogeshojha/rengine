from sqlalchemy import select

from app.celery import celery_app
from app.config import settings
from app.database import get_sync_session
from shared.definitions.notifications import (
    whois_enrichment_complete,
    whois_enrichment_failed,
)
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.target import Target
from shared.services.activity_log import ActivityLogService
from shared.services.notification_sync import SyncNotificationPublisher
from shared.utils.datetime import utc_now
from shared.utils.validation import normalize_query
from tools.whois.service import WhoisService

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.whois.perform_whois_lookups",
    queue="default",
    max_retries=0,
    soft_time_limit=600,
    time_limit=900,
)
def perform_whois_lookups(target_ids: list[str]) -> dict:  # noqa: PLR0915
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
            normalized = normalize_query(target.target_value, target.target_type)
            query_groups.setdefault(normalized, []).append(target)

        success_count = 0
        failed_count = 0

        for normalized_query, group_targets in query_groups.items():
            representative = group_targets[0]

            try:
                record = service.get_or_create_record_sync(
                    session, normalized_query, representative.target_type
                )

                for target in group_targets:
                    target.whois_record_id = record.id
                    target.whois_status = TaskStatus.SUCCESS
                    target.whois_error = None
                    target.updated_at = utc_now()
                    success_count += 1
                    activity.log(
                        event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_COMPLETED,
                        title="WHOIS query completed.",
                        level=ActivityLevel.SUCCESS,
                        target_id=target.id,
                        project_id=target.project_id,
                    )

                session.commit()

            except Exception as e:
                error_msg = str(e)[:1000]
                logger.warning(
                    "WHOIS lookup failed for %s: %s", normalized_query, error_msg
                )
                for target in group_targets:
                    target.whois_status = TaskStatus.FAILED
                    target.whois_error = error_msg
                    target.updated_at = utc_now()
                    failed_count += 1
                    activity.log(
                        event=ActivityEvent.TARGET_ENRICHMENT_WHOIS_FAILED,
                        title="WHOIS query failed.",
                        description=error_msg,
                        level=ActivityLevel.ERROR,
                        target_id=target.id,
                        project_id=target.project_id,
                    )
                session.commit()

        total = success_count + failed_count
        template = whois_enrichment_complete(
            success=success_count, failed=failed_count, total=total
        )
        notifier.publish(
            session=session,
            type=template["type"],
            severity=template["severity"],
            title=template["title"],
            message=template["message"],
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
                    title=f"WHOIS failed for {target.target_value}",
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
