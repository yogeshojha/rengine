from celery import Celery
from celery.signals import (
    setup_logging,
    task_failure,
    task_postrun,
    task_prerun,
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
from shared.logging import get_logger
from shared.logging import setup_logging as setup_rengine_logging

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
    beat_schedule_filename="/tmp/celerybeat-schedule",  # noqa: S108
)


default_exchange = Exchange("default", type="direct")
scan_exchange = Exchange("scans", type="direct")

celery_app.conf.task_queues = (
    Queue(
        "critical",
        exchange=default_exchange,
        routing_key="critical",
        queue_arguments={"x-max-priority": 10},
    ),
    Queue(
        "default",
        exchange=default_exchange,
        routing_key="default",
        queue_arguments={"x-max-priority": 5},
    ),
    Queue(
        SCANS_QUEUE,
        exchange=scan_exchange,
        routing_key="scans",
        queue_arguments={"x-max-priority": 5},
    ),
    Queue(
        SCAN_CONTROL_QUEUE,
        exchange=Exchange(SCAN_CONTROL_QUEUE, type="direct"),
        routing_key=SCAN_CONTROL_QUEUE,
    ),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"


celery_app.conf.task_routes = {
    "app.tasks.scan.reap_stalled": {"queue": DEFAULT_QUEUE},
    "app.tasks.scan.run_scan_stage": {"queue": SCANS_QUEUE},
    "app.tasks.scan.*": {"queue": SCAN_CONTROL_QUEUE},
    "app.tasks.whois.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.ripestat.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.dns.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.schedule.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.vuln_templates.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.daily.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.new_checks.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.endpoints.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.reports.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.export.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.interest.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.threat_intel.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.freshness.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.hygiene.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.screenshots.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.software.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.secrets.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.scan_deltas.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.bounty_programs.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.estate.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.issue_trackers.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.tripwires.*": {"queue": DEFAULT_QUEUE},
    "app.tasks.toolbox.*": {"queue": CRITICAL_QUEUE},
}


celery_app.autodiscover_tasks(
    [
        "app.tasks.whois",
        "app.tasks.ripestat",
        "app.tasks.dns",
        "app.tasks.scan",
        "app.tasks.schedule",
        "app.tasks.ip_asn",
        "app.tasks.vuln_templates",
        "app.tasks.daily",
        "app.tasks.new_checks",
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
    },
    "export-cleanup": {
        "task": "app.tasks.export.cleanup",
        "schedule": EXPORT_CLEANUP_SECONDS,
    },
    "export-reap": {
        "task": "app.tasks.export.reap",
        "schedule": EXPORT_REAP_SECONDS,
        "options": {"expires": EXPORT_REAP_SECONDS},
    },
    "notification-cleanup": {
        "task": "app.tasks.notifications.cleanup",
        "schedule": NOTIFICATION_CLEANUP_SECONDS,
    },
    "retention-enforce": {
        "task": "app.tasks.retention.enforce",
        "schedule": RETENTION_SECONDS,
    },
    "threat-intel-refresh": {
        "task": "app.tasks.threat_intel.refresh",
        "schedule": THREAT_INTEL_REFRESH_SECONDS,
    },
    "certificate-recheck": {
        "task": "app.tasks.freshness.certificates",
        "schedule": CERT_RECHECK_SECONDS,
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
    setup_rengine_logging(name="", level=settings.LOG_LEVEL, colored=True)


@worker_process_init.connect
def on_process_init(**_) -> None:
    """Drop pooled sockets inherited from the parent."""
    from app.database import engine  # noqa: PLC0415

    engine.dispose(close=False)


@worker_ready.connect
def on_worker_ready(sender, **kwargs) -> None:  # noqa: ARG001
    """Log when worker is ready."""
    logger.info("Worker ready: %s", sender.hostname)
    consumed = celery_app.amqp.queues.consume_from
    if consumed.keys() & set(SCAN_QUEUES):
        from shared.services import worker_presence as presence  # noqa: PLC0415

        presence.announce(sender.hostname)
        sender.timer.call_repeatedly(
            presence.ANNOUNCE_SECONDS, presence.announce, (sender.hostname,)
        )
    if DEFAULT_QUEUE not in consumed:
        return
    _warm_library()
    _warm_threat_intel()
    _warm_ip_ranges()


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


@celery_app.task(bind=True, name="celery.ping")
def ping(self) -> str:  # noqa: ARG001
    """Debug health check task."""
    return "pong"
