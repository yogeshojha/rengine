"""The one place a tool result becomes a stored run."""

from __future__ import annotations

from datetime import datetime

from pydantic import ValidationError

from shared.definitions.toolbox import Block, BlockKind, RunStatus, ToolRunRead
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control
from toolbox.base import ToolError, ToolInput, ToolOutcome
from toolbox.registry import ToolSpec

MAX_ERROR_LENGTH = 400
QUEUE_DEADLINE_SECONDS = 120
RUN_DEADLINE_SECONDS = 420


def validate(spec: ToolSpec, payload: dict) -> ToolInput:
    try:
        return spec.tool_cls.Input.model_validate(payload)
    except ValidationError as exc:
        raise ToolError(_readable(exc)) from exc


def _readable(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:3]:
        field = ".".join(str(p) for p in error.get("loc", ()) if p != "body")
        message = error.get("msg", "is invalid")
        parts.append(f"{field}: {message}" if field else message)
    return "; ".join(parts) or "The input is not valid."


def _elapsed(run: ToolRunRead) -> int:
    start = run.started_at or run.queued_at
    try:
        began = datetime.fromisoformat(start)
    except (TypeError, ValueError):
        return 0
    return max(0, int((utc_now() - began).total_seconds() * 1000))


_SELF_CARRYING = frozenset({BlockKind.HERO.value, BlockKind.IMAGE.value})


def _worth_showing(block: Block) -> bool:
    """An empty block with no empty-state text is not rendered."""
    if block.kind in _SELF_CARRYING:
        return bool(block.headline or block.src)
    if block.facts or block.rows or block.tags or block.text:
        return True
    return bool(block.empty)


def _age(stamp: str | None) -> float:
    try:
        return (utc_now() - datetime.fromisoformat(stamp or "")).total_seconds()
    except (TypeError, ValueError):
        return 0.0


def expire(run: ToolRunRead) -> ToolRunRead:
    """A run past its deadline is recorded as failed rather than left pending."""
    if (
        run.status == RunStatus.QUEUED.value
        and _age(run.queued_at) > QUEUE_DEADLINE_SECONDS
    ):
        return fail(run, "No worker accepted this run.")
    if (
        run.status == RunStatus.RUNNING.value
        and _age(run.started_at) > RUN_DEADLINE_SECONDS
    ):
        return fail(run, "The worker stopped reporting on this run.")
    return run


def complete(run: ToolRunRead, outcome: ToolOutcome) -> ToolRunRead:
    run.status = RunStatus.COMPLETED.value
    run.summary = outcome.summary
    run.blocks = [b for b in outcome.blocks if _worth_showing(b)]
    run.caveats = outcome.caveats
    run.pivot = outcome.pivot
    run.raw = outcome.raw
    run.finished_at = utc_now().isoformat()
    run.duration_ms = _elapsed(run)
    return run


def fail(run: ToolRunRead, message: str) -> ToolRunRead:
    run.status = RunStatus.FAILED.value
    run.error = strip_control(str(message))[:MAX_ERROR_LENGTH] or "The run failed."
    run.finished_at = utc_now().isoformat()
    run.duration_ms = _elapsed(run)
    return run
