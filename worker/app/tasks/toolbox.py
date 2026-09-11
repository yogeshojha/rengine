"""Toolbox runs that shell out to a tool binary."""

import uuid

from celery import shared_task

from app.database import get_sync_session
from shared.logging import get_logger
from toolbox import registry, store
from toolbox.base import ToolContext, ToolError
from toolbox.runner import complete, fail, validate

logger = get_logger(__name__)

SOFT_TIME_LIMIT = 300
HARD_TIME_LIMIT = 360


@shared_task(
    name="app.tasks.toolbox.run",
    soft_time_limit=SOFT_TIME_LIMIT,
    time_limit=HARD_TIME_LIMIT,
    max_retries=0,
)
def run(
    run_id: str,
    user_id: str,
    tool: str,
    payload: dict,
    project_id: str | None = None,
) -> dict:
    record = store.mark_running(user_id, run_id)
    if record is None:
        logger.info("toolbox run gone before it started", run_id=run_id)
        return {"run_id": run_id, "status": "gone"}

    spec = registry.get(tool)
    if spec is None:
        store.save_sync(user_id, fail(record, f"No tool called {tool!r}."))
        return {"run_id": run_id, "status": record.status}

    with get_sync_session() as session:
        ctx = ToolContext(
            session=session,
            user_id=uuid.UUID(user_id),
            project_id=uuid.UUID(project_id) if project_id else None,
        )
        try:
            complete(record, spec.tool_cls().run(ctx, validate(spec, payload)))
        except ToolError as exc:
            fail(record, str(exc))
        except Exception as exc:
            logger.warning("toolbox run failed", tool=tool, error=str(exc))
            fail(record, f"The run failed: {exc}")

    store.save_sync(user_id, record)
    return {"run_id": run_id, "status": record.status}
