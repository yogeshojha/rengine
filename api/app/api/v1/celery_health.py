from celery import Celery
from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/celery")
async def celery_health_check() -> dict:
    celery_client = Celery(broker=settings.celery_broker_url)
    inspect = celery_client.control.inspect()

    try:
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

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Could not connect to Celery workers",
        }


@router.get("/celery/tasks")
async def celery_active_tasks() -> dict:
    celery_client = Celery(broker=settings.celery_broker_url)
    inspect = celery_client.control.inspect()

    try:
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
            "reserved": {
                worker: len(tasks) for worker, tasks in reserved.items()
            },
            "scheduled": {
                worker: len(tasks) for worker, tasks in scheduled.items()
            },
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
