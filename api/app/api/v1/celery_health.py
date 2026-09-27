import asyncio
from collections import Counter

from fastapi import APIRouter

from app.api.deps import CurrentSuperuser
from shared.definitions.workers import QUEUES
from shared.logging import get_logger
from shared.models.dataset import QueueHealth, QueueRead
from shared.services.celery_dispatch import get_celery_client

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

INSPECT_TIMEOUT = 1.0


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


def _collect_worker_health() -> dict:
    inspect = get_celery_client().control.inspect(timeout=INSPECT_TIMEOUT)

    ping_response = inspect.ping() or {}
    active_queues = inspect.active_queues() or {}
    stats = inspect.stats() or {}

    workers = {}
    for worker_name, pong in ping_response.items():
        queues = active_queues.get(worker_name, [])
        worker_stats = stats.get(worker_name, {})

        workers[worker_name] = {
            "status": "online" if pong.get("ok") == "pong" else "unhealthy",
            "queues": [q["name"] for q in queues],
            "concurrency": worker_stats.get("pool", {}).get("max-concurrency"),
            "processed": worker_stats.get("total", {}).get("tasks.total", 0),
        }

    online_count = sum(1 for w in workers.values() if w["status"] == "online")

    return {
        "status": "healthy" if online_count > 0 else "unhealthy",
        "workers_online": online_count,
        "workers_total": len(workers),
        "workers": workers,
    }


@router.get("/celery")
async def celery_health_check(_current_user: CurrentSuperuser) -> dict:
    try:
        return await asyncio.to_thread(_collect_worker_health)
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Celery workers did not respond. Check that the worker services are running.",
        }


def _collect_active_tasks() -> dict:
    inspect = get_celery_client().control.inspect(timeout=INSPECT_TIMEOUT)

    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    scheduled = inspect.scheduled() or {}

    return {
        "status": "healthy",
        "active": {
            worker: [
                {
                    "id": task["id"],
                    "name": task["name"],
                    "args": task.get("args", []),
                }
                for task in tasks
            ]
            for worker, tasks in active.items()
        },
        "reserved": {worker: len(tasks) for worker, tasks in reserved.items()},
        "scheduled": {worker: len(tasks) for worker, tasks in scheduled.items()},
    }


@router.get("/celery/tasks")
async def celery_active_tasks(_current_user: CurrentSuperuser) -> dict:
    try:
        return await asyncio.to_thread(_collect_active_tasks)
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def _queue_health(replies: dict | None) -> QueueHealth:
    consumers: Counter[str] = Counter()
    for queues in (replies or {}).values():
        consumers.update({queue["name"] for queue in queues})
    return QueueHealth(
        responded=bool(replies),
        queues=[
            QueueRead(
                name=spec.name,
                label=spec.label,
                service=spec.service,
                workers=consumers[spec.name],
            )
            for spec in QUEUES
        ],
    )


def _collect_queues() -> QueueHealth:
    inspect = get_celery_client().control.inspect(timeout=INSPECT_TIMEOUT)
    return _queue_health(inspect.active_queues())


@router.get("/queues", response_model=QueueHealth)
async def queue_health(_current_user: CurrentSuperuser) -> QueueHealth:
    """Workers consuming each queue."""
    try:
        return await asyncio.to_thread(_collect_queues)
    except Exception:
        logger.warning("worker inspect failed", exc_info=True)
        return _queue_health(None)
