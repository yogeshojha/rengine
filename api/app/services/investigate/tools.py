"""The tools an investigation may call: read rows, propose a plan, conclude."""

from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask import tools as ask_tools
from app.services.investigate import policy
from mcp.context import ToolContext
from shared.definitions.ask import TraceStatus
from shared.definitions.investigate import (
    MAX_INVESTIGATION_REQUESTS,
    MAX_PLANS,
    PLAN_LABELS,
    REFUSAL_LABELS,
    PlanKind,
    PlanState,
    Verdict,
)
from shared.definitions.oast import OAST_TAG
from shared.models.ask import TraceStep
from shared.models.investigate import Investigation, InvestigationPlan
from shared.models.vuln_template import VulnTemplate
from shared.models.vulnerability import VulnerabilityRead
from shared.services.ai.agent import AgentTool
from shared.services.issue_tracking.body import mask_secrets
from shared.utils.net import host_port, split_host_port

PROPOSE_REPLAY = "propose_replay"
PROPOSE_CHECK = "propose_check"
CONCLUDE = "conclude"
ACTION_TOOLS = frozenset({PROPOSE_REPLAY, PROPOSE_CHECK, CONCLUDE})

PLAN_LIMIT = "The plan limit for this investigation is reached."
AGENT_VERDICTS: frozenset[str] = frozenset(
    {
        Verdict.CONFIRMED.value,
        Verdict.FALSE_POSITIVE.value,
        Verdict.PENDING.value,
        Verdict.NEEDS_PERSON.value,
    }
)

_REPLAY_TOOL = AgentTool(
    PROPOSE_REPLAY,
    "Propose that reNgine re-run this finding's own check on its host. A person "
    "approves it, and reNgine runs it through its scanner. State why a re-run settles "
    "the finding.",
    {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why re-running this check would settle the finding.",
            }
        },
        "required": ["reason"],
    },
)

_CHECK_TOOL = AgentTool(
    PROPOSE_CHECK,
    "Propose that reNgine run a named check on a host this scan already recorded under "
    "the finding's target. A person approves it. State the host, the template id and "
    "why the check is warranted.",
    {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "The host or host:port to run the check on, recorded by this scan.",
            },
            "template_id": {
                "type": "string",
                "description": "The nuclei template id to run.",
            },
            "reason": {
                "type": "string",
                "description": "Why this check is warranted.",
            },
        },
        "required": ["host", "template_id", "reason"],
    },
)

_CONCLUDE_TOOL = AgentTool(
    CONCLUDE,
    "Record the verdict and end. Use confirmed or false_positive when the stored "
    "evidence settles the finding, pending when a replay you proposed must run first, "
    "and needs_person when verification needs a step you do not take.",
    {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": sorted(AGENT_VERDICTS),
            },
            "rationale": {
                "type": "string",
                "description": "One or two sentences a reviewer reads, citing the evidence.",
            },
        },
        "required": ["verdict", "rationale"],
    },
)


def _ok(name: str, label: str, detail: str, started: float) -> TraceStep:
    return TraceStep(
        tool=name,
        label=label,
        status=TraceStatus.DONE.value,
        ms=int((time.monotonic() - started) * 1000),
        detail=detail[:200],
    )


class InvestigateTools:
    """Holds one investigation's run state while the agent calls tools."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        ask_ctx: ToolContext,
        investigation: Investigation,
        finding: VulnerabilityRead,
        target_value: str,
        target_zone: str,
        oast_ready: bool,
    ) -> None:
        self.session = session
        self.ask_ctx = ask_ctx
        self.investigation = investigation
        self.finding = finding
        self.target_value = target_value
        self.target_zone = target_zone
        self.oast_ready = oast_ready
        self.plans: list[InvestigationPlan] = []
        self.verdict: str | None = None
        self.rationale: str | None = None
        # requests this run's proposals reserve, above what the record already spent
        self.reserved = 0

    def tools(self) -> list[AgentTool]:
        return [*ask_tools.agent_tools(), _REPLAY_TOOL, _CHECK_TOOL, _CONCLUDE_TOOL]

    async def call(self, name: str, args: dict) -> tuple[str, TraceStep]:
        if name == PROPOSE_REPLAY:
            return await self._propose_replay(args)
        if name == PROPOSE_CHECK:
            return await self._propose_check(args)
        if name == CONCLUDE:
            return self._conclude(args)
        return await ask_tools.call(self.ask_ctx, name, args)

    # ---------- proposals ----------

    def _budget_remaining(self) -> int:
        return (
            MAX_INVESTIGATION_REQUESTS
            - self.investigation.requests_spent
            - self.reserved
        )

    async def _propose(
        self,
        *,
        kind: PlanKind,
        template_id: str,
        template_name: str | None,
        host: str,
        tags: frozenset[str],
        requests: int | None,
        needs_callback: bool,
        in_scope: bool,
        reason: str,
    ) -> tuple[str, TraceStep]:
        started = time.monotonic()
        label = PLAN_LABELS[kind.value]
        if len(self.plans) >= MAX_PLANS:
            return PLAN_LIMIT, _ok(kind.value, label, PLAN_LIMIT, started)
        decision = policy.refuses(
            policy.PlanInput(
                tags=tags,
                needs_callback=needs_callback,
                oast_ready=self.oast_ready,
                request_count=requests,
                in_scope=in_scope,
                budget_remaining=self._budget_remaining(),
            )
        )
        state = PlanState.REFUSED if decision else PlanState.PROPOSED
        plan = InvestigationPlan(
            investigation_id=self.investigation.id,
            kind=kind.value,
            template_id=template_id[:200],
            template_name=template_name,
            host=host[:255],
            reason=mask_secrets(reason)[:280],
            state=state.value,
            refusal_reason=decision.value if decision else None,
            request_count=requests,
        )
        self.session.add(plan)
        self.plans.append(plan)
        if state is PlanState.PROPOSED:
            self.reserved += policy.plan_cost(requests)
            ack = f"Proposed. {label} on {host}. A person approves it before it runs."
        else:
            ack = f"Refused. {REFUSAL_LABELS[decision.value]}. A person handles it."
        return ack, _ok(kind.value, label, ack, started)

    async def _propose_replay(self, args: dict) -> tuple[str, TraceStep]:
        v = self.finding
        tags, requests, needs_oast, name = await self._template_facts(
            v.template_id, frozenset(v.tags or ())
        )
        return await self._propose(
            kind=PlanKind.REPLAY,
            template_id=v.template_id,
            template_name=v.template_name or name,
            host=finding_seed(v),
            tags=tags,
            requests=requests,
            needs_callback=needs_oast or OAST_TAG in tags,
            in_scope=True,
            reason=str(args.get("reason") or ""),
        )

    async def _propose_check(self, args: dict) -> tuple[str, TraceStep]:
        host = str(args.get("host") or "").strip().lower()
        template_id = str(args.get("template_id") or "").strip()
        if not host or not template_id:
            step = _ok(
                PROPOSE_CHECK,
                PLAN_LABELS[PlanKind.CHECK.value],
                "missing",
                time.monotonic(),
            )
            return "A check needs a host and a template id.", step
        tags, requests, needs_oast, name = await self._template_facts(
            template_id, frozenset()
        )
        in_scope = self._under_target(host) and await self._recorded(host)
        return await self._propose(
            kind=PlanKind.CHECK,
            template_id=template_id,
            template_name=name,
            host=_seed_url(host),
            tags=tags,
            requests=requests,
            needs_callback=needs_oast,
            in_scope=in_scope,
            reason=str(args.get("reason") or ""),
        )

    def _conclude(self, args: dict) -> tuple[str, TraceStep]:
        verdict = str(args.get("verdict") or "")
        if verdict not in AGENT_VERDICTS:
            verdict = Verdict.NEEDS_PERSON.value
        self.verdict = verdict
        self.rationale = mask_secrets(str(args.get("rationale") or ""))
        ack = f"Recorded. Verdict {verdict}."
        return ack, _ok(CONCLUDE, "Conclude", ack, time.monotonic())

    # ---------- reads ----------

    async def _template_facts(
        self, template_id: str, fallback_tags: frozenset[str]
    ) -> tuple[frozenset[str], int | None, bool, str | None]:
        row = (
            await self.session.execute(
                select(VulnTemplate)
                .where(VulnTemplate.template_id == template_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return fallback_tags, None, False, None
        tags = frozenset(str(t).lower() for t in (row.tags or ())) | fallback_tags
        requests = row.requests if row.requests else None
        return tags, requests, bool(row.needs_oast), row.name

    def _under_target(self, host: str) -> bool:
        from shared.definitions.domains import owning_zone, target_zone  # noqa: PLC0415

        apex = split_host_port(host)[0]
        return (
            target_zone(apex) == self.target_zone
            or owning_zone(apex, {self.target_zone}) is not None
        )

    async def _recorded(self, host: str) -> bool:
        from shared.models.subdomain import Subdomain  # noqa: PLC0415

        apex = split_host_port(host)[0]
        found = (
            await self.session.execute(
                select(Subdomain.id)
                .where(
                    Subdomain.scan_id == self.investigation.scan_id,
                    Subdomain.name == apex,
                )
                .limit(1)
            )
        ).scalar()
        return found is not None


def _seed_url(host: str) -> str:
    """A host the agent named, as a URL seed; the probe scheme still applies."""
    host = host.strip()
    if "://" in host:
        return host
    return f"https://{host}"


def tool_label(name: str) -> str:
    if name == PROPOSE_REPLAY:
        return PLAN_LABELS[PlanKind.REPLAY.value]
    if name == PROPOSE_CHECK:
        return PLAN_LABELS[PlanKind.CHECK.value]
    if name == CONCLUDE:
        return "Conclude"
    return ask_tools.label(name)


def finding_seed(v: VulnerabilityRead) -> str:
    """The root URL a replay seeds, keeping the finding's port."""
    host = v.host or v.ip or ""
    scheme = v.scheme or "https"
    if v.port:
        return f"{scheme}://{host_port(host, v.port)}"
    return f"{scheme}://{host}"
