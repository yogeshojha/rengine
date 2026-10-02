"""Render the stage execution plan as a celery canvas, one step at a time."""

from celery import Celery, chain, chord, group, signature

from shared.definitions.constants import SCAN_CONTROL_QUEUE, SCANS_QUEUE
from stages.registry import execution_plan

Steps = list[list[str]]

STAGE_TASK = "app.tasks.scan.run_scan_stage"
STEP_TASK = "app.tasks.scan.run_scan_step"
FINALIZE_TASK = "app.tasks.scan.finalize_scan"


def _sig(app: Celery, task: str, queue: str = SCAN_CONTROL_QUEUE, **kwargs):
    return signature(task, kwargs=kwargs, queue=queue, immutable=True, app=app)


def _stage_sig(app: Celery, scan_id: str, stage_name: str, epoch: int):
    sig = _sig(
        app,
        STAGE_TASK,
        queue=SCANS_QUEUE,
        scan_id=scan_id,
        stage_name=stage_name,
        epoch=epoch,
    )
    sig.options["link_error"] = [_finalize_sig(app, scan_id, epoch)]
    return sig


def _finalize_sig(app: Celery, scan_id: str, epoch: int):
    return _sig(app, FINALIZE_TASK, scan_id=scan_id, epoch=epoch)


def _step_sig(app: Celery, scan_id: str, epoch: int, steps: Steps, index: int):
    return _sig(app, STEP_TASK, scan_id=scan_id, epoch=epoch, steps=steps, index=index)


def plan_steps(start_level: int = 0, done: set[str] | None = None) -> Steps:
    """The steps a canvas runs, as plain lists so a task can carry them."""
    return [
        list(step)
        for step in execution_plan(start_level, frozenset(done or ()))
        if step
    ]


def build_step(app: Celery, scan_id: str, epoch: int, steps: Steps, index: int):
    """One step's stages, then the dispatch of the next step or finalize."""
    if index >= len(steps):
        return _finalize_sig(app, scan_id, epoch)
    after = (
        _step_sig(app, scan_id, epoch, steps, index + 1)
        if index + 1 < len(steps)
        else _finalize_sig(app, scan_id, epoch)
    )
    sigs = [_stage_sig(app, scan_id, name, epoch) for name in steps[index]]
    if len(sigs) == 1:
        return chain(sigs[0], after, app=app)
    return chord(group(sigs, app=app), after, app=app)


def build_canvas(
    app: Celery,
    scan_id: str,
    epoch: int,
    start_level: int = 0,
    done: set[str] | None = None,
):
    """The first step of the plan; each step dispatches the next when it settles."""
    return build_step(app, scan_id, epoch, plan_steps(start_level, done), 0)
