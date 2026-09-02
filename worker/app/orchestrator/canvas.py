"""Build the celery canvas (parallel group per level, chained, + finalize) for a scan."""

from celery import chain, chord, group, signature

from shared.definitions.constants import SCANS_QUEUE
from stages.registry import ordered_levels


def _stage_sig(scan_id: str, stage_name: str):
    sig = signature(
        "app.tasks.scan.run_scan_stage",
        kwargs={"scan_id": scan_id, "stage_name": stage_name},
        queue=SCANS_QUEUE,
        immutable=True,
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
    )


def build_canvas(scan_id: str):
    """Nest levels as chords innermost-first — a flat chain of groups lets celery merge and double-apply one."""
    workflow = _finalize_sig(scan_id)
    for level in reversed(ordered_levels()):
        stage_sigs = [_stage_sig(scan_id, spec.name) for spec in level]
        workflow = (
            chain(stage_sigs[0], workflow)
            if len(stage_sigs) == 1
            else chord(group(stage_sigs), workflow)
        )
    return workflow
