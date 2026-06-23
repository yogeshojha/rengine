"""Build the celery canvas (parallel group per level, chained, + finalize) for a scan."""

from celery import chain, group, signature

from engines.registry import ordered_levels
from shared.definitions.constants import SCANS_QUEUE


def _stage_sig(scan_id: str, stage_name: str):
    return signature(
        "app.tasks.scan.run_scan_stage",
        kwargs={"scan_id": scan_id, "stage_name": stage_name},
        queue=SCANS_QUEUE,
        immutable=True,
    )


def _finalize_sig(scan_id: str):
    return signature(
        "app.tasks.scan.finalize_scan",
        kwargs={"scan_id": scan_id},
        queue=SCANS_QUEUE,
        immutable=True,
    )


def build_canvas(scan_id: str):
    level_sigs = []
    for level in ordered_levels():
        stage_sigs = [_stage_sig(scan_id, spec.name) for spec in level]
        level_sigs.append(stage_sigs[0] if len(stage_sigs) == 1 else group(stage_sigs))

    finalize = _finalize_sig(scan_id)
    workflow = chain(*level_sigs, finalize)
    workflow.options["link_error"] = [_finalize_sig(scan_id)]
    return workflow
