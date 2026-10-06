"""Ask across the estate: threads, the streamed reply and the blocks it shows."""

from __future__ import annotations

import json
import re
import secrets
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import async_db_session
from app.services.ask import budget, citations, context, tools
from app.services.ask.estate import (
    blocks,
    busy,
    follow_ups,
    prompt,
    scope,
    show,
    starters,
)
from app.services.ask.service import (
    ASK_FAILED,
    DEFAULT_TITLE,
    NO_ANSWER,
    _frame,
    _message_read,
    _title,
    availability,
    off_code,
)
from app.services.target_scope import TargetFilter, resolve_targets
from mcp import limits
from mcp.context import ToolContext
from mcp.result import UNTRUSTED_NOTE
from shared.definitions.ai import AITask
from shared.definitions.ask import (
    ACROSS_RUNS,
    ASK_CLIENT,
    ASK_OFF_REASONS,
    BLOCK_REF,
    EMPTY_THREAD_SECONDS,
    ESTATE_CALLS_PER_ROUND,
    ESTATE_TOOL_ROUNDS,
    INTELLIGENT_TOOL_ROUNDS,
    LISTED_SCANS,
    LISTED_THREADS,
    MAX_ANSWER_CHARS,
    MAX_ESTATE_THREADS,
    QUESTIONS_PER_DAY,
    RATE_PER_MINUTE,
    AskOffCode,
    AskSubject,
    BlockKind,
    MessageRole,
    StreamEvent,
    TraceStatus,
)
from shared.enums.scan import ScanStatus
from shared.logging import get_logger
from shared.models.ask import (
    AnswerBlock,
    AskMessage,
    AskThread,
    BlockData,
    EstateQuestion,
    EstateScanOption,
    EstateStarters,
    EstateStatus,
    EstateThreadCreate,
    EstateThreadDetail,
    EstateThreadRead,
    FollowUp,
    PinnedQuery,
    TraceStep,
)
from shared.models.project import Project
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.user import User
from shared.services.ai import AIError, ledger, load_config_async
from shared.services.ai.agent import CALL, DONE, RESULT, TEXT, AgentEvent, converse
from shared.services.ai.config import AIConfig
from shared.utils.datetime import utc_now
from shared.utils.text import strip_control

logger = get_logger(__name__)

THREAD_NOT_FOUND = "Thread not found."
FIRST_SENTENCE = re.compile(r"^[^.!?\n]*[.!?](?=\s|$)")
WORD = re.compile(r"[\w-]+")
BLOCK_WORD = re.compile(r"^b\d{1,2}$")
PARAGRAPH = re.compile(r"\n\s*\n")
NARRATION = re.compile(
    r"^(now|next|then|let me|let's|i'll|i will|i am|i'm|checking|looking|searching)\b"
    r"|:$",
    re.IGNORECASE,
)
FILLER = frozenset(
    {
        "exist",
        "exists",
        "are",
        "is",
        "were",
        "was",
        "found",
        "detected",
        "matched",
        "match",
        "in",
        "scope",
        "total",
        "there",
        "across",
        "the",
        "estate",
        "recorded",
        "lists",
        "shows",
        "holds",
        "contains",
    }
)
BLOCK_NOT_FOUND = "Block not found."


def _estate(row: AskThread | None, user_id: uuid.UUID) -> AskThread | None:
    if row is None or row.user_id != user_id:
        return None
    return row if row.subject == AskSubject.ESTATE.value else None


def identity(user: User, project_id: uuid.UUID, resolved: scope.Resolved):
    return tools.identity_for(user, project_id, targets=resolved.targets)


async def _reread(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: scope.Resolved,
    block: AnswerBlock,
) -> BlockData:
    """An edited block, with its grouping chosen again."""
    if block.kind != BlockKind.ROWS.value:
        return await blocks.read(session, project_id, resolved, block)
    try:
        return await blocks.rows(session, project_id, resolved, block, pick=True)
    except blocks.BlockError as exc:
        return BlockData(
            id=block.id, kind=block.kind, dimension=block.dimension, error=str(exc)
        )


def held_blocks(rows: list[AskMessage]) -> list[AnswerBlock]:
    out: list[AnswerBlock] = []
    for row in rows:
        for raw in row.blocks or []:
            try:
                out.append(AnswerBlock.model_validate(raw))
            except ValueError:
                continue
    return out


class EstateService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def status(self) -> EstateStatus:
        cfg = await load_config_async(self.session)
        code = off_code(cfg)
        on = code is None and cfg is not None
        return EstateStatus(
            available=on,
            off_reason=availability(cfg),
            off_code=code,
            provider=cfg.provider if on and cfg else None,
            model=cfg.model if on and cfg else None,
        )

    async def _read(
        self, row: AskThread, held: dict[str, scope.Resolved] | None = None
    ) -> EstateThreadRead:
        key = json.dumps(row.scope or {}, sort_keys=True)
        resolved = held.get(key) if held is not None else None
        if resolved is None:
            resolved = await scope.resolve(self.session, row.project_id, row.scope)
            if held is not None:
                held[key] = resolved
        return EstateThreadRead(
            id=row.id,
            project_id=row.project_id,
            title=row.title or DEFAULT_TITLE,
            scope=scope.read(row.scope, resolved),
            message_count=row.message_count,
            cost_usd=row.cost_usd,
            created_at=row.created_at,
            last_at=row.last_at,
        )

    async def threads(
        self, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[EstateThreadRead]:
        stmt = (
            select(AskThread)
            .where(
                AskThread.user_id == user_id,
                AskThread.project_id == project_id,
                AskThread.subject == AskSubject.ESTATE.value,
                AskThread.message_count > 0,
            )
            .order_by(AskThread.last_at.desc())
            .limit(LISTED_THREADS)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        held: dict[str, scope.Resolved] = {}
        return [await self._read(r, held) for r in rows]

    async def create(
        self, user_id: uuid.UUID, project_id: uuid.UUID, data: EstateThreadCreate
    ) -> EstateThreadRead:
        if await self.session.get(Project, project_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
        await self.session.execute(
            delete(AskThread).where(
                AskThread.user_id == user_id,
                AskThread.project_id == project_id,
                AskThread.subject == AskSubject.ESTATE.value,
                AskThread.message_count == 0,
                AskThread.created_at
                < utc_now() - timedelta(seconds=EMPTY_THREAD_SECONDS),
            )
        )
        count = await self.session.scalar(
            select(func.count())
            .select_from(AskThread)
            .where(
                AskThread.user_id == user_id,
                AskThread.project_id == project_id,
                AskThread.subject == AskSubject.ESTATE.value,
            )
        )
        if (count or 0) >= MAX_ESTATE_THREADS:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Thread limit of {MAX_ESTATE_THREADS} reached. "
                "Delete a thread to start another.",
            )
        if foreign := await scope.foreign(self.session, project_id, data.scope):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, foreign)
        title = strip_control(data.title or "").strip()
        row = AskThread(
            project_id=project_id,
            user_id=user_id,
            subject=AskSubject.ESTATE.value,
            dimension=AskSubject.ESTATE.value,
            scope=scope.stored(data.scope),
            title=_title(title) if title else None,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return await self._read(row)

    async def get(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> AskThread | None:
        return _estate(await self.session.get(AskThread, thread_id), user_id)

    async def messages(self, thread_id: uuid.UUID) -> list[AskMessage]:
        stmt = (
            select(AskMessage)
            .where(AskMessage.thread_id == thread_id)
            .order_by(AskMessage.created_at, AskMessage.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def detail(
        self, user_id: uuid.UUID, thread_id: uuid.UUID
    ) -> EstateThreadDetail | None:
        row = await self.get(user_id, thread_id)
        if row is None:
            return None
        rows = await self.messages(thread_id)
        return EstateThreadDetail(
            thread=await self._read(row), messages=[_message_read(m) for m in rows]
        )

    async def blocks(
        self, user_id: uuid.UUID, thread_id: uuid.UUID
    ) -> list[BlockData] | None:
        row = await self.get(user_id, thread_id)
        if row is None:
            return None
        project_id = row.project_id
        resolved = await scope.resolve(self.session, project_id, row.scope)
        held = held_blocks(await self.messages(thread_id))
        return [await blocks.read(self.session, project_id, resolved, b) for b in held]

    async def page(
        self, user_id: uuid.UUID, thread_id: uuid.UUID, block_id: str, offset: int
    ) -> BlockData:
        row = await self.get(user_id, thread_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, THREAD_NOT_FOUND)
        project_id = row.project_id
        held = held_blocks(await self.messages(thread_id))
        block = next((b for b in held if b.id == block_id), None)
        if block is None or block.kind != BlockKind.ROWS.value:
            raise HTTPException(status.HTTP_404_NOT_FOUND, BLOCK_NOT_FOUND)
        resolved = await scope.resolve(self.session, project_id, row.scope)
        try:
            return await blocks.rows(
                self.session,
                project_id,
                resolved,
                block,
                offset=offset,
                extras=False,
            )
        except blocks.BlockError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
            ) from exc

    async def edit(
        self, user_id: uuid.UUID, thread_id: uuid.UUID, block_id: str, query: str
    ) -> BlockData:
        """Run a block on a new query and keep it when it runs."""
        row = await self.get(user_id, thread_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, THREAD_NOT_FOUND)
        project_id, raw_scope = row.project_id, row.scope
        held = [(m.id, list(m.blocks or [])) for m in await self.messages(thread_id)]
        for message_id, stored in held:
            for index, raw in enumerate(stored):
                if raw.get("id") != block_id:
                    continue
                block = AnswerBlock.model_validate(raw)
                if block.kind == BlockKind.CVE.value:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_CONTENT,
                        "A CVE block has no query.",
                    )
                block.query = blocks.clean_query(query)
                block.cause_key = None
                resolved = await scope.resolve(self.session, project_id, raw_scope)
                data = await _reread(self.session, project_id, resolved, block)
                if data.error:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_CONTENT, data.error
                    )
                block.total = data.total
                block.capped = data.capped
                block.edited = True
                stored[index] = block.model_dump(mode="json")
                message = await self.session.get(AskMessage, message_id)
                if message is None:
                    break
                message.blocks = stored
                await self.session.commit()
                return data
        raise HTTPException(status.HTTP_404_NOT_FOUND, BLOCK_NOT_FOUND)

    async def delete(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> bool:
        row = await self.get(user_id, thread_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def starters(self, project_id: uuid.UUID, raw: dict) -> EstateStarters:
        if foreign := await scope.foreign(self.session, project_id, scope.parsed(raw)):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, foreign)
        resolved = await scope.resolve(self.session, project_id, raw)
        return await starters.counted(self.session, project_id, resolved)

    async def scans(
        self, project_id: uuid.UUID, spec: TargetFilter, text: str = ""
    ) -> list[EstateScanOption]:
        at = func.coalesce(Scan.completed_at, Scan.started_at, Scan.created_at)
        stmt = (
            select(
                Scan.id,
                Target.target_value,
                Scan.engine_name,
                Scan.status,
                Scan.scope,
                at,
            )
            .join(Target, Target.id == Scan.target_id)
            .where(
                Scan.project_id == project_id,
                Scan.status != ScanStatus.PENDING.value,
            )
            .order_by(at.desc())
            .limit(LISTED_SCANS)
        )
        picked = await resolve_targets(self.session, project_id, spec)
        if picked is not None:
            stmt = stmt.where(Scan.target_id.in_(picked))
        if needle := text.strip().lower():
            stmt = stmt.where(
                func.lower(Target.target_value).contains(needle)
                | func.lower(Scan.engine_name).contains(needle)
            )
        return [
            EstateScanOption(
                id=row[0],
                target=row[1],
                engine=row[2],
                status=str(row[3]),
                scope=str(row[4]),
                at=row[5],
            )
            for row in (await self.session.execute(stmt)).all()
        ]


# ---------- the streamed reply ----------


@dataclass
class _Turn:
    thread: AskThread
    thread_id: uuid.UUID
    project_id: uuid.UUID
    cfg: AIConfig
    board: show.Board
    project: str
    earlier: list[dict[str, str]]
    text: str
    about: str | None
    intelligent: bool
    asked: AskMessage
    pinned: PinnedQuery | None = None
    steps: list[TraceStep] = field(default_factory=list)
    parts: list[str] = field(default_factory=list)
    said: list[str] = field(default_factory=list)
    usage: AgentEvent = field(default_factory=lambda: AgentEvent(DONE))
    follow_ups: list[FollowUp] = field(default_factory=list)


async def _open(
    session: AsyncSession, user: User, thread_id: uuid.UUID, question: EstateQuestion
) -> _Turn | str:
    service = EstateService(session)
    thread = await service.get(user.id, thread_id)
    if thread is None:
        return THREAD_NOT_FOUND
    cfg = await load_config_async(session)
    reason = availability(cfg)
    if reason or cfg is None:
        return reason or ASK_OFF_REASONS[AskOffCode.SWITCHED_OFF.value]
    if await limits.exceeded(user.id, RATE_PER_MINUTE):
        return "Too many questions. Wait a minute."
    if await budget.over_daily(user.id):
        return f"{QUESTIONS_PER_DAY} questions a day reached. Ask again tomorrow."
    rows = await service.messages(thread.id)
    resolved = await scope.resolve(session, thread.project_id, thread.scope)
    project = await session.get(Project, thread.project_id)
    board = show.Board(thread.project_id, resolved, held_blocks(rows))
    earlier = context.history(rows)
    await session.commit()
    asked = AskMessage(
        thread_id=thread.id,
        role=MessageRole.USER.value,
        text=question.text,
        about=question.about,
        intelligent=question.intelligent,
    )
    return _Turn(
        thread=thread,
        thread_id=thread.id,
        project_id=thread.project_id,
        cfg=cfg,
        board=board,
        project=project.name if project else "",
        earlier=earlier,
        text=question.text,
        about=prompt.about_line(question.about, board.held),
        intelligent=question.intelligent,
        asked=asked,
        pinned=question.pinned,
    )


CITED = re.compile(r"[ \t]*\[(B\d{1,2})\]")


def _clean(raw: str, board: show.Board) -> str:
    known = {b.id for b in board.every}

    def keep(match) -> str:
        return match.group(0) if match.group(1) in known else ""

    return CITED.sub(keep, raw).strip()


def _unrestated(text: str, board: show.Board) -> str:
    """Drop a first sentence that only repeats the first block's count and title."""
    first = next((b for b in board.added if b.total is not None), None)
    found = FIRST_SENTENCE.match(text)
    if first is None or found is None:
        return text
    words = [
        w
        for w in WORD.findall(
            BLOCK_REF.sub("", found.group(0)).replace(",", "").lower()
        )
        if not BLOCK_WORD.match(w)
    ]
    lead = next((i for i, w in enumerate(words) if w not in FILLER), None)
    if lead is None or words[lead] != str(first.total):
        return text
    title = set(WORD.findall((first.title or "").lower()))
    if not set(words[:lead] + words[lead + 1 :]) <= title | FILLER:
        return text
    return text[found.end() :].lstrip() or text


async def _settle(session: AsyncSession, turn: _Turn) -> dict:
    raw = "".join(turn.parts)[:MAX_ANSWER_CHARS]
    cleaned = _unrestated(_clean(raw, turn.board), turn.board)
    text, cites = citations.resolve(cleaned, [], turn.steps)
    if not text and not turn.board.added:
        raise AIError(NO_ANSWER)
    usage = turn.usage
    cost = (usage.charge or turn.cfg.charge(usage.usage, usage.model or None)).usd
    answer = AskMessage(
        thread_id=turn.thread_id,
        role=MessageRole.ASSISTANT.value,
        text=text,
        citations=[c.model_dump() for c in cites],
        trace=[s.model_dump() for s in turn.steps],
        blocks=[b.model_dump(mode="json") for b in turn.board.added],
        follow_ups=[f.model_dump() for f in turn.follow_ups],
        intelligent=turn.intelligent,
        model=usage.model or None,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_usd=cost,
    )
    thread = await session.get(AskThread, turn.thread_id)
    if thread is None:
        raise AIError(THREAD_NOT_FOUND)
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
        "thread": (await EstateService(session)._read(thread)).model_dump(mode="json"),
    }


def _block_frame(block: AnswerBlock, data: BlockData) -> str:
    return _frame(
        StreamEvent.BLOCK,
        {"block": block.model_dump(mode="json"), "data": data.model_dump(mode="json")},
    )


async def _run(session: AsyncSession, user: User, turn: _Turn) -> AsyncIterator[str]:
    tctx = ToolContext(
        session=session,
        token=identity(user, turn.project_id, turn.board.resolved),
        ui_base_url=settings.ui_base_url,
        client=ASK_CLIENT,
    )
    steps = turn.steps
    nonce = secrets.token_hex(4)
    one_scan = turn.board.resolved.scan is not None

    async def call_tool(name: str, args: dict) -> tuple[str, bool]:
        if name in show.NAMES:
            result, step = await show.call(session, name, args, turn.board)
        elif result := _withheld(name, one_scan=one_scan):
            step = TraceStep(
                tool=name,
                label=tools.label(name),
                status=TraceStatus.FAILED.value,
                detail=result,
            )
        else:
            result, step = await tools.call(tctx, name, args)
        await session.commit()
        steps.append(step)
        if step.status != TraceStatus.DONE.value:
            return result, False
        n = sum(1 for s in steps if s.status == TraceStatus.DONE.value)
        fenced = f"<<untrusted {nonce}>>\n{UNTRUSTED_NOTE}\n{result}\n<<end {nonce}>>"
        return f"T{n}: {step.label}.\n{fenced}", True

    pinned: tuple[str, str] | None = None
    failed: str | None = None
    if turn.pinned is not None:
        args = {
            "dimension": turn.pinned.dimension,
            "query": turn.pinned.query,
            "title": turn.pinned.title,
            "narrows": turn.asked.about,
        }
        yield _frame(
            StreamEvent.TRACE,
            {
                "index": len(steps),
                "tool": show.SHOW_ROWS,
                "label": show.running(show.SHOW_ROWS, args),
                "status": TraceStatus.RUNNING.value,
            },
        )
        result, step = await show.call(session, show.SHOW_ROWS, args, turn.board)
        await session.commit()
        steps.append(step)
        yield _frame(StreamEvent.TRACE, {"index": len(steps) - 1, **step.model_dump()})
        while turn.board.fresh:
            yield _block_frame(*turn.board.fresh.pop(0))
        if step.status == TraceStatus.DONE.value and turn.board.added:
            fenced = (
                f"<<untrusted {nonce}>>\n{UNTRUSTED_NOTE}\n{result}\n<<end {nonce}>>"
            )
            pinned = (turn.board.added[-1].id, fenced)
        else:
            failed = prompt.pin_failed(turn.pinned.dimension, turn.pinned.query, result)

    message = prompt.turn(
        question=turn.text,
        resolved=turn.board.resolved,
        project=turn.project,
        blocks=turn.board.every,
        about=turn.about,
        intelligent=turn.intelligent,
        pinned=pinned,
        failed=failed,
        nonce=nonce,
    )
    stream = converse(
        turn.cfg,
        system=prompt.system(),
        messages=[*turn.earlier, {"role": MessageRole.USER.value, "content": message}],
        tools=agent_tools(one_scan=one_scan),
        call_tool=call_tool,
        task=AITask.ASK_DEEP.value if turn.intelligent else AITask.ASK.value,
        max_rounds=INTELLIGENT_TOOL_ROUNDS if turn.intelligent else ESTATE_TOOL_ROUNDS,
        max_calls=ESTATE_CALLS_PER_ROUND,
        stable_system=True,
    )
    async for event in stream:
        if event.kind == TEXT:
            turn.said.append(event.text)
            yield _frame(StreamEvent.DELTA, {"text": event.text})
        elif event.kind == CALL:
            _keep(turn)
            yield _frame(
                StreamEvent.TRACE,
                {
                    "index": len(steps),
                    "tool": event.name,
                    "label": (
                        show.running(event.name, event.args)
                        if event.name in show.NAMES
                        else tools.label(event.name)
                    ),
                    "status": TraceStatus.RUNNING.value,
                },
            )
        elif event.kind == RESULT and steps:
            yield _frame(
                StreamEvent.TRACE, {"index": len(steps) - 1, **steps[-1].model_dump()}
            )
            while turn.board.fresh:
                yield _block_frame(*turn.board.fresh.pop(0))
        elif event.kind == DONE:
            turn.parts.extend(turn.said)
            turn.said.clear()
            turn.usage = event


def _keep(turn: _Turn) -> None:
    """Text written before a tool call is kept only when it cites a block."""
    said = "".join(turn.said)
    if BLOCK_REF.search(said):
        parts = [p for p in PARAGRAPH.split(said) if p.strip()]
        kept = [
            p for p in parts if BLOCK_REF.search(p) or not NARRATION.search(p.strip())
        ]
        if len(kept) == len(parts):
            turn.parts.append(said)
        elif kept:
            turn.parts.append("\n\n".join(p.strip() for p in kept) + "\n\n")
    turn.said.clear()


def _withheld(name: str, *, one_scan: bool) -> str | None:
    if one_scan and name in ACROSS_RUNS:
        return f"{name} reads other scans. This thread reads one scan."
    if name in show.REPLACED:
        return f"{name} is not offered here. Use show_rows or show_groups."
    return None


def agent_tools(*, one_scan: bool = False) -> list:
    held = show.REPLACED | (ACROSS_RUNS if one_scan else frozenset())
    return [*show.AGENT_TOOLS, *(t for t in tools.agent_tools() if t.name not in held)]


async def _follow(session: AsyncSession, turn: _Turn) -> list[FollowUp]:
    board = turn.board
    items = follow_ups.candidates(board.added, board.datas)
    if turn.intelligent:
        datas = [board.datas[b.id] for b in board.added if b.id in board.datas]
        written = await follow_ups.by_model(
            turn.cfg, turn.text, "".join(turn.parts), datas, board.every
        )
        last = board.added[-1] if board.added else None
        about = next((b for b in reversed(board.added) if b.total), last)
        if about is not None:
            for item in written:
                item.about = about.id
            written = follow_ups.narrowed(written, about)
        items = [*written, *items]
    try:
        return await follow_ups.counted(
            session, board.project_id, board.resolved, items, board.every
        )
    except Exception as exc:
        await session.rollback()
        logger.info("ask follow-ups not counted", error=str(exc))
        return []


async def reply(
    session: AsyncSession,
    *,
    thread_id: uuid.UUID,
    user: User,
    question: EstateQuestion,
) -> AsyncIterator[str]:
    token: str | None = None
    try:
        token = await busy.claim(thread_id)
        if token is None:
            yield _frame(StreamEvent.ERROR, {"message": busy.BUSY})
            return
        turn = await _open(session, user, thread_id, question)
        if isinstance(turn, str):
            yield _frame(StreamEvent.ERROR, {"message": turn})
            return
        with ledger.source("thread", turn.thread_id, user.id):
            async for chunk in _run(session, user, turn):
                yield chunk
            turn.follow_ups = await _follow(session, turn)
        payload = await _settle(session, turn)
    except AIError as exc:
        yield _frame(StreamEvent.ERROR, {"message": str(exc)})
        return
    except Exception as exc:
        logger.warning("ask estate reply failed", error=str(exc))
        yield _frame(StreamEvent.ERROR, {"message": ASK_FAILED})
        return
    finally:
        if token is not None:
            await busy.release(thread_id, token)
    yield _frame(StreamEvent.DONE, payload)


async def stream_reply(
    *, thread_id: uuid.UUID, user: User, question: EstateQuestion
) -> AsyncIterator[str]:
    async with async_db_session() as session:
        async for chunk in reply(
            session, thread_id=thread_id, user=user, question=question
        ):
            yield chunk
