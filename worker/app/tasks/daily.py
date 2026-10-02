"""Once-a-day jobs, run in order."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from celery import shared_task

from shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DailyJob:
    name: str
    run: Callable[[], dict]


def _library() -> dict:
    from app.tasks.vuln_templates import sync  # noqa: PLC0415

    return sync()


def _new_checks() -> dict:
    from app.tasks.new_checks import sweep  # noqa: PLC0415

    return sweep()


# library first
DAILY_JOBS: tuple[DailyJob, ...] = (
    DailyJob("library", _library),
    DailyJob("new_checks", _new_checks),
)

DAILY_JOB_NAMES: tuple[str, ...] = tuple(job.name for job in DAILY_JOBS)


@shared_task(name="app.tasks.daily.run")
def run(jobs: list[str] | None = None) -> dict:
    wanted = set(jobs) if jobs else set(DAILY_JOB_NAMES)
    out: dict[str, dict] = {}
    for job in DAILY_JOBS:
        if job.name not in wanted:
            continue
        try:
            out[job.name] = job.run()
        except Exception:
            logger.warning("daily job failed", job=job.name, exc_info=True)
            out[job.name] = {"failed": True}
        else:
            logger.info("daily job finished", job=job.name, **out[job.name])
    return out
