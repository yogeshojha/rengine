"""Render the stage execution plan as a celery canvas."""

from celery import chain, chord, group, signature

from app.celery import celery_app
from shared.definitions.constants import SCANS_QUEUE
from stages.registry import execution_plan


def _stage_sig(scan_id: str, stage_name: str):
    sig = signature(
        "app.tasks.scan.run_scan_stage",
        kwargs={"scan_id": scan_id, "stage_name": stage_name},
        queue=SCANS_QUEUE,
        immutable=True,
        app=celery_app,
    )
    # celery rejects an errback on a group, so every stage carries its own
    sig.options["link_error"] = [_finalize_sig(scan_id)]
    return sig


def _finalize_sig(scan_id: str):
    return signature(
        "app.tasks.scan.finalize_scan",
        kwargs={"scan_id": scan_id},
        queue=SCANS_QUEUE,
        immutable=True,
        app=celery_app,
    )


def build_canvas(scan_id: str, start_level: int = 0, done: set[str] | None = None):
    """Nest the steps innermost-first — a flat chain of groups lets celery merge and
    double-apply one, and a chord inside a chord's header never fires its body, so every
    header here stays a plain group of stage signatures."""
    # every node carries the configured app: an unbound signature resolves to whatever
    # `current_app` happens to be, and a backend-less one cannot start a chord
    workflow = _finalize_sig(scan_id)
    for step in reversed(execution_plan(start_level, frozenset(done or ()))):
        sigs = [_stage_sig(scan_id, name) for name in step]
        workflow = (
            chain(sigs[0], workflow, app=celery_app)
            if len(sigs) == 1
            else chord(group(sigs, app=celery_app), workflow, app=celery_app)
        )
    return workflow
