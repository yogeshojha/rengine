from celery import Celery

from shared.config import BaseAppSettings
from shared.definitions.constants import (
    CRITICAL_QUEUE,
    DEFAULT_QUEUE,
    SCAN_CONTROL_QUEUE,
)
from shared.logging import get_logger

logger = get_logger(__name__)

_celery_client: Celery | None = None


def get_celery_client() -> Celery:
    global _celery_client  # noqa: PLW0603
    if _celery_client is None:
        _settings = BaseAppSettings()
        # kombu re-delivers messages older than this on any broker read
        visibility = _settings.TASK_HARD_TIME_LIMIT + 3600
        _celery_client = Celery(
            broker=_settings.celery_broker_url, set_as_current=False
        )
        _celery_client.conf.update(
            task_serializer="json",
            accept_content=["json"],
            broker_transport_options={"visibility_timeout": visibility},
            result_backend_transport_options={"visibility_timeout": visibility},
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

    logger.info("Dispatching DNS lookups for %d targets", len(target_ids))
    get_celery_client().send_task(
        "app.tasks.dns.perform_dns_lookups",
        kwargs={"target_ids": target_ids},
        queue="default",
    )


def dispatch_scan_run(scan_id: str, epoch: int) -> None:
    logger.info("Dispatching scan run %s", scan_id)
    get_celery_client().send_task(
        "app.tasks.scan.run_scan",
        kwargs={"scan_id": scan_id, "epoch": epoch},
        queue=SCAN_CONTROL_QUEUE,
    )


def dispatch_scan_resume(scan_id: str, epoch: int) -> None:
    logger.info("Dispatching scan resume %s", scan_id)
    get_celery_client().send_task(
        "app.tasks.scan.resume_scan",
        kwargs={"scan_id": scan_id, "epoch": epoch},
        queue=SCAN_CONTROL_QUEUE,
    )


def dispatch_scan_admission() -> None:
    get_celery_client().send_task(
        "app.tasks.scan.admit", kwargs={}, queue=SCAN_CONTROL_QUEUE
    )


def dispatch_scan_finalize(scan_id: str) -> None:
    logger.info("Dispatching scan finalize %s", scan_id)
    get_celery_client().send_task(
        "app.tasks.scan.finalize_scan",
        kwargs={"scan_id": scan_id},
        queue=SCAN_CONTROL_QUEUE,
    )


def revoke_scan_tasks(task_ids: list[str]) -> None:
    """Drop a scan's queued tasks. A task already running stops through its abort check."""
    if not task_ids:
        return
    logger.info("Revoking %d scan task(s)", len(task_ids))
    try:
        get_celery_client().control.revoke(list(task_ids))
    except Exception:
        logger.warning("scan task revoke failed", exc_info=True)


def dispatch_template_sync() -> bool:
    """Kick off a library refresh and the follow-up runs it feeds."""
    try:
        get_celery_client().send_task(
            "app.tasks.daily.run",
            kwargs={"jobs": ["library", "new_checks"]},
            queue="default",
        )
    except Exception:
        logger.warning("template sync dispatch failed", exc_info=True)
        return False
    return True


def dispatch_endpoint_verify(
    scan_id: str, host: str, dir_path: str | None, limit: int
) -> bool:
    """Verify one branch of a scan's endpoints on demand."""
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


def dispatch_scan_deltas_refresh(scan_id: str) -> bool:
    """Queue a recount of a live run's first-seen counts."""
    try:
        get_celery_client().send_task(
            "app.tasks.scan_deltas.refresh",
            kwargs={"scan_id": scan_id},
            queue="default",
        )
    except Exception:
        logger.warning("scan deltas dispatch failed", exc_info=True)
        return False
    return True


def dispatch_report(report_id: str) -> bool:
    """Queue a report render."""
    try:
        get_celery_client().send_task(
            "app.tasks.reports.generate", args=[report_id], queue="default"
        )
    except Exception:
        logger.warning("report dispatch failed", exc_info=True)
        return False
    return True


def dispatch_export(export_id: str) -> bool:
    """Queue an export run."""
    try:
        get_celery_client().send_task(
            "app.tasks.export.run", args=[export_id], queue="default"
        )
    except Exception:
        logger.warning("export dispatch failed", exc_info=True)
        return False
    return True


def dispatch_interest_evaluation(
    scan_id: str, *, include_ai: bool = True, notify: bool = True
) -> None:
    logger.info("Dispatching interest evaluation for scan %s", scan_id)
    get_celery_client().send_task(
        "app.tasks.interest.evaluate_scan",
        kwargs={"scan_id": scan_id, "include_ai": include_ai, "notify": notify},
        queue="default",
    )


def dispatch_interest_live(scan_id: str) -> None:
    """Re-judge a running scan from its rules alone."""
    try:
        get_celery_client().send_task(
            "app.tasks.interest.evaluate_live",
            kwargs={"scan_id": scan_id},
            queue="default",
        )
    except Exception:
        logger.warning("live interest dispatch failed", exc_info=True)


def dispatch_interest_refresh(project_id: str) -> None:
    logger.info("Dispatching interest refresh for project %s", project_id)
    get_celery_client().send_task(
        "app.tasks.interest.refresh_project",
        kwargs={"project_id": project_id},
        queue="default",
    )


def dispatch_threat_intel(scan_id: str, *, enrich: bool = True) -> bool:
    """Score a finished scan from the feeds, then fill the provider cache behind it."""
    try:
        client = get_celery_client()
        client.send_task(
            "app.tasks.threat_intel.apply_scan", args=[scan_id], queue="default"
        )
        if enrich:
            client.send_task(
                "app.tasks.threat_intel.enrich", args=[scan_id], queue="default"
            )
    except Exception:
        logger.warning("threat intel dispatch failed", exc_info=True)
        return False
    return True


def dispatch_dataset_sync(task: str, kwargs: dict) -> bool:
    """Queue one dataset's loader."""
    try:
        get_celery_client().send_task(task, kwargs=kwargs, queue=DEFAULT_QUEUE)
    except Exception:
        logger.warning("dataset sync dispatch failed", task=task, exc_info=True)
        return False
    return True


def dispatch_threat_intel_refresh(*, force: bool = False) -> bool:
    """Kick off a feed refresh."""
    try:
        get_celery_client().send_task(
            "app.tasks.threat_intel.refresh", kwargs={"force": force}, queue="default"
        )
    except Exception:
        logger.warning("threat intel refresh dispatch failed", exc_info=True)
        return False
    return True


def dispatch_bounty_sync(*, scopes: bool = True, platform: str | None = None) -> bool:
    """Refresh the bug bounty program library."""
    try:
        get_celery_client().send_task(
            "app.tasks.bounty_programs.sync",
            kwargs={"scopes": scopes, "platform": platform},
            queue="default",
        )
    except Exception:
        logger.warning("bounty program sync dispatch failed", exc_info=True)
        return False
    return True


def dispatch_bounty_report_sync(platform: str) -> bool:
    """Refresh the account's own reports and bounties."""
    try:
        get_celery_client().send_task(
            "app.tasks.bounty_programs.sync_reports",
            kwargs={"platform": platform},
            queue="default",
        )
    except Exception:
        logger.warning("bounty report sync dispatch failed", exc_info=True)
        return False
    return True


def dispatch_bounty_program_sync(handle: str, platform: str = "hackerone") -> bool:
    """Refresh one program's scope."""
    try:
        get_celery_client().send_task(
            "app.tasks.bounty_programs.sync_program",
            args=[handle, platform],
            queue="default",
        )
    except Exception:
        logger.warning("bounty program scope dispatch failed", exc_info=True)
        return False
    return True


def dispatch_bounty_feed_sync() -> bool:
    """Refresh the public program feed."""
    try:
        get_celery_client().send_task(
            "app.tasks.bounty_programs.sync_feed", queue="default"
        )
    except Exception:
        logger.warning("bounty feed sync dispatch failed", exc_info=True)
        return False
    return True


def dispatch_toolbox_run(
    *,
    run_id: str,
    user_id: str,
    tool: str,
    payload: dict,
    project_id: str | None,
) -> bool:
    """Hand a toolbox run to the worker."""
    try:
        get_celery_client().send_task(
            "app.tasks.toolbox.run",
            kwargs={
                "run_id": run_id,
                "user_id": user_id,
                "tool": tool,
                "payload": payload,
                "project_id": project_id,
            },
            queue=CRITICAL_QUEUE,
        )
    except Exception:
        logger.warning("toolbox dispatch failed", exc_info=True)
        return False
    return True


def dispatch_watch_certificate(cert: dict) -> bool:
    """One discovered certificate from the stream."""
    try:
        get_celery_client().send_task(
            "app.tasks.watch.certificate", kwargs={"cert": cert}, queue="default"
        )
        return True
    except Exception:
        logger.warning("watch certificate dispatch failed", exc_info=True)
        return False


def dispatch_watch_settle(scan_id: str) -> bool:
    try:
        get_celery_client().send_task(
            "app.tasks.watch.settle", kwargs={"scan_id": scan_id}, queue="default"
        )
        return True
    except Exception:
        logger.warning("watch settle dispatch failed", exc_info=True)
        return False


def dispatch_tripwire_settle(scan_id: str) -> bool:
    try:
        get_celery_client().send_task(
            "app.tasks.tripwires.settle", kwargs={"scan_id": scan_id}, queue="default"
        )
        return True
    except Exception:
        logger.warning("tripwire settle dispatch failed", exc_info=True)
        return False


def dispatch_tripwire_live(scan_id: str, dimension: str) -> None:
    try:
        get_celery_client().send_task(
            "app.tasks.tripwires.live",
            kwargs={"scan_id": scan_id, "dimension": dimension},
            queue="default",
        )
    except Exception:
        logger.warning("tripwire live dispatch failed", exc_info=True)


def dispatch_watch_reconcile(program_id: str | None = None) -> bool:
    try:
        get_celery_client().send_task(
            "app.tasks.watch.reconcile",
            kwargs={"program_id": program_id},
            queue="default",
        )
        return True
    except Exception:
        logger.warning("watch reconcile dispatch failed", exc_info=True)
        return False


def dispatch_issue_filing(issue_ids: list[str]) -> bool:
    """Queue filing of pending issues and comments on the named issues."""
    try:
        get_celery_client().send_task(
            "app.tasks.issue_trackers.file",
            kwargs={"issue_ids": issue_ids},
            queue=DEFAULT_QUEUE,
        )
    except Exception:
        logger.warning("issue filing dispatch failed", exc_info=True)
        return False
    return True


def dispatch_issue_observe(scan_id: str) -> bool:
    """Queue the rescan comments a finished run owes its filed issues."""
    try:
        get_celery_client().send_task(
            "app.tasks.issue_trackers.observe",
            kwargs={"scan_id": scan_id},
            queue=DEFAULT_QUEUE,
        )
    except Exception:
        logger.warning("issue observe dispatch failed", exc_info=True)
        return False
    return True
