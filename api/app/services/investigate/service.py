"""Running an investigation, approving its plans, and reading the record."""

from __future__ import annotations

import json
import secrets
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import async_db_session
from app.services.ask.service import software_hit
from app.services.ask.verdict import assess
from app.services.investigate import context as inv_context
from app.services.investigate import tools as inv_tools
from app.services.investigate.policy import plan_cost
from app.services.scan import ScanService
from app.services.vulnerability import VulnerabilityService
from mcp import limits
from mcp.capabilities import Capability
from mcp.context import TokenIdentity, ToolContext
from mcp.result import UNTRUSTED_NOTE
from shared.definitions.ai import KEY_OPTIONAL_PROVIDERS, AITask
from shared.definitions.ask import VERDICT_LABELS as ASK_VERDICT_LABELS
from shared.definitions.ask import TraceStatus
from shared.definitions.default_engine import VULNERABILITY_STAGE
from shared.definitions.investigate import (
    INVESTIGATE_CLIENT,
    INVESTIGATE_FEATURE,
    INVESTIGATE_OFF_REASONS,
    MAX_CALLS_PER_ROUND,
    MAX_RATIONALE_CHARS,
    MAX_TOOL_ROUNDS,
    PLAN_LABELS,
    PLAN_RESULT_LABELS,
    PLAN_STATE_LABELS,
    RATE_PER_MINUTE,
    REFUSAL_LABELS,
    InvestigateOffCode,
    PlanState,
    StreamEvent,
    Verdict,
    is_verified,
    verdict_label,
)
from shared.definitions.new_checks import FOLLOW_UP_STAGES
from shared.definitions.rescan import SeedKind
from shared.logging import get_logger
from shared.models.investigate import (
    InvestigateBrief,
    InvestigateRequest,
    Investigation,
    InvestigationPlan,
    InvestigationRead,
    PlanRead,
)
from shared.models.scan import Scan, ScanCreate, SeedAsset
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.user import User
from shared.models.vulnerability import Vulnerability, VulnerabilityRead
from shared.services.ai import AIError, ledger, load_config_async
from shared.services.ai.agent import CALL, DONE, RESULT, TEXT, AgentEvent, converse
from shared.services.ai.config import AIConfig
from shared.services.asset_query import QueryScope
from shared.services.credential_access import launch_refusal
from shared.services.focused import focused_overrides
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

FEATURE = INVESTIGATE_FEATURE
PROMPT = "Investigate this finding and reach a verdict."
FAILED = "Investigate did not complete. Check the api log."
RUNS_LIMIT = "Too many investigations. Wait a minute."
_VULN_STAGE = VULNERABILITY_STAGE


# ---------- availability ----------


def off_code(cfg: AIConfig | None) -> str | None:
    if cfg is None or not cfg.enabled:
        return InvestigateOffCode.SWITCHED_OFF.value
    if not cfg.provider:
        return InvestigateOffCode.NO_PROVIDER.value
    if not cfg.api_key and cfg.provider not in KEY_OPTIONAL_PROVIDERS:
        return InvestigateOffCode.NO_KEY.value
    if not cfg.available:
        return InvestigateOffCode.UNSUPPORTED.value
    if not cfg.allows(FEATURE):
        return InvestigateOffCode.FEATURE_OFF.value
    return None


def availability(cfg: AIConfig | None) -> str | None:
    code = off_code(cfg)
    return INVESTIGATE_OFF_REASONS.get(code) if code else None


def _identity(user: User, project_id: uuid.UUID, target_id: uuid.UUID) -> TokenIdentity:
    return TokenIdentity(
        id=user.id,
        name=INVESTIGATE_CLIENT,
        project_id=project_id,
        capabilities=frozenset({Capability.READ.value}),
        issued_by=user.id,
        targets=frozenset({target_id}),
    )


# ---------- read models ----------


def _plan_read(p: InvestigationPlan) -> PlanRead:
    return PlanRead(
        id=p.id,
        kind=p.kind,
        kind_label=PLAN_LABELS.get(p.kind, p.kind),
        template_id=p.template_id,
        template_name=p.template_name,
        host=p.host,
        reason=p.reason,
        state=p.state,
        state_label=PLAN_STATE_LABELS.get(p.state, p.state),
        refusal_reason=p.refusal_reason,
        refusal_label=REFUSAL_LABELS.get(p.refusal_reason or "") or None,
        request_count=p.request_count,
        approved_by=p.approved_by,
        approved_at=p.approved_at,
        launched_scan_id=p.launched_scan_id,
        result=p.result,
        result_label=PLAN_RESULT_LABELS.get(p.result or "") or None,
        created_at=p.created_at,
    )


def _read(inv: Investigation, plans: list[InvestigationPlan]) -> InvestigationRead:
    return InvestigationRead(
        id=inv.id,
        target_id=inv.target_id,
        scan_id=inv.scan_id,
        dimension=inv.dimension,
        fingerprint=inv.fingerprint,
        verdict=inv.verdict,
        verdict_label=verdict_label(inv.verdict),
        verified=inv.verified_at is not None,
        rationale=inv.rationale,
        trace=inv.trace,
        by_rule=inv.by_rule,
        started_by=inv.started_by,
        requests_spent=inv.requests_spent,
        verified_at=inv.verified_at,
        model=inv.model,
        cost_usd=inv.cost_usd,
        plans=[_plan_read(p) for p in plans],
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )


# ---------- loads ----------


async def _finding(
    session: AsyncSession, scan: Scan, fingerprint: str
) -> VulnerabilityRead | None:
    vuln_id = (
        await session.execute(
            select(Vulnerability.id)
            .where(
                Vulnerability.scan_id == scan.id,
                Vulnerability.target_id == scan.target_id,
                Vulnerability.fingerprint == fingerprint,
            )
            .limit(1)
        )
    ).scalar()
    if vuln_id is None:
        return None
    return await VulnerabilityService(session).get(QueryScope.of(scan.id), vuln_id)


async def _plans(
    session: AsyncSession, investigation_id: uuid.UUID
) -> list[InvestigationPlan]:
    rows = (
        (
            await session.execute(
                select(InvestigationPlan)
                .where(InvestigationPlan.investigation_id == investigation_id)
                .order_by(InvestigationPlan.created_at, InvestigationPlan.id)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def _scan_in_project(
    session: AsyncSession, scan_id: uuid.UUID, project_id: uuid.UUID
) -> Scan:
    scan = await session.get(Scan, scan_id)
    if scan is None or scan.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found.")
    return scan


# ---------- the run ----------


@dataclass
class _Turn:
    scan: Scan
    cfg: AIConfig
    investigation: Investigation
    bag: inv_tools.InvestigateTools
    ctx: inv_context.ask_context.Context
    steps: list = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    usage: AgentEvent = field(default_factory=lambda: AgentEvent(DONE))


def _frame(event: StreamEvent, data: dict) -> str:
    return f"event: {event.value}\ndata: {json.dumps(data, default=str)}\n\n"


async def _open(
    session: AsyncSession,
    user: User,
    project_id: uuid.UUID,
    request: InvestigateRequest,
) -> _Turn | str:
    scan = await _scan_in_project(session, request.scan_id, project_id)
    cfg = await load_config_async(session)
    reason = availability(cfg)
    if reason or cfg is None:
        return reason or "AI is switched off."
    if await limits.exceeded(user.id, RATE_PER_MINUTE):
        return RUNS_LIMIT
    finding = await _finding(session, scan, request.fingerprint)
    if finding is None:
        return "Finding not found in that scan."
    inv = await _get_or_create(session, scan, request.fingerprint, user)
    verdict, facts = assess(finding, software=await software_hit(session, finding))
    target_value = finding.target_value or finding.host or ""
    ctx = inv_context.build(
        finding,
        facts=facts,
        verdict=ASK_VERDICT_LABELS[verdict],
        target=target_value,
    )
    bag = inv_tools.InvestigateTools(
        session=session,
        ask_ctx=ToolContext(
            session=session,
            token=_identity(user, scan.project_id, scan.target_id),
            ui_base_url=settings.ui_base_url,
            client=INVESTIGATE_CLIENT,
        ),
        investigation=inv,
        finding=finding,
        target_value=target_value,
        target_zone=_zone(target_value),
        oast_ready=await _oast_ready(session),
    )
    await session.commit()
    return _Turn(scan=scan, cfg=cfg, investigation=inv, bag=bag, ctx=ctx)


async def _get_or_create(
    session: AsyncSession, scan: Scan, fingerprint: str, user: User
) -> Investigation:
    inv = (
        await session.execute(
            select(Investigation)
            .where(
                Investigation.target_id == scan.target_id,
                Investigation.fingerprint == fingerprint,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if inv is None:
        inv = Investigation(
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            fingerprint=fingerprint,
            started_by=user.id,
        )
        session.add(inv)
        await session.flush()
        return inv
    inv.scan_id = scan.id
    inv.verdict = Verdict.PENDING.value
    inv.verified_at = None
    inv.updated_at = utc_now()
    await session.execute(
        delete(InvestigationPlan).where(
            InvestigationPlan.investigation_id == inv.id,
            InvestigationPlan.state.in_(
                [PlanState.PROPOSED.value, PlanState.REFUSED.value]
            ),
        )
    )
    return inv


async def _drive(session: AsyncSession, turn: _Turn) -> AsyncIterator[str]:
    steps = turn.steps
    nonce = secrets.token_hex(4)

    async def call_tool(name: str, args: dict) -> tuple[str, bool]:
        text, step = await turn.bag.call(name, args)
        await session.commit()
        steps.append(step)
        if step.status != TraceStatus.DONE.value:
            return text, False
        if name in inv_tools.ACTION_TOOLS:
            return text, True
        n = sum(
            1
            for s in steps
            if s.status == TraceStatus.DONE.value
            and s.tool not in inv_tools.ACTION_TOOLS
        )
        fenced = f"<<untrusted {nonce}>>\n{UNTRUSTED_NOTE}\n{text}\n<<end {nonce}>>"
        return f"T{n}: {step.label}. Cite as [T{n}].\n{fenced}", True

    stream = converse(
        turn.cfg,
        system=turn.ctx.system,
        messages=[{"role": "user", "content": PROMPT}],
        tools=turn.bag.tools(),
        call_tool=call_tool,
        task=AITask.INVESTIGATE.value,
        max_rounds=MAX_TOOL_ROUNDS,
        max_calls=MAX_CALLS_PER_ROUND,
    )
    async for event in stream:
        if event.kind == TEXT:
            turn.parts.append(event.text)
            yield _frame(StreamEvent.DELTA, {"text": event.text})
        elif event.kind == CALL:
            yield _frame(
                StreamEvent.TRACE,
                {
                    "index": len(steps),
                    "tool": event.name,
                    "label": inv_tools.tool_label(event.name),
                    "status": TraceStatus.RUNNING.value,
                },
            )
        elif event.kind == RESULT and steps:
            yield _frame(
                StreamEvent.TRACE, {"index": len(steps) - 1, **steps[-1].model_dump()}
            )
        elif event.kind == DONE:
            turn.usage = event


async def _settle(session: AsyncSession, turn: _Turn) -> dict:
    inv = turn.investigation
    bag = turn.bag
    usage = turn.usage
    cost = (usage.charge or turn.cfg.charge(usage.usage, usage.model or None)).usd
    inv.verdict = bag.verdict or Verdict.NEEDS_PERSON.value
    rationale = (bag.rationale or "".join(turn.parts)).strip()[:MAX_RATIONALE_CHARS]
    inv.rationale = rationale or None
    inv.trace = [s.model_dump() for s in turn.steps]
    inv.flags = [f.model_dump() for f in turn.ctx.flags]
    inv.model = usage.model or None
    inv.input_tokens += usage.input_tokens
    inv.output_tokens += usage.output_tokens
    if cost is not None:
        inv.cost_usd = (inv.cost_usd or 0.0) + cost
    if is_verified(inv.verdict):
        inv.verified_at = utc_now()
    inv.updated_at = utc_now()
    await session.commit()
    plans = await _plans(session, inv.id)
    return _read(inv, plans).model_dump(mode="json")


async def run(
    session: AsyncSession,
    *,
    user: User,
    project_id: uuid.UUID,
    request: InvestigateRequest,
) -> AsyncIterator[str]:
    try:
        turn = await _open(session, user, project_id, request)
        if isinstance(turn, str):
            yield _frame(StreamEvent.ERROR, {"message": turn})
            return
        with ledger.source("scan", turn.scan.id):
            async for chunk in _drive(session, turn):
                yield chunk
        payload = await _settle(session, turn)
    except AIError as exc:
        yield _frame(StreamEvent.ERROR, {"message": str(exc)})
        return
    except Exception as exc:
        logger.warning("investigate run failed", error=str(exc))
        yield _frame(StreamEvent.ERROR, {"message": FAILED})
        return
    yield _frame(StreamEvent.DONE, payload)


async def stream_run(
    *, user: User, project_id: uuid.UUID, request: InvestigateRequest
) -> AsyncIterator[str]:
    async with async_db_session() as session:
        async for chunk in run(
            session, user=user, project_id=project_id, request=request
        ):
            yield chunk


# ---------- service: reads and approval ----------


class InvestigateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self, project_id: uuid.UUID, scan_id: uuid.UUID, fingerprint: str
    ) -> InvestigationRead | None:
        scan = await _scan_in_project(self.session, scan_id, project_id)
        inv = (
            await self.session.execute(
                select(Investigation)
                .where(
                    Investigation.target_id == scan.target_id,
                    Investigation.fingerprint == fingerprint,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if inv is None:
            return None
        return _read(inv, await _plans(self.session, inv.id))

    async def brief(
        self, project_id: uuid.UUID, scan_id: uuid.UUID, fingerprint: str
    ) -> InvestigateBrief:
        cfg = await load_config_async(self.session)
        reason = availability(cfg)
        found = await self.get(project_id, scan_id, fingerprint)
        return InvestigateBrief(
            investigation=found,
            available=reason is None,
            off_reason=reason,
            model=cfg.model if cfg and reason is None else None,
        )

    async def approve(
        self, user: User, project_id: uuid.UUID, plan_ids: list[uuid.UUID]
    ) -> InvestigationRead:
        plans = (
            (
                await self.session.execute(
                    select(InvestigationPlan).where(InvestigationPlan.id.in_(plan_ids))
                )
            )
            .scalars()
            .all()
        )
        if not plans:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No plan found.")
        investigation_id = plans[0].investigation_id
        inv = await self.session.get(Investigation, investigation_id)
        if inv is None or inv.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Investigation not found.")
        scan = await self.session.get(Scan, inv.scan_id)
        if scan is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found.")
        context = (
            await self.session.get(ScanContext, scan.context_id)
            if scan.context_id
            else None
        )
        refusal = launch_refusal(
            engine=None,
            context=context,
            user_id=user.id,
            superuser=user.is_superuser,
        )
        if refusal:
            raise HTTPException(status.HTTP_403_FORBIDDEN, refusal)
        for plan in plans:
            if (
                plan.investigation_id != investigation_id
                or plan.state != PlanState.PROPOSED.value
            ):
                continue
            await self._launch(user, project_id, scan, inv, plan)
        inv.updated_at = utc_now()
        await self.session.commit()
        return _read(inv, await _plans(self.session, inv.id))

    async def decline(
        self, project_id: uuid.UUID, plan_ids: list[uuid.UUID]
    ) -> InvestigationRead:
        plans = (
            (
                await self.session.execute(
                    select(InvestigationPlan).where(InvestigationPlan.id.in_(plan_ids))
                )
            )
            .scalars()
            .all()
        )
        if not plans:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No plan found.")
        inv = await self.session.get(Investigation, plans[0].investigation_id)
        if inv is None or inv.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Investigation not found.")
        for plan in plans:
            if (
                plan.investigation_id == inv.id
                and plan.state == PlanState.PROPOSED.value
            ):
                plan.state = PlanState.DECLINED.value
                plan.updated_at = utc_now()
        await self.session.commit()
        return _read(inv, await _plans(self.session, inv.id))

    async def _launch(
        self,
        user: User,
        project_id: uuid.UUID,
        scan: Scan,
        inv: Investigation,
        plan: InvestigationPlan,
    ) -> None:
        overrides = focused_overrides(FOLLOW_UP_STAGES)
        overrides[_VULN_STAGE] = {
            **(overrides.get(_VULN_STAGE) or {}),
            "enabled": True,
            "template_ids": [plan.template_id],
            "custom_templates": [],
        }
        created = await ScanService(self.session).create(
            ScanCreate(
                engine_id=await self._engine_for(scan, project_id),
                context_id=scan.context_id,
                target_id=inv.target_id,
                overrides=overrides,
                intensity=(scan.execution_config or {}).get("intensity"),
                seed_assets=[SeedAsset(kind=SeedKind.URL.value, value=plan.host)],
                parent_scan_id=scan.id,
                dimension=inv.dimension,
            ),
            project_id,
            user.id,
            reused_context=True,
        )
        plan.state = PlanState.RUNNING.value
        plan.approved_by = user.id
        plan.approved_at = utc_now()
        plan.launched_scan_id = created.id
        plan.updated_at = utc_now()
        inv.requests_spent += plan_cost(plan.request_count)

    async def _engine_for(self, scan: Scan, project_id: uuid.UUID) -> uuid.UUID | None:
        if scan.engine_id is None:
            return None
        engine = await self.session.get(ScanEngine, scan.engine_id)
        if engine is None or engine.project_id != project_id:
            return None
        return scan.engine_id


# ---------- helpers ----------


def _zone(value: str) -> str:
    from shared.definitions.domains import target_zone  # noqa: PLC0415

    return target_zone(value) if value else ""


async def _oast_ready(session: AsyncSession) -> bool:
    from shared.services import oast  # noqa: PLC0415

    try:
        return bool(await session.run_sync(lambda s: oast.config(s).enabled))
    except Exception:
        return False


__all__ = [
    "FEATURE",
    "InvestigateService",
    "availability",
    "off_code",
    "run",
    "stream_run",
]
