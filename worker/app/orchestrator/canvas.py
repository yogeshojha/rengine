"""Build the celery canvas (parallel group per level, chained, + finalize) for a scan."""

from celery import chain, chord, group, signature

from app.celery import celery_app
from shared.definitions.constants import SCANS_QUEUE
from stages.registry import ordered_levels


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


def build_canvas(scan_id: str):
    """Nest levels as chords innermost-first — a flat chain of groups lets celery merge and double-apply one."""
    # every node carries the configured app: an unbound signature resolves to whatever
    # `current_app` happens to be, and a backend-less one cannot start a chord
    workflow = _finalize_sig(scan_id)
    for level in reversed(ordered_levels()):
        stage_sigs = [_stage_sig(scan_id, spec.name) for spec in level]
        workflow = (
            chain(stage_sigs[0], workflow, app=celery_app)
            if len(stage_sigs) == 1
            else chord(group(stage_sigs, app=celery_app), workflow, app=celery_app)
        )
    return workflow
