"""Render the stage execution plan as a celery canvas."""

from celery import chain, chord, group, signature

from app.celery import celery_app
from shared.definitions.constants import SCANS_QUEUE
from stages.registry import StagePlan, execution_plan


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


def _parallel(parts: list):
    return parts[0] if len(parts) == 1 else group(parts, app=celery_app)


def _render(scan_id: str, plan: StagePlan):
    """`gating` in front of `then`, `beside` alongside it."""
    tail = None if plan.then is None else _render(scan_id, plan.then)
    gating = [_stage_sig(scan_id, name) for name in plan.gating]
    beside = [_stage_sig(scan_id, name) for name in plan.beside]

    if tail is None:
        return _parallel(gating + beside)
    head = _parallel(gating) if gating else None
    if head is None:
        spine = tail
    elif isinstance(head, group):
        spine = chord(head, tail, app=celery_app)
    else:
        spine = chain(head, tail, app=celery_app)
    return spine if not beside else _parallel([spine, *beside])


def build_canvas(scan_id: str, start_level: int = 0, done: set[str] | None = None):
    """Nest levels innermost-first — a flat chain of groups lets celery merge and double-apply one."""
    # every node carries the configured app: an unbound signature resolves to whatever
    # `current_app` happens to be, and a backend-less one cannot start a chord
    plan = execution_plan(start_level, frozenset(done or ()))
    finalize = _finalize_sig(scan_id)
    if plan is None:
        return finalize
    body = _render(scan_id, plan)
    if isinstance(body, group):
        return chord(body, finalize, app=celery_app)
    return chain(body, finalize, app=celery_app)
