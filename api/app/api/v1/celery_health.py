import asyncio
from collections import Counter

from fastapi import APIRouter

from app.api.deps import CurrentSuperuser
from shared.definitions.workers import INSPECT_TIMEOUT, QUEUES
from shared.logging import get_logger
from shared.models.dataset import QueueHealth, QueueRead
from shared.services.celery_dispatch import get_celery_client

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


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
