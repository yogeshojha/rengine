"""What a tripwire does with the rows that fired."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from shared.config import BaseAppSettings
from shared.definitions.notifications import (
    FiredRowLike,
    TripwireFired,
    TripwireRescan,
    TripwireRunResult,
    tripwire_fired,
    tripwire_run_result,
)
from shared.definitions.rescan import (
    ASSET_SEED_STAGE,
    MAX_RUN_ASSETS,
    RESCANNABLE_STAGES,
    stages_for,
)
from shared.definitions.surface import SURFACE_NOUN
from shared.definitions.tripwires import (
    MAX_RUNS_PER_DAY,
    TRIPWIRE_KEY,
    ActionKind,
    OutcomeStatus,
    run_label,
)
from shared.definitions.vulnerabilities import ACTIONABLE_SEVERITIES
from shared.enums.scan import ScanStatus
from shared.logging import get_logger
from shared.models.notification_channel import NotificationChannel
from shared.models.scan import Scan
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.target import Target
from shared.models.tripwire import (
    FiredRow,
    Outcome,
    ScanAction,
    Tripwire,
    TripwireAction,
    TripwireRun,
)
from shared.models.vulnerability import Vulnerability
from shared.services.celery_dispatch import dispatch_scan_run
from shared.services.focused import focused_overrides
from shared.services.launch_plan import AdHocEngine
from shared.services.notification_sync import SyncNotificationPublisher
from shared.services.proxy_resolve import scan_proxy_url
from shared.services.scan_factory import build_scan_row
from shared.services.scan_resolve import merge_engine_context
from shared.services.tripwires.identity import identity, seed_kind_of
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

NOT_QUEUED = "Run not queued. Check that the worker is running."
DAILY_LIMIT = f"Daily limit of {MAX_RUNS_PER_DAY} runs reached."
NO_SEEDS = "No host or address to scan."
NO_STAGES = "No stage to run."
PASSIVE = "Every chosen stage is off at passive intensity."


def parse_actions(raw: list) -> list[TripwireAction]:
    from pydantic import TypeAdapter  # noqa: PLC0415

    adapter = TypeAdapter(list[TripwireAction])
    return adapter.validate_python(raw or [])


def _target_value(scan: Scan) -> str:
    return (scan.execution_config or {}).get("target_value", "")


# ---------- notify ----------


def live_channels(session: Session, chosen: list) -> list[uuid.UUID]:
    """The chosen channels that still exist; type routing when none were chosen."""
    ids = [uuid.UUID(str(c)) for c in (chosen or [])]
    if not ids:
        return []
    return list(
        session.scalars(
            select(NotificationChannel.id).where(
                NotificationChannel.id.in_(ids),
                NotificationChannel.is_active.is_(True),
            )
        )
    )


def notify(
    session: Session,
    tripwire: Tripwire,
    run: TripwireRun,
    scan: Scan,
    rows: list[FiredRow],
    channel_ids: list,
    *,
    live: bool = False,
    fired: int | None = None,
    rescan: TripwireRescan | None = None,
) -> Outcome:
    from shared.services import notifier  # noqa: PLC0415

    payload = tripwire_fired(
        TripwireFired(
            name=tripwire.name,
            target=_target_value(scan),
            dimension=tripwire.dimension,
            fire_on=tripwire.fire_on,
            fired=len(rows) if fired is None else fired,
            rows=[FiredRowLike(r.label, r.detail, r.severity) for r in rows],
            run_id=str(run.id),
            scan_id=str(scan.id),
            live=live,
            rescan=rescan,
        )
    )
    channels = live_channels(session, channel_ids)
    try:
        SyncNotificationPublisher(BaseAppSettings().redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=scan.project_id,
            dispatch=False,
        )
    except Exception:
        logger.warning("tripwire notification failed", exc_info=True)
        return Outcome(
            kind=ActionKind.NOTIFY.value,
            status=OutcomeStatus.FAILED.value,
            detail="Notification not recorded.",
        )
    try:
        sent = notifier.dispatch_sync(
            session,
            payload["type"],
            payload["severity"],
            payload["title"],
            payload["message"],
            channel_ids=channels,
            metadata=payload.get("metadata"),
        )
    except Exception:
        logger.warning("tripwire channel dispatch failed", exc_info=True)
        sent = [(cid, False, "The message was not sent.") for cid in channels]
    return delivery_outcome(session, sent, chosen=bool(channels))


def delivery_outcome(session: Session, sent: list[tuple], *, chosen: bool) -> Outcome:
    """What the fan-out reported, channel by channel."""
    delivered = [cid for cid, ok, _msg in sent if ok]
    failed = [cid for cid, ok, _msg in sent if not ok]
    if not sent:
        detail = (
            "No channel subscribed to Tripwires. Recorded in the app."
            if not chosen
            else "The chosen channels no longer exist. Recorded in the app."
        )
        return Outcome(
            kind=ActionKind.NOTIFY.value, status=OutcomeStatus.DONE.value, detail=detail
        )
    names = dict(
        session.execute(
            select(NotificationChannel.id, NotificationChannel.name).where(
                NotificationChannel.id.in_(failed)
            )
        ).all()
        if failed
        else []
    )
    parts = []
    if delivered:
        parts.append(
            f"Sent to {len(delivered)} {'channel' if len(delivered) == 1 else 'channels'}"
        )
    if failed:
        listed = ", ".join(names.get(cid, str(cid)) for cid in failed)
        parts.append(
            f"{len(failed)} {'channel' if len(failed) == 1 else 'channels'} failed: {listed}"
        )
    return Outcome(
        kind=ActionKind.NOTIFY.value,
        status=OutcomeStatus.DONE.value if delivered else OutcomeStatus.FAILED.value,
        detail=" · ".join(parts),
    )


# ---------- focused scan ----------


def runs_today(session: Session, tripwire_id: uuid.UUID) -> int:
    marker = cast(Scan.execution_config, JSONB).op("->")(TRIPWIRE_KEY)
    return int(
        session.scalar(
            select(func.count()).where(
                marker.op("->>")("tripwire_id") == str(tripwire_id),
                Scan.created_at >= utc_now() - timedelta(days=1),
            )
        )
        or 0
    )


def seeds_of(dimension: str, rows: list[FiredRow]) -> list[dict]:
    kind = identity(dimension).seed_kind
    seen: dict[str, dict] = {}
    for row in rows:
        value = row.seed
        if not value or value in seen:
            continue
        seen[value] = {"kind": seed_kind_of(kind, value), "value": value}
        if len(seen) >= MAX_RUN_ASSETS:
            break
    return list(seen.values())


def _skip(detail: str) -> Outcome:
    return Outcome(
        kind=ActionKind.SCAN.value, status=OutcomeStatus.SKIPPED.value, detail=detail
    )


def start_run(
    session: Session,
    tripwire: Tripwire,
    run: TripwireRun,
    scan: Scan,
    seeds: list[dict],
    action: ScanAction,
) -> Outcome:
    """A focused run over the rows that fired, nested under the run that fired it."""
    stages = [
        s
        for s in (action.stages or stages_for(tripwire.dimension))
        if s in RESCANNABLE_STAGES
    ]
    target = session.get(Target, scan.target_id)
    refused = (
        NO_SEEDS
        if not seeds or target is None
        else NO_STAGES
        if not stages
        else DAILY_LIMIT
        if runs_today(session, tripwire.id) >= MAX_RUNS_PER_DAY
        else None
    )
    if refused:
        return _skip(refused)

    engine = session.get(ScanEngine, scan.engine_id) if scan.engine_id else None
    if engine is not None and engine.project_id != scan.project_id:
        engine = None
    context = session.get(ScanContext, scan.context_id) if scan.context_id else None
    if context is not None and context.project_id != scan.project_id:
        context = None
    resolved = merge_engine_context(
        engine or AdHocEngine(),
        context,
        target.target_value,
        target.target_type.value,
        proxy_url=scan_proxy_url(session, context),
        overrides=focused_overrides(stages),
        intensity=action.intensity or (scan.execution_config or {}).get("intensity"),
    )
    if not any(resolved.stage(s).get("enabled") for s in stages):
        return _skip(PASSIVE)
    resolved.seed_assets = seeds
    resolved.seed_only = True
    resolved.stages[ASSET_SEED_STAGE] = {
        **(resolved.stages.get(ASSET_SEED_STAGE) or {}),
        "enabled": True,
    }
    singular, plural = SURFACE_NOUN[tripwire.dimension]
    label = run_label(len(seeds), singular, plural)
    new = build_scan_row(
        resolved=resolved,
        engine=engine if engine is not None else AdHocEngine(name=label),
        context=context,
        target=target,
        project_id=scan.project_id,
        created_by=scan.created_by,
        parent_scan_id=scan.id,
        dimension=tripwire.dimension,
    )
    new.engine_name = label
    new.execution_config = {
        **new.execution_config,
        TRIPWIRE_KEY: {"tripwire_id": str(tripwire.id), "run_id": str(run.id)},
    }
    session.add(new)
    session.commit()
    try:
        dispatch_scan_run(str(new.id), new.run_epoch)
    except Exception:
        logger.warning("tripwire run dispatch failed", scan=str(new.id), exc_info=True)
        new.status = ScanStatus.FAILED.value
        new.error = NOT_QUEUED
        new.completed_at = utc_now()
        session.commit()
        return Outcome(
            kind=ActionKind.SCAN.value,
            status=OutcomeStatus.FAILED.value,
            detail=NOT_QUEUED,
            scan_id=new.id,
        )
    return Outcome(
        kind=ActionKind.SCAN.value,
        status=OutcomeStatus.DONE.value,
        detail=f"{label} started",
        scan_id=new.id,
    )


# ---------- the run's result ----------


def settle_run(session: Session, scan: Scan) -> Outcome | None:
    """Record what a tripwire's focused run found on the check that started it."""
    marker = (scan.execution_config or {}).get(TRIPWIRE_KEY) or {}
    try:
        run_id = uuid.UUID(str(marker.get("run_id")))
    except (TypeError, ValueError):
        return None
    run = session.get(TripwireRun, run_id)
    tripwire = session.get(Tripwire, run.tripwire_id) if run is not None else None
    if run is None or tripwire is None:
        return None
    counts = dict(
        session.execute(
            select(Vulnerability.severity, func.count())
            .where(
                Vulnerability.scan_id == scan.id,
                Vulnerability.severity.in_(ACTIONABLE_SEVERITIES),
                Vulnerability.replayed_from_id.is_(None),
            )
            .group_by(Vulnerability.severity)
        ).all()
    )
    findings = sum(counts.values())
    failed = scan.status != ScanStatus.COMPLETED.value
    if failed:
        detail = f"{scan.engine_name} did not complete"
    else:
        listed = ", ".join(
            f"{n} {sev}" for sev in ACTIONABLE_SEVERITIES if (n := counts.get(sev, 0))
        )
        detail = f"{scan.engine_name} completed · " + (
            listed if listed else "no findings"
        )
    outcome = Outcome(
        kind="scan_result",
        status=OutcomeStatus.FAILED.value if failed else OutcomeStatus.DONE.value,
        detail=detail,
        scan_id=scan.id,
    )
    run.outcomes = [*list(run.outcomes or []), outcome.model_dump(mode="json")]
    session.commit()

    notify_action = next(
        (
            a
            for a in parse_actions(tripwire.actions)
            if a.kind == ActionKind.NOTIFY.value
        ),
        None,
    )
    fired_on = session.get(Scan, run.scan_id)
    if notify_action is not None and fired_on is not None:
        sent = notify(
            session,
            tripwire,
            run,
            fired_on,
            [FiredRow.model_validate(r) for r in run.rows or []],
            notify_action.channel_ids,
            fired=run.fired,
            rescan=TripwireRescan(completed=not failed, by_severity=counts),
        )
        run.outcomes = [*list(run.outcomes or []), sent.model_dump(mode="json")]
        session.commit()
        return outcome

    payload = tripwire_run_result(
        TripwireRunResult(
            name=tripwire.name,
            target=_target_value(scan),
            findings=findings,
            by_severity=counts,
            scan_id=str(scan.id),
        )
    )
    if payload is None:
        return outcome
    try:
        SyncNotificationPublisher(BaseAppSettings().redis_url).publish(
            session=session,
            type=payload["type"],
            severity=payload["severity"],
            title=payload["title"],
            message=payload["message"],
            metadata=payload.get("metadata"),
            project_id=scan.project_id,
        )
    except Exception:
        logger.warning("tripwire run result notification failed", exc_info=True)
    return outcome


# ---------- dispatch ----------


def run_actions(
    session: Session,
    tripwire: Tripwire,
    run: TripwireRun,
    scan: Scan,
    rows: list[FiredRow],
    *,
    live: bool = False,
) -> list[Outcome]:
    """Every action, each recorded on its own. A started rescan carries the notification."""
    outcomes: list[Outcome] = []
    try:
        actions = parse_actions(tripwire.actions)
    except Exception:
        logger.warning("tripwire actions did not parse", tripwire=str(tripwire.id))
        return outcomes
    rescanning = False
    for action in sorted(actions, key=lambda a: a.kind == ActionKind.NOTIFY.value):
        try:
            if action.kind == ActionKind.SCAN.value:
                seeds = seeds_of(tripwire.dimension, rows)
                started = start_run(session, tripwire, run, scan, seeds, action)
                outcomes.append(started)
                rescanning = rescanning or started.status == OutcomeStatus.DONE.value
            elif action.kind == ActionKind.NOTIFY.value and not rescanning:
                outcomes.append(
                    notify(
                        session,
                        tripwire,
                        run,
                        scan,
                        rows,
                        action.channel_ids,
                        live=live,
                    )
                )
        except Exception:
            session.rollback()
            logger.warning("tripwire action failed", action=action.kind, exc_info=True)
            outcomes.append(
                Outcome(
                    kind=action.kind,
                    status=OutcomeStatus.FAILED.value,
                    detail="The action did not complete.",
                )
            )
    return outcomes


__all__ = [
    "delivery_outcome",
    "live_channels",
    "notify",
    "parse_actions",
    "run_actions",
    "runs_today",
    "seeds_of",
    "settle_run",
    "start_run",
]
