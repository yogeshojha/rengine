"""RIPEstat enrichment tasks, triggered after target creation."""

from sqlalchemy import select
from sqlmodel import col

from app.celery import celery_app
from app.database import get_sync_session
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.logging import get_logger
from shared.models.target import Target
from shared.services.bgp_summary import write_bgp_summary_for_target
from shared.utils.net import is_registry_routable
from tools.ripestat.service import RIPEStatLookupError, RIPEStatService

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.ripestat.enrich_targets_bgp",
    soft_time_limit=600,
    time_limit=900,
)
def enrich_targets_bgp(target_ids: list[str]) -> dict:
    """Run the RIPEstat lookups for a batch of targets, grouped by target type."""
    if not target_ids:
        return {"success": 0, "failed": 0, "skipped": 0}

    session = get_sync_session()

    try:
        targets = (
            session.execute(select(Target).where(col(Target.id).in_(target_ids)))
            .scalars()
            .all()
        )
        if not targets:
            logger.warning("No targets found for IDs: %s", target_ids)
            return {"success": 0, "failed": 0, "skipped": 0}

        service = RIPEStatService()
        success = 0
        failed = 0
        skipped = 0

        for target in targets:
            try:
                _enrich_target(service, session, target)
            except Exception:
                logger.exception(
                    "RIPEstat enrichment failed for %s (%s)",
                    target.target_value,
                    target.target_type,
                )
                failed += 1
                continue
            if target.bgp_status == TaskStatus.SUCCESS:
                success += 1
            elif target.bgp_status == TaskStatus.NOT_APPLICABLE:
                skipped += 1
            else:
                failed += 1

        logger.info(
            "RIPEstat enrichment complete: %d success, %d failed, %d skipped",
            success,
            failed,
            skipped,
        )
        return {"success": success, "failed": failed, "skipped": skipped}

    except Exception:
        logger.exception("RIPEstat enrichment task failed entirely")

        raise

    finally:
        session.close()


def _enrich_target(service: RIPEStatService, session, target: Target) -> int:
    """Run target-type-specific lookups."""
    target.bgp_status = TaskStatus.QUERYING
    session.commit()

    if target.target_type in (
        TargetType.IP,
        TargetType.IP_RANGE,
    ) and not is_registry_routable(target.target_value):
        target.bgp_status = TaskStatus.NOT_APPLICABLE
        session.commit()
        return 0

    try:
        match target.target_type:
            case TargetType.ASN:
                count = _enrich_asn(service, session, target.target_value)
            case TargetType.IP:
                count = _enrich_ip(service, session, target.target_value)
            case TargetType.IP_RANGE:
                count = _enrich_ip_range(service, session, target.target_value)
            case _:
                target.bgp_status = TaskStatus.NOT_APPLICABLE
                session.commit()
                return 0

        if count > 0:
            write_bgp_summary_for_target(session, target)
            target.bgp_status = TaskStatus.SUCCESS
        else:
            target.bgp_status = TaskStatus.FAILED
        session.commit()
        return count

    except Exception:
        session.rollback()
        target.bgp_status = TaskStatus.FAILED
        session.commit()
        raise


def _enrich_asn(service: RIPEStatService, session, asn: str) -> int:
    """ASN targets: prefixes, neighbours, overview, abuse contact."""
    lookups = 0

    try:
        service.announced_prefixes_sync(session, asn)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("announced_prefixes failed for %s", asn)

    try:
        service.asn_neighbours_sync(session, asn)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("asn_neighbours failed for %s", asn)

    try:
        service.as_overview_sync(session, asn)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("as_overview failed for %s", asn)

    try:
        service.abuse_contact_sync(session, asn)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("abuse_contact failed for %s", asn)

    return lookups


def _enrich_ip(service: RIPEStatService, session, ip: str) -> int:
    """IP targets: network info (-> prefix + ASN) and abuse contact."""
    lookups = 0

    try:
        service.network_info_sync(session, ip)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("network_info failed for %s", ip)

    try:
        service.abuse_contact_sync(session, ip)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("abuse_contact failed for %s", ip)

    return lookups


def _enrich_ip_range(service: RIPEStatService, session, prefix: str) -> int:
    """IP_RANGE targets: prefix overview and related prefixes."""
    lookups = 0

    try:
        service.prefix_overview_sync(session, prefix)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("prefix_overview failed for %s", prefix)

    try:
        service.related_prefixes_sync(session, prefix)
        lookups += 1
    except RIPEStatLookupError:
        logger.warning("related_prefixes failed for %s", prefix)

    return lookups
