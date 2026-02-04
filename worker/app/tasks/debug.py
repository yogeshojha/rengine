
from celery import shared_task

from shared.logging import get_logger

logger = get_logger("rengine.worker.tasks.debug")


@shared_task(
    bind=True,
    name="app.tasks.debug.debug_task",
    queue="default",
)
def debug_task(self, message: str = "Hello from Worker!") -> dict:
    """Simple debug task to verify Celery is working.
    """
    logger.info("Debug task executed: %s", message)
    logger.info("Task ID: %s", self.request.id)
    logger.info("Worker: %s", self.request.hostname)

    return {
        "status": "success",
        "message": message,
        "task_id": self.request.id,
        "worker": self.request.hostname,
    }
