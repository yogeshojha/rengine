from celery import Celery

from shared.config import BaseAppSettings
from shared.logging import get_logger

logger = get_logger(__name__)

_celery_client: Celery | None = None


def get_celery_client() -> Celery:
    global _celery_client  # noqa: PLW0603
    if _celery_client is None:
        _settings = BaseAppSettings()
        _celery_client = Celery(broker=_settings.celery_broker_url)
        _celery_client.conf.update(
            task_serializer="json",
            accept_content=["json"],
        )
    return _celery_client


def dispatch_whois_lookups(target_ids: list[str]) -> None:
    if not target_ids:
        return
    logger.info("Dispatching WHOIS lookups for %d targets", len(target_ids))
    get_celery_client().send_task(
        "app.tasks.whois.perform_whois_lookups",
        kwargs={"target_ids": target_ids},
        queue="default",
    )


def dispatch_ripestat_enrichment(target_ids: list[str]) -> None:
    if not target_ids:
        return

    logger.info("Dispatching RIPEstat enrichment for %d targets", len(target_ids))
    get_celery_client().send_task(
        "app.tasks.ripestat.enrich_targets_bgp",
        kwargs={"target_ids": target_ids},
        queue="default",
    )


def dispatch_dns_lookups(target_ids: list[str]) -> None:
    if not target_ids:
        return

    logger.info(f"Dispatching DNS lookup for {len(target_ids)} target(s)")
    get_celery_client().send_task(
        "app.tasks.dns.perform_dns_lookups",
        kwargs={"target_ids": target_ids},
        queue="default",
    )
