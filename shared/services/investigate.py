"""Settling an investigation's plan once its focused run finishes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.definitions.investigate import (
    MAX_INVESTIGATION_REQUESTS,
    MAX_RULE_REPLAYS,
    PlanKind,
    PlanResult,
    PlanState,
    Verdict,
)
from shared.definitions.oast import OAST_TAG
from shared.enums.scan import ScanStatus
from shared.logging import get_logger
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.investigate import Investigation, InvestigationPlan
from shared.models.scan import Scan
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import Vulnerability
from shared.services.investigate_policy import PlanInput, plan_cost, refuses
from shared.utils.datetime import utc_now
from shared.utils.net import host_port

logger = get_logger(__name__)

_LAUNCHED_STATES = (PlanState.RUNNING.value, PlanState.APPROVED.value)


def settle(session: Session, scan: Scan) -> bool:
    """Read a launched run's result onto its plan and the investigation's verdict."""
    plan = (
        session.execute(
            select(InvestigationPlan)
            .where(
                InvestigationPlan.launched_scan_id == scan.id,
                InvestigationPlan.state.in_(_LAUNCHED_STATES),
            )
            .limit(1)
        )
        .scalars()
        .first()
    )
    if plan is None:
        return False
    inv = session.get(Investigation, plan.investigation_id)
    if inv is None:
        return False
    now = utc_now()
    if scan.status != ScanStatus.COMPLETED.value:
        plan.result = PlanResult.ERROR.value
        plan.state = PlanState.FAILED.value
    else:
        plan.result = (
            PlanResult.REPRODUCED.value
            if _matched(session, scan.id, plan.template_id)
            else PlanResult.NOT_REPRODUCED.value
        )
        plan.state = PlanState.DONE.value
    plan.updated_at = now
    _reverdict(session, inv, now)
    return True


def _matched(session: Session, scan_id, template_id: str) -> bool:
    found = (
        session.execute(
            select(Vulnerability.id)
            .where(
                Vulnerability.scan_id == scan_id,
                Vulnerability.template_id == template_id,
            )
            .limit(1)
        )
        .scalars()
        .first()
    )
    return found is not None


def _reverdict(session: Session, inv: Investigation, now: datetime) -> None:
    plans = (
        session.execute(
            select(InvestigationPlan).where(
                InvestigationPlan.investigation_id == inv.id
            )
        )
        .scalars()
        .all()
    )
    done = [p.result for p in plans if p.state == PlanState.DONE.value]
    pending = any(p.state in _LAUNCHED_STATES for p in plans)
    if any(r == PlanResult.REPRODUCED.value for r in done):
        inv.verdict = Verdict.REPRODUCED.value
        inv.verified_at = inv.verified_at or now
    elif pending:
        inv.verdict = Verdict.PENDING.value
    elif done:
        inv.verdict = Verdict.NOT_REPRODUCED.value
        inv.verified_at = None
    inv.updated_at = now


# ---------- the known-exploited replay rule ----------


def replay_known_exploited(session: Session, scan: Scan) -> int:
    """Replay every known-exploited finding whose own check runs without judgement."""
    settings = (
        session.execute(
            select(InstanceSettings).where(
                InstanceSettings.singleton_key == SINGLETON_KEY
            )
        )
        .scalars()
        .first()
    )
    if settings is None or not settings.investigate_replay_kev:
        return 0
    from shared.services import oast  # noqa: PLC0415

    oast_ready = bool(oast.config(session).enabled)
    findings = (
        session.execute(
            select(Vulnerability)
            .where(Vulnerability.scan_id == scan.id, Vulnerability.is_kev.is_(True))
            .order_by(Vulnerability.discovered_at)
            .limit(MAX_RULE_REPLAYS)
        )
        .scalars()
        .all()
    )
    started = 0
    for v in findings:
        if _already_investigated(session, scan.target_id, v.fingerprint):
            continue
        try:
            if _rule_replay(session, scan, v, oast_ready):
                started += 1
        except Exception:
            session.rollback()
            logger.warning(
                "investigate rule replay failed",
                scan=str(scan.id),
                fingerprint=v.fingerprint,
                exc_info=True,
            )
    logger.info("investigate rule", scan=str(scan.id), started=started)
    return started


def _already_investigated(session: Session, target_id, fingerprint: str) -> bool:
    found = (
        session.execute(
            select(Investigation.id)
            .where(
                Investigation.target_id == target_id,
                Investigation.fingerprint == fingerprint,
            )
            .limit(1)
        )
        .scalars()
        .first()
    )
    return found is not None


def _template_facts(
    session: Session, template_id: str, finding_tags
) -> tuple[frozenset[str], int | None, bool]:
    row = (
        session.execute(
            select(VulnTemplate).where(VulnTemplate.template_id == template_id).limit(1)
        )
        .scalars()
        .first()
    )
    tags = {str(t).lower() for t in (finding_tags or ())}
    if row is None:
        return frozenset(tags), None, False
    tags |= {str(t).lower() for t in (row.tags or ())}
    return frozenset(tags), (row.requests or None), bool(row.needs_oast)


def _seed_url(v: Vulnerability) -> str:
    host = v.host or v.ip or ""
    scheme = v.scheme or "https"
    return f"{scheme}://{host_port(host, v.port)}" if v.port else f"{scheme}://{host}"


def _rule_replay(
    session: Session, scan: Scan, v: Vulnerability, oast_ready: bool
) -> bool:
    tags, requests, needs_oast = _template_facts(session, v.template_id, v.tags)
    decision = refuses(
        PlanInput(
            tags=tags,
            needs_callback=needs_oast or OAST_TAG in tags,
            oast_ready=oast_ready,
            request_count=requests,
            in_scope=True,
            budget_remaining=MAX_INVESTIGATION_REQUESTS,
        )
    )
    if decision is not None:
        return False
    seed = _seed_url(v)
    row = _build_focused_run(session, scan, v.template_id, seed)
    if row is None:
        return False
    now = utc_now()
    inv = Investigation(
        project_id=scan.project_id,
        target_id=scan.target_id,
        scan_id=scan.id,
        fingerprint=v.fingerprint,
        verdict=Verdict.PENDING.value,
        by_rule=True,
        started_by=None,
        rationale="Known-exploited finding replayed by the rule.",
        requests_spent=plan_cost(requests),
    )
    session.add(inv)
    session.flush()
    plan = InvestigationPlan(
        investigation_id=inv.id,
        kind=PlanKind.REPLAY.value,
        template_id=v.template_id,
        template_name=v.template_name,
        host=seed,
        reason="Known exploited.",
        state=PlanState.RUNNING.value,
        request_count=requests,
        approved_by=None,
        approved_at=now,
        launched_scan_id=row.id,
    )
    session.add(plan)
    session.commit()
    try:
        from shared.services.celery_dispatch import dispatch_scan_run  # noqa: PLC0415

        dispatch_scan_run(str(row.id), row.run_epoch)
    except Exception:
        row.status = ScanStatus.FAILED.value
        row.error = "Not queued. Check that the worker is running."
        row.completed_at = utc_now()
        plan.state = PlanState.FAILED.value
        plan.result = PlanResult.ERROR.value
        session.commit()
        logger.warning("investigate replay not queued", scan=str(row.id), exc_info=True)
        return False
    return True


def _build_focused_run(session: Session, scan: Scan, template_id: str, seed_url: str):
    """One focused vulnerability run over a single template and host seed."""
    from shared.definitions.default_engine import VULNERABILITY_STAGE  # noqa: PLC0415
    from shared.definitions.new_checks import FOLLOW_UP_STAGES  # noqa: PLC0415
    from shared.definitions.rescan import ASSET_SEED_STAGE, SeedKind  # noqa: PLC0415
    from shared.definitions.surface import SurfaceDimension  # noqa: PLC0415
    from shared.models.scan_context import ScanContext  # noqa: PLC0415
    from shared.models.scan_engine import ScanEngine  # noqa: PLC0415
    from shared.models.target import Target  # noqa: PLC0415
    from shared.services.focused import focused_overrides  # noqa: PLC0415
    from shared.services.launch_plan import AdHocEngine  # noqa: PLC0415
    from shared.services.proxy_resolve import scan_proxy_url  # noqa: PLC0415
    from shared.services.scan_factory import build_scan_row  # noqa: PLC0415
    from shared.services.scan_resolve import merge_engine_context  # noqa: PLC0415

    target = session.get(Target, scan.target_id)
    if target is None:
        return None
    engine = session.get(ScanEngine, scan.engine_id) if scan.engine_id else None
    if engine is not None and engine.project_id != target.project_id:
        engine = None
    context = session.get(ScanContext, scan.context_id) if scan.context_id else None
    if context is not None and context.project_id != target.project_id:
        context = None
    overrides = focused_overrides(FOLLOW_UP_STAGES)
    overrides[VULNERABILITY_STAGE] = {
        **(overrides.get(VULNERABILITY_STAGE) or {}),
        "enabled": True,
        "template_ids": [template_id],
        "custom_templates": [],
    }
    resolved = merge_engine_context(
        engine or AdHocEngine(),
        context,
        target.target_value,
        target.target_type.value,
        proxy_url=scan_proxy_url(session, context),
        overrides=overrides,
        intensity=(scan.execution_config or {}).get("intensity"),
    )
    if not resolved.stage(VULNERABILITY_STAGE).get("enabled"):
        return None
    resolved.seed_assets = [{"kind": SeedKind.URL.value, "value": seed_url}]
    resolved.seed_only = True
    resolved.stages[ASSET_SEED_STAGE] = {
        **(resolved.stages.get(ASSET_SEED_STAGE) or {}),
        "enabled": True,
    }
    row = build_scan_row(
        resolved=resolved,
        engine=engine if engine is not None else AdHocEngine(name="Investigate"),
        context=context,
        target=target,
        project_id=target.project_id,
        created_by=scan.created_by,
        parent_scan_id=scan.id,
        dimension=SurfaceDimension.VULNERABILITIES.value,
    )
    session.add(row)
    session.flush()
    return row
