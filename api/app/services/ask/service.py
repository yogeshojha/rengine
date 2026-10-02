"""Ask threads and the streamed reply."""

from __future__ import annotations

import json
import secrets
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import async_db_session
from app.services.ask import (
    asset_context,
    budget,
    citations,
    context,
    starters,
    suggest,
    tools,
)
from app.services.ask.verdict import assess
from app.services.vulnerability import VulnerabilityService
from mcp import limits
from mcp.context import ToolContext
from mcp.result import UNTRUSTED_NOTE
from shared.definitions.ai import KEY_OPTIONAL_PROVIDERS, AITask
from shared.definitions.ask import (
    ASK_CLIENT,
    MAX_ANSWER_CHARS,
    MAX_CALLS_PER_ROUND,
    MAX_THREADS_PER_FINDING,
    MAX_TITLE,
    MAX_TOOL_ROUNDS,
    QUESTIONS_PER_DAY,
    RATE_PER_MINUTE,
    VERDICT_LABELS,
    MessageRole,
    StreamEvent,
    TraceStatus,
)
from shared.definitions.surface import SurfaceDimension
from shared.logging import get_logger
from shared.models.ask import (
    AskBrief,
    AskMessage,
    AskMessageRead,
    AskQuestion,
    AskThread,
    AskThreadCreate,
    AskThreadDetail,
    AskThreadRead,
    Fact,
    TraceStep,
)
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.user import User
from shared.models.vulnerability import Vulnerability, VulnerabilityRead
from shared.services.ai import AIError, ledger, load_config_async
from shared.services.ai.agent import CALL, DONE, RESULT, TEXT, AgentEvent, converse
from shared.services.ai.config import AIConfig
from shared.services.asset_query import QueryScope
from shared.utils.datetime import utc_now
from shared.utils.text import clip_line, strip_control

logger = get_logger(__name__)

FEATURE = "ask"
DEFAULT_TITLE = "New thread"
ASK_FAILED = "Ask did not complete. Check the api log."
NO_ANSWER = "The model returned no answer."


def availability(cfg: AIConfig | None) -> str | None:
    if cfg is None or not cfg.enabled:
        return "AI is switched off."
    if not cfg.provider:
        return "No AI provider is in use."
    if not cfg.api_key and cfg.provider not in KEY_OPTIONAL_PROVIDERS:
        return "No AI provider key is set."
    if not cfg.available:
        return "The AI provider is not supported."
    if not cfg.allows(FEATURE):
        return "Ask is switched off in AI settings."
    return None


def _thread_read(row: AskThread) -> AskThreadRead:
    return AskThreadRead(
        id=row.id,
        target_id=row.target_id,
        dimension=row.dimension,
        asset_key=row.asset_key,
        title=row.title or DEFAULT_TITLE,
        message_count=row.message_count,
        cost_usd=row.cost_usd,
        created_at=row.created_at,
        last_at=row.last_at,
    )


def _message_read(row: AskMessage) -> AskMessageRead:
    return AskMessageRead.model_validate(row, from_attributes=True)


def _title(text: str) -> str:
    return clip_line(text, MAX_TITLE)


def _frame(event: StreamEvent, data: Any) -> str:
    return f"event: {event.value}\ndata: {json.dumps(data, default=str)}\n\n"


async def software_hit(
    session: AsyncSession, v: VulnerabilityRead
) -> SoftwareCve | None:
    if not v.cve_ids or not v.host:
        return None
    stmt = (
        select(SoftwareCve)
        .where(
            SoftwareCve.scan_id == v.scan_id,
            SoftwareCve.host == v.host,
            SoftwareCve.cve.in_(v.cve_ids),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()


class AskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def threads(
        self, user_id: uuid.UUID, target_id: uuid.UUID, dimension: str, asset_key: str
    ) -> list[AskThreadRead]:
        stmt = (
            select(AskThread)
            .where(
                AskThread.user_id == user_id,
                AskThread.target_id == target_id,
                AskThread.dimension == dimension,
                AskThread.asset_key == asset_key,
            )
            .order_by(AskThread.last_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_thread_read(r) for r in rows]

    async def create(
        self, user_id: uuid.UUID, project_id: uuid.UUID, data: AskThreadCreate
    ) -> AskThreadRead:
        target = await self.session.get(Target, data.target_id)
        if target is None or target.project_id != project_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found.")
        if not await _exists(
            self.session, data.dimension, data.target_id, data.asset_key
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND[data.dimension])
        count = await self.session.scalar(
            select(func.count())
            .select_from(AskThread)
            .where(
                AskThread.user_id == user_id,
                AskThread.target_id == data.target_id,
                AskThread.dimension == data.dimension,
                AskThread.asset_key == data.asset_key,
            )
        )
        if (count or 0) >= MAX_THREADS_PER_FINDING:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Thread limit of {MAX_THREADS_PER_FINDING} reached. "
                "Delete a thread to start another.",
            )
        title = strip_control(data.title or "").strip()
        row = AskThread(
            project_id=project_id,
            target_id=data.target_id,
            user_id=user_id,
            dimension=data.dimension,
            asset_key=data.asset_key,
            title=_title(title) if title else None,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return _thread_read(row)

    async def get(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> AskThread | None:
        row = await self.session.get(AskThread, thread_id)
        return row if row is not None and row.user_id == user_id else None

    async def messages(self, thread_id: uuid.UUID) -> list[AskMessage]:
        stmt = (
            select(AskMessage)
            .where(AskMessage.thread_id == thread_id)
            .order_by(AskMessage.created_at, AskMessage.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def detail(
        self, user_id: uuid.UUID, thread_id: uuid.UUID
    ) -> AskThreadDetail | None:
        row = await self.get(user_id, thread_id)
        if row is None:
            return None
        rows = await self.messages(thread_id)
        return AskThreadDetail(
            thread=_thread_read(row), messages=[_message_read(m) for m in rows]
        )

    async def delete_all(
        self, user_id: uuid.UUID, target_id: uuid.UUID, dimension: str, asset_key: str
    ) -> int:
        stmt = (
            delete(AskThread)
            .where(
                AskThread.user_id == user_id,
                AskThread.target_id == target_id,
                AskThread.dimension == dimension,
                AskThread.asset_key == asset_key,
            )
            .returning(AskThread.id)
        )
        gone = len((await self.session.execute(stmt)).scalars().all())
        await self.session.commit()
        return gone

    async def delete(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> bool:
        row = await self.get(user_id, thread_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def brief(self, scope: QueryScope, vuln_id: uuid.UUID) -> AskBrief | None:
        v = await VulnerabilityService(self.session).get(scope, vuln_id)
        if v is None:
            return None
        software = await software_hit(self.session, v)
        verdict, facts = assess(v, software=software)
        asks = starters.for_finding(v, verdict=verdict, software=software)
        return await self._brief(verdict, facts, asks)

    async def brief_asset(self, scan_id: uuid.UUID, name: str) -> AskBrief | None:
        row = (
            await self.session.execute(
                select(Subdomain.target_id)
                .where(Subdomain.scan_id == scan_id, Subdomain.name == name)
                .limit(1)
            )
        ).scalar()
        if row is None:
            return None
        bundle = await asset_context.load(self.session, scan_id, row, name)
        if bundle is None:
            return None
        verdict, facts = asset_context.assess(bundle)
        return await self._brief(verdict, facts, starters.for_asset(bundle))

    async def _brief(
        self, verdict: str, facts: list[Fact], asks: list[str]
    ) -> AskBrief:
        cfg = await load_config_async(self.session)
        reason = availability(cfg)
        model = cfg.model if cfg and reason is None else None
        return AskBrief(
            verdict=verdict,
            label=VERDICT_LABELS[verdict],
            facts=facts,
            available=reason is None,
            off_reason=reason,
            model=model,
            starters=asks,
        )


NOT_FOUND: dict[str, str] = {
    SurfaceDimension.VULNERABILITIES.value: "Finding not found.",
    SurfaceDimension.WEB_ASSETS.value: "Web asset not found.",
}


async def _exists(
    session: AsyncSession, dimension: str, target_id: uuid.UUID, key: str
) -> bool:
    if dimension == SurfaceDimension.WEB_ASSETS.value:
        stmt = (
            select(Subdomain.id)
            .where(Subdomain.target_id == target_id, Subdomain.name == key)
            .limit(1)
        )
    else:
        stmt = (
            select(Vulnerability.id)
            .where(
                Vulnerability.target_id == target_id, Vulnerability.fingerprint == key
            )
            .limit(1)
        )
    return (await session.execute(stmt)).scalar() is not None


async def _target_value(session: AsyncSession, target_id: uuid.UUID) -> str:
    target = await session.get(Target, target_id)
    return target.target_value if target else ""


def _target(v: VulnerabilityRead) -> str:
    return v.target_value or v.host or v.ip or ""


async def _finding(
    session: AsyncSession, thread: AskThread, scan_id: uuid.UUID
) -> VulnerabilityRead | None:
    stmt = (
        select(Vulnerability.id)
        .where(
            Vulnerability.scan_id == scan_id,
            Vulnerability.target_id == thread.target_id,
            Vulnerability.fingerprint == thread.asset_key,
        )
        .limit(1)
    )
    vuln_id = (await session.execute(stmt)).scalar()
    if vuln_id is None:
        return None
    return await VulnerabilityService(session).get(QueryScope.of(scan_id), vuln_id)


@dataclass
class _Turn:
    thread: AskThread
    cfg: AIConfig
    ctx: context.Context
    facts: list[Fact]
    earlier: list[dict[str, str]]
    text: str
    asked: AskMessage
    steps: list[TraceStep] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    usage: AgentEvent = field(default_factory=lambda: AgentEvent(DONE))


async def _subject(
    session: AsyncSession, thread: AskThread, scan_id: uuid.UUID
) -> tuple[context.Context, list[Fact]] | str:
    if thread.dimension == SurfaceDimension.WEB_ASSETS.value:
        bundle = await asset_context.load(
            session, scan_id, thread.target_id, thread.asset_key
        )
        if bundle is None:
            return "Web asset not found in that scan."
        _, facts = asset_context.assess(bundle)
        target = await _target_value(session, thread.target_id)
        return asset_context.build(bundle, facts=facts, target=target), facts
    v = await _finding(session, thread, scan_id)
    if v is None:
        return "Finding not found in that scan."
    verdict, facts = assess(v, software=await software_hit(session, v))
    ctx = context.build(
        v, facts=facts, verdict=VERDICT_LABELS[verdict], target=_target(v)
    )
    return ctx, facts


async def _open(
    session: AsyncSession, user: User, thread_id: uuid.UUID, question: AskQuestion
) -> _Turn | str:
    service = AskService(session)
    thread = await service.get(user.id, thread_id)
    if thread is None:
        return "Thread not found."
    cfg = await load_config_async(session)
    reason = availability(cfg)
    if reason or cfg is None:
        return reason or "AI is switched off."
    if await limits.exceeded(user.id, RATE_PER_MINUTE):
        return "Too many questions. Wait a minute."
    if await budget.over_daily(user.id):
        return f"{QUESTIONS_PER_DAY} questions a day reached. Ask again tomorrow."
    built = await _subject(session, thread, question.scan_id)
    if isinstance(built, str):
        return built
    ctx, facts = built
    earlier = context.history(await service.messages(thread.id))
    await session.commit()
    text = question.text
    asked = AskMessage(thread_id=thread.id, role=MessageRole.USER.value, text=text)
    return _Turn(thread, cfg, ctx, facts, earlier, text, asked)


async def _settle(session: AsyncSession, turn: _Turn) -> dict:
    raw, suggestion = suggest.split("".join(turn.parts)[:MAX_ANSWER_CHARS])
    clean, cites = citations.resolve(
        raw, turn.facts, turn.steps, response_lines=turn.ctx.response_lines
    )
    if not clean:
        raise AIError(NO_ANSWER)
    usage = turn.usage
    cost = (usage.charge or turn.cfg.charge(usage.usage, usage.model or None)).usd
    answer = AskMessage(
        thread_id=turn.thread.id,
        role=MessageRole.ASSISTANT.value,
        text=clean,
        citations=[c.model_dump() for c in cites],
        trace=[s.model_dump() for s in turn.steps],
        flags=[f.model_dump() for f in turn.ctx.flags],
        suggestion=suggestion.model_dump() if suggestion else None,
        model=usage.model or None,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=cost,
    )
    thread = turn.thread
    session.add(turn.asked)
    session.add(answer)
    if thread.title is None:
        thread.title = _title(turn.text)
    thread.input_tokens += usage.input_tokens
    thread.output_tokens += usage.output_tokens
    if cost is not None:
        thread.cost_usd = (thread.cost_usd or 0.0) + cost
    thread.last_at = utc_now()
    await session.flush()
    thread.message_count = (
        await session.scalar(
            select(func.count())
            .select_from(AskMessage)
            .where(AskMessage.thread_id == thread.id)
        )
        or 0
    )
    await session.commit()
    await session.refresh(answer)
    await session.refresh(turn.asked)
    return {
        "question": _message_read(turn.asked).model_dump(mode="json"),
        "answer": _message_read(answer).model_dump(mode="json"),
        "thread": _thread_read(thread).model_dump(mode="json"),
    }


async def _run(session: AsyncSession, user: User, turn: _Turn) -> AsyncIterator[str]:
    tctx = ToolContext(
        session=session,
        token=tools.identity_for(user, turn.thread.project_id),
        ui_base_url=settings.ui_base_url,
        client=ASK_CLIENT,
    )
    steps = turn.steps
    nonce = secrets.token_hex(4)

    async def call_tool(name: str, args: dict) -> tuple[str, bool]:
        result, step = await tools.call(tctx, name, args)
        await session.commit()
        steps.append(step)
        if step.status != TraceStatus.DONE.value:
            return result, False
        n = sum(1 for s in steps if s.status == TraceStatus.DONE.value)
        fenced = f"<<untrusted {nonce}>>\n{UNTRUSTED_NOTE}\n{result}\n<<end {nonce}>>"
        return f"T{n}: {step.label}. Cite as [T{n}].\n{fenced}", True

    stream = converse(
        turn.cfg,
        system=turn.ctx.system,
        messages=[
            *turn.earlier,
            {"role": MessageRole.USER.value, "content": turn.text},
        ],
        tools=tools.agent_tools(),
        call_tool=call_tool,
        task=AITask.ASK.value,
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
                    "label": tools.label(event.name),
                    "status": TraceStatus.RUNNING.value,
                },
            )
        elif event.kind == RESULT and steps:
            yield _frame(
                StreamEvent.TRACE, {"index": len(steps) - 1, **steps[-1].model_dump()}
            )
        elif event.kind == DONE:
            turn.usage = event


async def reply(
    session: AsyncSession, *, thread_id: uuid.UUID, user: User, question: AskQuestion
) -> AsyncIterator[str]:
    try:
        turn = await _open(session, user, thread_id, question)
        if isinstance(turn, str):
            yield _frame(StreamEvent.ERROR, {"message": turn})
            return
        with ledger.source("thread", turn.thread.id, user.id):
            async for chunk in _run(session, user, turn):
                yield chunk
        payload = await _settle(session, turn)
    except AIError as exc:
        yield _frame(StreamEvent.ERROR, {"message": str(exc)})
        return
    except Exception as exc:
        logger.warning("ask reply failed", error=str(exc))
        yield _frame(StreamEvent.ERROR, {"message": ASK_FAILED})
        return
    yield _frame(StreamEvent.DONE, payload)


async def stream_reply(
    *, thread_id: uuid.UUID, user: User, question: AskQuestion
) -> AsyncIterator[str]:
    async with async_db_session() as session:
        async for chunk in reply(
            session, thread_id=thread_id, user=user, question=question
        ):
            yield chunk
