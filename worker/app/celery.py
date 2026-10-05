import gc
import os
import time
from pathlib import Path

from celery import Celery, bootsteps
from celery.platforms import EX_FAILURE
from celery.signals import (
    setup_logging,
    task_failure,
    task_postrun,
    task_prerun,
    worker_before_create_process,
    worker_process_init,
    worker_ready,
    worker_shutdown,
)
from kombu import Exchange, Queue

from app.config import settings
from shared.definitions.constants import (
    CRITICAL_QUEUE,
    DEFAULT_QUEUE,
    SCAN_CONTROL_QUEUE,
    SCAN_QUEUES,
    SCANS_QUEUE,
)
from shared.definitions.issue_trackers import STATUS_REFRESH_SECONDS
from shared.definitions.workers import (
    HEARTBEAT_PATH,
    HEARTBEAT_SECONDS,
    STOPPED_GRACE_SECONDS,
)
from shared.logging import get_logger
from shared.logging import setup_logging as setup_rengine_logging
from shared.utils.fork import release_sockets_to

logger = get_logger(__name__)

celery_app = Celery("rengine")


_VISIBILITY_TIMEOUT = settings.TASK_HARD_TIME_LIMIT + 3600

_RESULT_EXPIRES = settings.TASK_HARD_TIME_LIMIT + 3600

celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": _VISIBILITY_TIMEOUT},
    result_backend_transport_options={"visibility_timeout": _VISIBILITY_TIMEOUT},
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    result_expires=_RESULT_EXPIRES,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.TASK_HARD_TIME_LIMIT,
    worker_send_task_events=True,
    worker_max_tasks_per_child=100,
    worker_pool="prefork",
    worker_hijack_root_logger=False,
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule_filename="/app/beat-state/celerybeat-schedule",
)


default_exchange = Exchange(DEFAULT_QUEUE, type="direct")
scan_exchange = Exchange(SCANS_QUEUE, type="direct")

celery_app.conf.task_queues = (
    Queue(
        CRITICAL_QUEUE,
        exchange=default_exchange,
        routing_key=CRITICAL_QUEUE,
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        DEFAULT_QUEUE,
        exchange=default_exchange,
        routing_key=DEFAULT_QUEUE,
        queue_arguments={"x-max-priority": 5},
    ),
    Queue(
        SCANS_QUEUE,
        exchange=scan_exchange,
        routing_key=SCANS_QUEUE,
        queue_arguments={"x-max-priority": 5},
    ),
    Queue(
        SCAN_CONTROL_QUEUE,
        exchange=Exchange(SCAN_CONTROL_QUEUE, type="direct"),
        routing_key=SCAN_CONTROL_QUEUE,
    ),
)

celery_app.conf.task_default_queue = DEFAULT_QUEUE
celery_app.conf.task_default_exchange = default_exchange.name
celery_app.conf.task_default_routing_key = DEFAULT_QUEUE


celery_app.conf.task_routes = {
    "app.tasks.scan.reap_stalled": {"queue": DEFAULT_QUEUE},
    "app.tasks.scan.run_scan_stage": {"queue": SCANS_QUEUE},
    "app.tasks.scan.*": {"queue": SCAN_CONTROL_QUEUE},
    "app.tasks.toolbox.*": {"queue": CRITICAL_QUEUE},
}


celery_app.autodiscover_tasks(
    [
        "app.tasks.whois",
        "app.tasks.infostealer",
        "app.tasks.ripestat",
        "app.tasks.dns",
        "app.tasks.scan",
        "app.tasks.source_ip",
        "app.tasks.schedule",
        "app.tasks.ip_asn",
        "app.tasks.vuln_templates",
        "app.tasks.daily",
        "app.tasks.freshness",
        "app.tasks.endpoints",
        "app.tasks.reports",
        "app.tasks.export",
        "app.tasks.interest",
        "app.tasks.notifications",
        "app.tasks.threat_intel",
        "app.tasks.bounty_programs",
        "app.tasks.toolbox",
        "app.tasks.retention",
        "app.tasks.hygiene",
        "app.tasks.screenshots",
        "app.tasks.software",
        "app.tasks.secrets",
        "app.tasks.scan_deltas",
        "app.tasks.watch",
        "app.tasks.estate",
        "app.tasks.issue_trackers",
        "app.tasks.tripwires",
    ]
)


SCHEDULE_TICK_SECONDS = 60.0
STALL_REAP_SECONDS = 300.0
TRIPWIRE_PRUNE_SECONDS = 24 * 60 * 60.0
IP_RANGE_REFRESH_SECONDS = 7 * 24 * 60 * 60.0
TEMPLATE_SYNC_SECONDS = 24 * 60 * 60.0
REPORT_CLEANUP_SECONDS = 24 * 60 * 60.0
REPORT_REAP_SECONDS = 10 * 60.0
EXPORT_CLEANUP_SECONDS = 24 * 60 * 60.0
EXPORT_REAP_SECONDS = 10 * 60.0
NOTIFICATION_CLEANUP_SECONDS = 6 * 60 * 60.0
RETENTION_SECONDS = 24 * 60 * 60.0
THREAT_INTEL_REFRESH_SECONDS = 24 * 60 * 60.0
CERT_RECHECK_SECONDS = 4 * 60 * 60.0
SOFTWARE_BACKFILL_SECONDS = 5 * 60.0
SECRET_BACKFILL_SECONDS = 5 * 60.0
ESTATE_ENRICH_SECONDS = 5 * 60.0
HYGIENE_BACKFILL_SECONDS = 5 * 60.0
SCAN_DELTAS_BACKFILL_SECONDS = 5 * 60.0
WATCH_RECHECK_SECONDS = 10 * 60.0
ISSUE_STATUS_SECONDS = float(STATUS_REFRESH_SECONDS)

# the task itself decides whether the interval is due
BOUNTY_SYNC_TICK_SECONDS = 60 * 60

celery_app.conf.beat_schedule = {
    "issue-status-refresh": {
        "task": "app.tasks.issue_trackers.refresh",
        "schedule": ISSUE_STATUS_SECONDS,
        "options": {"expires": ISSUE_STATUS_SECONDS},
    },
    "scan-schedule-tick": {
        "task": "app.tasks.schedule.tick",
        "schedule": SCHEDULE_TICK_SECONDS,
        "options": {"expires": SCHEDULE_TICK_SECONDS},
    },
    "scan-stall-reap": {
        "task": "app.tasks.scan.reap_stalled",
        "schedule": STALL_REAP_SECONDS,
        "options": {"expires": STALL_REAP_SECONDS},
    },
    "bounty-program-sync": {
        "task": "app.tasks.bounty_programs.sync",
        "schedule": BOUNTY_SYNC_TICK_SECONDS,
        "kwargs": {"force": False},
        "options": {"expires": BOUNTY_SYNC_TICK_SECONDS},
    },
    "bounty-report-sync": {
        "task": "app.tasks.bounty_programs.sync_reports",
        "schedule": BOUNTY_SYNC_TICK_SECONDS,
        "kwargs": {"force": False},
        "options": {"expires": BOUNTY_SYNC_TICK_SECONDS},
    },
    "bounty-feed-sync": {
        "task": "app.tasks.bounty_programs.sync_feed",
        "schedule": BOUNTY_SYNC_TICK_SECONDS,
        "kwargs": {"force": False},
        "options": {"expires": BOUNTY_SYNC_TICK_SECONDS},
    },
    "ip-range-refresh": {
        "task": "app.tasks.ip_asn.refresh",
        "schedule": IP_RANGE_REFRESH_SECONDS,
        "options": {"expires": IP_RANGE_REFRESH_SECONDS},
    },
    "ip-range-backfill": {
        "task": "app.tasks.ip_asn.backfill",
        "schedule": HYGIENE_BACKFILL_SECONDS,
        "options": {"expires": HYGIENE_BACKFILL_SECONDS},
    },
    "daily-jobs": {
        "task": "app.tasks.daily.run",
        "schedule": TEMPLATE_SYNC_SECONDS,
        "options": {"expires": TEMPLATE_SYNC_SECONDS},
    },
    "report-cleanup": {
        "task": "app.tasks.reports.cleanup",
        "schedule": REPORT_CLEANUP_SECONDS,
        "options": {"expires": REPORT_CLEANUP_SECONDS},
    },
    "report-reap": {
        "task": "app.tasks.reports.reap",
        "schedule": REPORT_REAP_SECONDS,
        "options": {"expires": REPORT_REAP_SECONDS},
    },
    "export-cleanup": {
        "task": "app.tasks.export.cleanup",
        "schedule": EXPORT_CLEANUP_SECONDS,
        "options": {"expires": EXPORT_CLEANUP_SECONDS},
    },
    "export-reap": {
        "task": "app.tasks.export.reap",
        "schedule": EXPORT_REAP_SECONDS,
        "options": {"expires": EXPORT_REAP_SECONDS},
    },
    "notification-cleanup": {
        "task": "app.tasks.notifications.cleanup",
        "schedule": NOTIFICATION_CLEANUP_SECONDS,
        "options": {"expires": NOTIFICATION_CLEANUP_SECONDS},
    },
    "retention-enforce": {
        "task": "app.tasks.retention.enforce",
        "schedule": RETENTION_SECONDS,
        "options": {"expires": RETENTION_SECONDS},
    },
    "threat-intel-refresh": {
        "task": "app.tasks.threat_intel.refresh",
        "schedule": THREAT_INTEL_REFRESH_SECONDS,
        "options": {"expires": THREAT_INTEL_REFRESH_SECONDS},
    },
    "certificate-recheck": {
        "task": "app.tasks.freshness.certificates",
        "schedule": CERT_RECHECK_SECONDS,
        "options": {"expires": CERT_RECHECK_SECONDS},
    },
    "hygiene-backfill": {
        "task": "app.tasks.hygiene.backfill",
        "schedule": HYGIENE_BACKFILL_SECONDS,
        "options": {"expires": HYGIENE_BACKFILL_SECONDS},
    },
    "screenshot-backfill": {
        "task": "app.tasks.screenshots.backfill",
        "schedule": HYGIENE_BACKFILL_SECONDS,
        "options": {"expires": HYGIENE_BACKFILL_SECONDS},
    },
    "software-backfill": {
        "task": "app.tasks.software.backfill",
        "schedule": SOFTWARE_BACKFILL_SECONDS,
        "options": {"expires": SOFTWARE_BACKFILL_SECONDS},
    },
    "secret-backfill": {
        "task": "app.tasks.secrets.backfill",
        "schedule": SECRET_BACKFILL_SECONDS,
        "options": {"expires": SECRET_BACKFILL_SECONDS},
    },
    "estate-enrich": {
        "task": "app.tasks.estate.enrich",
        "schedule": ESTATE_ENRICH_SECONDS,
        "options": {"expires": ESTATE_ENRICH_SECONDS},
    },
    "scan-deltas-backfill": {
        "task": "app.tasks.scan_deltas.backfill",
        "schedule": SCAN_DELTAS_BACKFILL_SECONDS,
        "options": {"expires": SCAN_DELTAS_BACKFILL_SECONDS},
    },
    "watch-recheck": {
        "task": "app.tasks.watch.recheck",
        "schedule": WATCH_RECHECK_SECONDS,
        "options": {"expires": WATCH_RECHECK_SECONDS},
    },
    "tripwire-prune": {
        "task": "app.tasks.tripwires.prune",
        "schedule": TRIPWIRE_PRUNE_SECONDS,
        "options": {"expires": TRIPWIRE_PRUNE_SECONDS},
    },
}


@setup_logging.connect
def configure_logging(loglevel: int, **kwargs) -> None:  # noqa: ARG001
    """Configure logging for Celery workers."""
    setup_rengine_logging(level=settings.LOG_LEVEL)


@worker_before_create_process.connect
def freeze_heap(**_) -> None:
    """Keep the parent's heap shared with the child about to fork."""
    gc.collect()
    gc.freeze()


@worker_process_init.connect
def on_process_init(**_) -> None:
    """Drop pooled sockets inherited from the parent."""
    from app import ai_ledger  # noqa: PLC0415
    from app.database import engine  # noqa: PLC0415

    try:
        release_sockets_to(settings.REDIS_PORT)
    except OSError:
        logger.warning("inherited broker sockets not released", exc_info=True)
    engine.dispose(close=False)
    ai_ledger.install()


@worker_ready.connect
def on_worker_ready(sender, **kwargs) -> None:  # noqa: ARG001
    """Log when worker is ready."""
    logger.info("Worker ready: %s", sender.hostname)
    from shared.services import worker_presence as presence  # noqa: PLC0415

    _heartbeat(sender)
    sender.timer.call_repeatedly(HEARTBEAT_SECONDS, _heartbeat, (sender,))
    consumed = celery_app.amqp.queues.consume_from
    if consumed.keys() & set(SCAN_QUEUES):
        presence.announce(sender.hostname)
        sender.timer.call_repeatedly(
            presence.ANNOUNCE_SECONDS, presence.announce, (sender.hostname,)
        )
    if DEFAULT_QUEUE not in consumed:
        return
    _warm_library()
    _warm_threat_intel()
    _warm_ip_ranges()
    _warm_ai_prices()


def _consuming(consumer) -> bool:
    """Whether the worker and its consumer are both running."""
    return (
        consumer.blueprint.state == bootsteps.RUN
        and consumer.controller.blueprint.state == bootsteps.RUN
    )


_stopped_at: float | None = None


def _exit_once_stopped() -> None:
    """End a worker that left the running state and is still up after the grace."""
    global _stopped_at  # noqa: PLW0603
    now = time.monotonic()
    if _stopped_at is None:
        _stopped_at = now
        return
    if now - _stopped_at < STOPPED_GRACE_SECONDS:
        return
    logger.critical("worker stopped consuming and did not exit, exiting now")
    os._exit(EX_FAILURE)


def _heartbeat(consumer) -> None:
    """Touch the heartbeat file while the worker consumes and the broker answers."""
    global _stopped_at  # noqa: PLW0603
    from shared.services import worker_presence as presence  # noqa: PLC0415

    # the timer fires through a warm shutdown too
    if not _consuming(consumer):
        _exit_once_stopped()
        return
    _stopped_at = None
    if not presence.broker_answers():
        logger.warning("broker did not answer, heartbeat not written")
        return
    try:
        Path(HEARTBEAT_PATH).touch()
    except OSError:
        logger.warning("heartbeat file not written", exc_info=True)


def _warm_ai_prices() -> None:
    """Share the stored model price list, or load it on first boot."""
    try:
        from app.database import get_sync_session  # noqa: PLC0415
        from shared.definitions.datasets import DatasetKind  # noqa: PLC0415
        from shared.services.ai import prices  # noqa: PLC0415

        with get_sync_session() as session:
            if prices.share(session):
                return
        celery_app.send_task(
            "app.tasks.daily.run", kwargs={"jobs": [DatasetKind.AI_PRICES.value]}
        )
        logger.info("model price list empty, load dispatched")
    except Exception:
        logger.warning("model price list warm-up could not be scheduled", exc_info=True)


def _warm_library() -> None:
    """Load the check library on first boot."""
    try:
        from app.database import get_sync_session  # noqa: PLC0415
        from shared.services.vuln_templates import library_ready  # noqa: PLC0415

        with get_sync_session() as session:
            if library_ready(session):
                return
        celery_app.send_task("app.tasks.vuln_templates.sync")
        logger.info("check library empty, sync dispatched")
    except Exception:
        logger.warning("check library warm-up could not be scheduled", exc_info=True)


def _warm_ip_ranges() -> None:
    """Pre-load the IP -> ASN/country tables."""
    try:
        from app.database import get_sync_session  # noqa: PLC0415
        from shared.services.ip_asn import ranges_ready  # noqa: PLC0415

        with get_sync_session() as session:
            if ranges_ready(session):
                return
        celery_app.send_task("app.tasks.ip_asn.refresh")
        logger.info("ip range tables empty, refresh dispatched")
    except Exception:
        logger.warning("ip range warm-up could not be scheduled", exc_info=True)


def _warm_threat_intel() -> None:
    """Pull every empty feed on boot."""
    try:
        from app.database import get_sync_session  # noqa: PLC0415
        from shared.services.threat_intel import (  # noqa: PLC0415
            auto_sync_enabled,
            missing_feeds,
        )

        with get_sync_session() as session:
            if not auto_sync_enabled(session):
                return
            missing = missing_feeds(session)
        if not missing:
            return
        celery_app.send_task(
            "app.tasks.threat_intel.refresh", kwargs={"feeds": missing}
        )
        logger.info("threat feeds empty, refresh dispatched", feeds=missing)
    except Exception:
        logger.warning("threat intel warm-up could not be scheduled", exc_info=True)


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs) -> None:  # noqa: ARG001
    """Log when worker shuts down."""
    logger.info("Worker shutting down: %s", sender.hostname)
    from shared.services import worker_presence as presence  # noqa: PLC0415

    presence.withdraw(sender.hostname)


@task_prerun.connect
def on_task_prerun(task_id: str, task, args, kwargs, **_) -> None:  # noqa: ARG001
    """Log task start."""
    logger.info("Task started: %s[%s]", task.name, task_id)


@task_postrun.connect
def on_task_postrun(task_id: str, task, retval, state, **_) -> None:  # noqa: ARG001
    """Log task completion."""
    logger.info("Task completed: %s[%s] -> %s", task.name, task_id, state)


@task_failure.connect
def on_task_failure(task_id: str, exception, **_) -> None:
    """Log task failure."""
    logger.exception("Task failed: %s - %s", task_id, str(exception))
