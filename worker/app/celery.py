from celery import Celery
from celery.signals import (
    setup_logging,
    task_failure,
    task_postrun,
    task_prerun,
    worker_ready,
    worker_shutdown,
)
from kombu import Exchange, Queue

from app.config import settings
from shared.definitions.constants import SCANS_QUEUE
from shared.logging import get_logger
from shared.logging import setup_logging as setup_rengine_logging

logger = get_logger(__name__)

celery_app = Celery("rengine")

# #############################################################
# Celery Configuration
# #############################################################

# redis re-delivers a task still unacked after visibility_timeout — at celery's 1h
# default a stage that runs longer is dispatched a second time and the whole rest of
# the scan runs twice, so it must sit above the hard time limit, not below it.
_VISIBILITY_TIMEOUT = settings.TASK_HARD_TIME_LIMIT + 3600

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
    result_expires=3600,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.TASK_HARD_TIME_LIMIT,
    worker_send_task_events=True,
    worker_max_tasks_per_child=100,
    worker_pool="prefork",
    worker_hijack_root_logger=False,
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule_filename="/tmp/celerybeat-schedule",  # noqa: S108
)

# #############################################################
# Queue Definitions
# #############################################################

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
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# #############################################################
# Task Routing
# #############################################################

celery_app.conf.task_routes = {
    "app.tasks.scan.*": {"queue": SCANS_QUEUE},
    "app.tasks.whois.*": {"queue": "default"},
    "app.tasks.debug.*": {"queue": "default"},
    "app.tasks.ripestat.*": {"queue": "default"},
    "app.tasks.dns.*": {"queue": "default"},
    "app.tasks.schedule.*": {"queue": "default"},
    "app.tasks.vuln_templates.*": {"queue": "default"},
    "app.tasks.endpoints.*": {"queue": "default"},
}

# #############################################################
# Auto-discover Tasks
# #############################################################

celery_app.autodiscover_tasks(
    [
        "app.tasks.debug",
        "app.tasks.whois",
        "app.tasks.ripestat",
        "app.tasks.dns",
        "app.tasks.scan",
        "app.tasks.schedule",
        "app.tasks.ip_asn",
        "app.tasks.vuln_templates",
        "app.tasks.endpoints",
    ]
)

# #############################################################
# Beat Schedule (Periodic Tasks)
# #############################################################

SCHEDULE_TICK_SECONDS = 60.0
IP_RANGE_REFRESH_SECONDS = 7 * 24 * 60 * 60.0
TEMPLATE_SYNC_SECONDS = 24 * 60 * 60.0

celery_app.conf.beat_schedule = {
    "scan-schedule-tick": {
        "task": "app.tasks.schedule.tick",
        "schedule": SCHEDULE_TICK_SECONDS,
    },
    "ip-range-refresh": {
        "task": "app.tasks.ip_asn.refresh",
        "schedule": IP_RANGE_REFRESH_SECONDS,
    },
    "vuln-template-sync": {
        "task": "app.tasks.vuln_templates.sync",
        "schedule": TEMPLATE_SYNC_SECONDS,
    },
}


# #############################################################
# Signal Handlers
# #############################################################


@setup_logging.connect
def configure_logging(loglevel: int, **kwargs) -> None:  # noqa: ARG001
    """Configure logging for Celery workers."""
    setup_rengine_logging(
        name="rengine.worker",
        level=settings.LOG_LEVEL,
        colored=True,
    )


@worker_ready.connect
def on_worker_ready(sender, **kwargs) -> None:  # noqa: ARG001
    """Log when worker is ready."""
    logger.info(
        "Worker ready: %s (concurrency: %s)",
        sender.hostname,
        sender.concurrency,
    )
    _warm_ip_ranges()


def _warm_ip_ranges() -> None:
    """Pre-load the IP -> ASN/country tables so the first scan never waits on the download."""
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


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs) -> None:  # noqa: ARG001
    """Log when worker shuts down."""
    logger.info("Worker shutting down: %s", sender.hostname)


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


# #############################################################
# Debug Health Check Task
# #############################################################


@celery_app.task(bind=True, name="celery.ping")
def ping(self) -> str:  # noqa: ARG001
    """Debug health check task."""
    return "pong"
