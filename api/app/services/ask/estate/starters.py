"""What an empty Ask page offers: counted starters and an example."""

from __future__ import annotations

import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask.estate import blocks, causes
from app.services.ask.estate.blocks import SINGLE_TARGET_SKIP
from app.services.ask.estate.dimensions import DIMENSIONS
from app.services.ask.estate.scope import Resolved
from shared.definitions.ask import (
    ESTATE_STARTERS,
    MAX_ESTATE_STARTERS,
    MIN_CAUSE_ROWS,
    PIVOTS,
    STARTER_CAUSE_SHARE,
    STARTER_TTL_SECONDS,
    BlockKind,
    EstateStarter,
)
from shared.definitions.surface import SURFACE_NOUN
from shared.logging import get_logger
from shared.models.ask import (
    AnswerBlock,
    EstateStarterRead,
    EstateStarters,
    StarterCause,
)

logger = get_logger(__name__)

_held: dict[tuple, tuple[float, EstateStarters]] = {}
_FAILED = StarterCause(key="", value="", label="", count=0, one="")
MAX_HELD = 200


def _key(project_id: uuid.UUID, resolved: Resolved) -> tuple:
    return (project_id, resolved.filtered, resolved.targets, resolved.scan)


async def _cause(
    session: AsyncSession,
    project_id: uuid.UUID,
    resolved: Resolved,
    starter: EstateStarter,
    total: int,
) -> StarterCause | None:
    dim = DIMENSIONS[starter.dimension]
    try:
        async with session.begin_nested():
            scope = await blocks._scope(session, project_id, dim, resolved)
            found = await causes.read(
                session,
                project_id,
                dim,
                scope,
                blocks.scoped(resolved, starter.query),
                starter.cause or "",
            )
    except Exception as exc:
        logger.info("ask starter cause failed", starter=starter.key, error=str(exc))
        return _FAILED
    if found is None or not found.groups or total < MIN_CAUSE_ROWS:
        return None
    top = found.groups[0]
    if top.count < total * STARTER_CAUSE_SHARE:
        return None
    return StarterCause(
        key=found.key, value=top.value, label=top.label, count=top.count, one=found.one
    )


def _example(starters: list[EstateStarterRead]) -> str | None:
    for s in starters:
        if s.cause and (pivots := PIVOTS.get((s.dimension, s.cause.key), ())):
            return pivots[0].question.format(value=s.cause.value)
    return None


async def counted(
    session: AsyncSession, project_id: uuid.UUID, resolved: Resolved
) -> EstateStarters:
    key = _key(project_id, resolved)
    hit = _held.get(key)
    if hit and time.monotonic() - hit[0] < STARTER_TTL_SECONDS:
        return hit[1]
    out: list[EstateStarterRead] = []
    failed = False
    for starter in ESTATE_STARTERS:
        block = AnswerBlock(
            id="starter",
            kind=BlockKind.ROWS.value,
            dimension=starter.dimension,
            query=starter.query,
        )
        try:
            data = await blocks.rows(
                session, project_id, resolved, block, limit=1, extras=False
            )
        except blocks.BlockError:
            continue
        if not data.total:
            continue
        wants = starter.cause and not (
            resolved.count == 1 and starter.cause in SINGLE_TARGET_SKIP
        )
        cause = (
            await _cause(session, project_id, resolved, starter, data.total)
            if wants
            else None
        )
        failed = failed or (wants and cause is _FAILED)
        cause = None if cause is _FAILED else cause
        one, many = SURFACE_NOUN[starter.dimension]
        out.append(
            EstateStarterRead(
                key=starter.key,
                question=starter.question,
                statement=starter.statement.format(
                    noun=one if data.total == 1 else many
                ),
                dimension=starter.dimension,
                query=starter.query,
                count=data.total,
                capped=data.capped,
                cause=cause,
            )
        )
        if len(out) >= MAX_ESTATE_STARTERS:
            break
    result = EstateStarters(
        filtered=resolved.filtered,
        scope_values=resolved.links,
        starters=out,
        example=_example(out),
    )
    if failed:
        return result
    if len(_held) >= MAX_HELD:
        _held.clear()
    _held[key] = (time.monotonic(), result)
    return result
