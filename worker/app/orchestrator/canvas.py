"""Render the stage execution plan as a celery canvas."""

from collections.abc import Iterable

from celery import chain, chord, group, signature

from app.celery import celery_app
from shared.definitions.constants import SCANS_QUEUE
from shared.models.scan_activity import ScanActivity
from shared.services.orchestrator import stages_done
from stages.registry import execution_plan, resume_level


def _stage_sig(scan_id: str, stage_name: str, epoch: int):
    sig = signature(
        "app.tasks.scan.run_scan_stage",
        kwargs={"scan_id": scan_id, "stage_name": stage_name, "epoch": epoch},
        queue=SCANS_QUEUE,
        immutable=True,
        app=celery_app,
    )
    sig.options["link_error"] = [_finalize_sig(scan_id, epoch)]
    return sig


def _finalize_sig(scan_id: str, epoch: int):
    return signature(
        "app.tasks.scan.finalize_scan",
        kwargs={"scan_id": scan_id, "epoch": epoch},
        queue=SCANS_QUEUE,
        immutable=True,
        app=celery_app,
    )


def build_canvas(
    scan_id: str, epoch: int = 0, start_level: int = 0, done: set[str] | None = None
):
    """Nest the steps innermost-first."""
    workflow = _finalize_sig(scan_id, epoch)
    for step in reversed(execution_plan(start_level, frozenset(done or ()))):
        sigs = [_stage_sig(scan_id, name, epoch) for name in step]
        workflow = (
            chain(sigs[0], workflow, app=celery_app)
            if len(sigs) == 1
            else chord(group(sigs, app=celery_app), workflow, app=celery_app)
        )
    return workflow


def resume_point(activities: Iterable[ScanActivity]) -> tuple[int, set[str]]:
    """The level a resumed canvas starts at, and the stages it does not run again."""
    done = stages_done(activities)
    return resume_level(frozenset(done)), done
