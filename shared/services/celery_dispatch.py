from celery import Celery

from shared.config import BaseAppSettings
from shared.definitions.constants import SCANS_QUEUE
from shared.logging import get_logger

logger = get_logger(__name__)

_celery_client: Celery | None = None


def get_celery_client() -> Celery:
    global _celery_client  # noqa: PLW0603
    if _celery_client is None:
        _settings = BaseAppSettings()
        # never set_as_current: this client carries no result backend, and adopting it as
        # the ambient app leaves every later chord in the process unable to start
        _celery_client = Celery(
            broker=_settings.celery_broker_url, set_as_current=False
        )
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


def dispatch_scan_run(scan_id: str) -> None:
    logger.info("Dispatching scan run %s", scan_id)
    get_celery_client().send_task(
        "app.tasks.scan.run_scan",
        kwargs={"scan_id": scan_id},
        queue=SCANS_QUEUE,
    )


def revoke_scan_tasks(task_ids: list[str]) -> None:
    """SIGKILL-revoke a scan's celery tasks so an in-flight scan stops promptly."""
    if not task_ids:
        return
    logger.info("Revoking %d scan task(s)", len(task_ids))
    try:
        get_celery_client().control.revoke(
            list(task_ids), terminate=True, signal="SIGKILL"
        )
    except Exception:
        logger.warning("scan task revoke failed", exc_info=True)


def dispatch_template_sync() -> bool:
    """Kick off a library refresh. Returns whether the queue accepted it."""
    try:
        get_celery_client().send_task("app.tasks.vuln_templates.sync", queue="default")
    except Exception:
        logger.warning("template sync dispatch failed", exc_info=True)
        return False
    return True


def dispatch_endpoint_verify(
    scan_id: str, host: str, dir_path: str | None, limit: int
) -> bool:
    """Verify one branch of a scan's endpoints on demand. Returns whether the queue took it."""
    try:
        get_celery_client().send_task(
            "app.tasks.endpoints.verify_branch",
            kwargs={
                "scan_id": scan_id,
                "host": host,
                "dir_path": dir_path,
                "limit": limit,
            },
            queue="default",
        )
    except Exception:
        logger.warning("endpoint verify dispatch failed", exc_info=True)
        return False
    return True


def dispatch_report(report_id: str) -> bool:
    """Queue a report render. Returns whether the queue took it."""
    try:
        get_celery_client().send_task(
            "app.tasks.reports.generate", args=[report_id], queue="default"
        )
    except Exception:
        logger.warning("report dispatch failed", exc_info=True)
        return False
    return True


def dispatch_interest_evaluation(scan_id: str, *, include_ai: bool = True) -> None:
    logger.info("Dispatching interest evaluation for scan %s", scan_id)
    get_celery_client().send_task(
        "app.tasks.interest.evaluate_scan",
        kwargs={"scan_id": scan_id, "include_ai": include_ai},
        queue="default",
    )


def dispatch_interest_refresh(project_id: str) -> None:
    logger.info("Dispatching interest refresh for project %s", project_id)
    get_celery_client().send_task(
        "app.tasks.interest.refresh_project",
        kwargs={"project_id": project_id},
        queue="default",
    )
