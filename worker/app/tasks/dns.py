"""Celery task for DNS enrichment of domain targets."""

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.target import Target
from shared.services.activity_log import ActivityLogService
from shared.utils.datetime import utc_now
from tools.dnsx.service import DnsxService, DnsxServiceError

logger = get_logger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.dns.perform_dns_lookups",
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=360,
)
def perform_dns_lookups(self, target_ids: list[str]) -> dict:  # noqa: ARG001, PLR0915
    """Run dnsx recon on domain targets and store the records for correlation."""
    logger.info(f"DNS lookup task started for {len(target_ids)} target(s)")

    try:
        service = DnsxService()
    except DnsxServiceError as e:
        logger.error(f"Failed to initialize DNS service: {e}")
        _mark_all_failed(target_ids, str(e))
        return {"error": str(e), "success": 0, "failed": len(target_ids), "skipped": 0}

    results = {"success": 0, "failed": 0, "skipped": 0}

    with get_sync_session() as session:
        activity = ActivityLogService(session)

        for target_id in target_ids:
            target = session.execute(
                select(Target).where(Target.id == target_id)
            ).scalar_one_or_none()

            if not target:
                logger.warning(f"Target {target_id} not found, skipping")
                results["skipped"] += 1
                continue

            # Only process domain targets
            if target.target_type != TargetType.DOMAIN:
                logger.debug(
                    f"Target {target_id} is {target.target_type.value}, "
                    f"skipping DNS lookup"
                )
                target.dns_status = TaskStatus.SKIPPED
                session.commit()
                results["skipped"] += 1
                continue

            target.dns_status = TaskStatus.QUERYING
            target.dns_error = None
            session.commit()

            try:
                lookup = service.lookup_and_store(
                    session=session,
                    target_id=target.id,
                    domain=target.target_value,
                )

                # Link lookup to target and mark complete
                target.dns_lookup_id = lookup.id
                target.dns_status = TaskStatus.SUCCESS
                target.dns_error = None
                target.updated_at = utc_now()
                session.commit()

                record_count = len(lookup.records) if lookup.records else 0
                logger.info(
                    f"DNS lookup completed for {target.target_value}: "
                    f"{record_count} records stored"
                )
                results["success"] += 1

                # log
                activity.log(
                    event=ActivityEvent.TARGET_ENRICHMENT_DNS_COMPLETED,
                    title="DNS Query completed.",
                    description=f"{record_count} records stored",
                    level=ActivityLevel.SUCCESS,
                    target_id=target.id,
                    project_id=target.project_id,
                )
                session.commit()

            except DnsxServiceError as e:
                logger.warning(f"DNS lookup failed for {target.target_value}: {e}")
                target.dns_status = TaskStatus.FAILED
                target.dns_error = str(e)[:1000]
                target.updated_at = utc_now()
                session.commit()
                results["failed"] += 1

            except Exception as e:
                logger.error(
                    f"Unexpected error in DNS lookup for {target.target_value}: {e}",
                    exc_info=True,
                )
                target.dns_status = TaskStatus.FAILED
                target.dns_error = f"Unexpected error: {str(e)[:900]}"
                target.updated_at = utc_now()
                session.commit()
                results["failed"] += 1
                activity.log(
                    event=ActivityEvent.TARGET_ENRICHMENT_DNS_FAILED,
                    title="DNS Query failed.",
                    description=str(e)[:1000],
                    level=ActivityLevel.ERROR,
                    target_id=target.id,
                    project_id=target.project_id,
                )
                session.commit()

    logger.info(
        f"DNS lookup task completed: "
        f"{results['success']} success, "
        f"{results['failed']} failed, "
        f"{results['skipped']} skipped"
    )
    return results


def _mark_all_failed(target_ids: list[str], error: str) -> None:
    """Mark all targets as DNS failed (used when service init fails)."""
    try:
        with get_sync_session() as session:
            for target_id in target_ids:
                target = session.execute(
                    select(Target).where(Target.id == target_id)
                ).scalar_one_or_none()
                if target:
                    target.dns_status = TaskStatus.FAILED
                    target.dns_error = error[:1000]
                    target.updated_at = utc_now()
            session.commit()
    except Exception as e:
        logger.error(f"Failed to mark targets as DNS failed: {e}")
